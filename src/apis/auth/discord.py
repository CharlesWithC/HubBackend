# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
import uuid
from typing import Optional

from discord_oauth2 import DiscordAuth
from fastapi import Request
from fastapi.responses import RedirectResponse

import multilang as ml
from functions import *
from api import tracebackHandler


async def get_redirect(request: Request, connect_account: Optional[bool] = False):
    app = request.app
    if not connect_account:
        return RedirectResponse(url=f"https://discord.com/api/oauth2/authorize?client_id={app.config.discord_client_id}&redirect_uri=https%3A%2F%2F{app.config.apidomain}%2F{app.config.abbr}%2Fauth%2Fdiscord%2Fcallback&response_type=code&scope=identify%20email%20role_connections.write", status_code=302)
    else:
        return RedirectResponse(url=f"https://discord.com/api/oauth2/authorize?client_id={app.config.discord_client_id}&redirect_uri=https%3A%2F%2F{app.config.apidomain}%2F{app.config.abbr}%2Fauth%2Fdiscord%2Fconnect&response_type=code&scope=identify%20email%20role_connections.write", status_code=302)
    
async def get_connect(request: Request, code: Optional[str] = "", error_description: Optional[str] = ""):
    app = request.app
    referer = request.headers.get("Referer")
    data = str(request.query_params)
    if referer in ["", "-", None] or data == "":
        return RedirectResponse(url=f"https://discord.com/api/oauth2/authorize?client_id={app.config.discord_client_id}&redirect_uri=https%3A%2F%2F{app.config.apidomain}%2F{app.config.abbr}%2Fauth%2Fdiscord%2Fconnect&response_type=code&scope=identify%20email%20role_connections.write", status_code=302)

    if code == "":
        return RedirectResponse(url=getUrl4Msg(app, error_description), status_code=302)
    
    return RedirectResponse(url=app.config.frontend_urls.discord_callback + f"?code={code}", status_code=302)

async def get_callback(request: Request, code: Optional[str] = "", error_description: Optional[str] = ""):
    app = request.app
    referer = request.headers.get("Referer")
    if referer in ["", "-", None] or code == "" and error_description == "":
        return RedirectResponse(url=f"https://discord.com/api/oauth2/authorize?client_id={app.config.discord_client_id}&redirect_uri=https%3A%2F%2F{app.config.apidomain}%2F{app.config.abbr}%2Fauth%2Fdiscord%2Fcallback&response_type=code&scope=identify%20email%20role_connections.write", status_code=302)
    
    if code == "":
        return RedirectResponse(url=getUrl4Msg(app, error_description), status_code=302)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /auth/discord/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "rate_limit")), status_code=302)

    try:
        discord_auth = DiscordAuth(app.config.discord_client_id, app.config.discord_client_secret, f"https://{app.config.apidomain}/{app.config.abbr}/auth/discord/callback")
        tokens = discord_auth.get_tokens(code)
        if "access_token" in tokens.keys():
            await app.db.extend_conn(dhrid, 30)
            user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
            await app.db.extend_conn(dhrid, 2)
            if not 'id' in user_data:
                return RedirectResponse(url=getUrl4Msg(app, "Discord Error: " + user_data['message']), status_code=302)
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
            await app.db.execute(dhrid, f"INSERT INTO discord_access_token VALUES ({discordid}, 'callback', '{access_token}', '{refresh_token}', {expire_timestamp})")

            await app.db.execute(dhrid, f"SELECT uid, mfa_secret, email FROM user WHERE discordid = {discordid}")
            t = await app.db.fetchall(dhrid)
            mfa_secret = ""
            if len(t) == 0:
                if not "discord" in app.config.register_methods:
                    return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "user_not_found")), status_code=302)
        
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
                await app.db.execute(dhrid, f"SELECT LAST_INSERT_ID();")
                uid = (await app.db.fetchone(dhrid))[0]
                await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,economy,event,')")
                await app.db.commit(dhrid)
                await AuditLog(request, uid, ml.ctr(request, "discord_register", var = {"country": getRequestCountry(request)}))
            else:
                uid = t[0][0]
                mfa_secret = t[0][1]
                if t[0][2] == "":
                    await app.db.execute(dhrid, f"UPDATE user SET email = '{email}' WHERE uid = {uid}")
                    await app.db.commit(dhrid)

            if mfa_secret != "":
                stoken = str(uuid.uuid4())
                stoken = "f" + stoken[1:]
                await app.db.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
                await app.db.commit(dhrid)
                return RedirectResponse(url=getUrl4MFA(app, stoken), status_code=302)

            await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR discordid = {discordid} OR email = '{email}'")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                reason = t[0][0]
                expire = t[0][1]
                if expire != 253402272000:
                    expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
                else:
                    expire = ml.tr(request, "forever")
                if reason != "":
                    return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)
                else:
                    return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "ban_with_expire", var = {"expire": expire})), status_code=302)
            
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

            return RedirectResponse(url=getUrl4Token(app, stoken), status_code=302)
        
        if 'error_description' in tokens.keys():
            return RedirectResponse(url=getUrl4Msg(app, tokens['error_description']), status_code=302)
        else:
            return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "unknown_error")), status_code=302)

    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "unknown_error")), status_code=302)
