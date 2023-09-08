# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
import uuid
from typing import Optional

from fastapi import Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *
from functions.discord import DiscordAuth


async def get_callback(request: Request, response: Response, code: Optional[str] = None, error_description: Optional[str] = None, callback_url: Optional[str] = None):
    app = request.app
    if code is None and error_description is None or callback_url is None:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_params")}

    if code is None and error_description is not None:
        response.status_code = 400
        return {"error": error_description}

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /auth/discord/callback', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    try:
        discord_auth = DiscordAuth(app.config.discord_client_id, app.config.discord_client_secret, callback_url)
        tokens = await discord_auth.get_tokens(code)

        if "access_token" in tokens.keys():
            await app.db.extend_conn(dhrid, 30)
            user_data = await discord_auth.get_user_data_from_token(tokens["access_token"])
            await app.db.extend_conn(dhrid, 2)

            if "id" not in user_data:
                response.status_code = 400
                return {"error": user_data['message']}

            discordid = user_data['id']
            username = str(user_data['username'])
            username = convertQuotation(username).replace(",","")
            email = ""
            if "email" in user_data.keys():
                email = convertQuotation(user_data['email'])
            avatar = ""
            if avatar is not None:
                avatar = getAvatarSrc(discordid, convertQuotation(user_data['avatar']))
            tokens = {**tokens, **user_data}

            await app.db.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
            await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

            (access_token, refresh_token, expire_timestamp) = (convertQuotation(tokens["access_token"]), convertQuotation(tokens["refresh_token"]), tokens["expires_in"] + int(time.time()) - 60)
            await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE discordid = {discordid}")
            await app.db.execute(dhrid, f"INSERT INTO discord_access_token VALUES ({discordid}, '{convertQuotation(callback_url)}', '{access_token}', '{refresh_token}', {expire_timestamp})")

            await app.db.execute(dhrid, f"SELECT uid, mfa_secret, email FROM user WHERE discordid = {discordid}")
            t = await app.db.fetchall(dhrid)
            mfa_secret = ""
            if len(t) == 0:
                if "discord" not in app.config.register_methods:
                    response.status_code = 404
                    return {"error": ml.tr(request, "user_not_found")}

                if app.config.use_server_nickname:
                    try:
                        r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {app.config.discord_bot_token}"}, dhrid = dhrid)
                        if r.status_code == 200:
                            d = json.loads(r.text)
                            if d["nick"] is not None:
                                username = convertQuotation(d["nick"])
                    except:
                        pass

                await app.db.execute(dhrid, f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES (-1, '{username}', '{email}', '{avatar}', '', '', {discordid}, NULL, NULL, {int(time.time())}, '')")
                await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
                uid = (await app.db.fetchone(dhrid))[0]
                await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,economy,event,')")
                await app.db.commit(dhrid)
                await AuditLog(request, uid, ml.ctr(request, "discord_register", var = {"country": getRequestCountry(request)}))

            else:
                uid = t[0][0]
                mfa_secret = t[0][1]
                if t[0][2] is None or "@" not in t[0][2] or app.config.sync_discord_email:
                    await app.db.execute(dhrid, f"UPDATE user SET email = '{email}' WHERE uid = {uid}")
                    await app.db.commit(dhrid)

            if mfa_secret != "":
                stoken = str(uuid.uuid4())
                stoken = "f" + stoken[1:]
                await app.db.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
                await app.db.commit(dhrid)
                return {"token": stoken, "mfa": True}

            await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR discordid = {discordid} OR email = '{email if email is not None and '@' in email else 'NULL'}'")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                reason = t[0][0]
                expire = t[0][1]
                if expire != 253402272000:
                    expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
                else:
                    expire = ml.tr(request, "forever")
                response.status_code = 423
                if reason != "":
                    return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
                else:
                    return {"error": ml.tr(request, "ban_with_expire", var = {"expire": expire})}

            await app.db.execute(dhrid, f"SELECT status FROM pending_user_deletion WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                status = t[0][0]
                if status == 1:
                    await app.db.execute(dhrid, f"UPDATE pending_user_deletion SET status = 0 WHERE uid = {uid}")
                    await app.db.commit(dhrid)
                    response.status_code = 423
                    return {"error": ml.tr(request, "user_pending_deletion")}
                elif status == 0:
                    await app.db.execute(dhrid, f"DELETE FROM pending_user_deletion WHERE uid = {uid}")
                    await app.db.commit(dhrid)

            stoken = str(uuid.uuid4())
            while stoken[0] == "e":
                stoken = str(uuid.uuid4())
            await app.db.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
            await app.db.commit(dhrid)

            await UpdateRoleConnection(request, discordid)

            username = (await GetUserInfo(request, uid = uid))["name"]
            language = await GetUserLanguage(request, uid)
            await AuditLog(request, uid, ml.ctr(request, "discord_login", var = {"country": getRequestCountry(request)}))

            await notification(request, "login", uid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language),
                discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language),
                                 "description": "",
                                 "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                                            {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
                }
            )

            return {"token": stoken, "mfa": False}

        elif 'error_description' in tokens.keys():
            response.status_code = 400
            return {"error": tokens['error_description']}
        elif 'error' in tokens.keys():
            response.status_code = 400
            return {"error": tokens['error']}
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "unknown_error")}

    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_error")}
