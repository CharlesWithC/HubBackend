# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import uuid

from fastapi import Request, Response

import multilang as ml
from functions import *


async def get_callback(request: Request, response: Response):
    app = request.app
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if data == "":
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_params")}

    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /auth/steam/callback', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    r = None
    try:
        r = await arequests.get(app, "https://steamcommunity.com/openid/login?" + data, dhrid = dhrid)
    except:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"})}
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"})}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_steam_auth")}
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    await app.db.execute(dhrid, f"SELECT uid, discordid FROM user WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        if "steam" not in app.config.register_methods:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}

        username = f"Steam User {steamid}"
        avatar = ""

        if app.config.steam_api_key != "":
            try:
                r = await arequests.get(app, f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={app.config.steam_api_key}&steamids={steamid}", dhrid = dhrid, timeout = 10)
                d = json.loads(r.text)
                username = convertQuotation(d["response"]["players"][0]["personaname"])
                avatar = convertQuotation(d["response"]["players"][0]["avatarfull"])
            except:
                pass

        # register user
        await app.db.execute(dhrid, f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret, tracker_in_use) VALUES (-1, '{username}', '', '{avatar}', '', '', NULL, {steamid}, NULL, {int(time.time())}, '', 0)")
        await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
        uid = (await app.db.fetchone(dhrid))[0]
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,economy,event,')")
        await app.db.commit(dhrid)
        await AuditLog(request, uid, ml.ctr(request, "steam_register", var = {"country": getRequestCountry(request)}))
    else:
        uid = t[0][0]

    await app.db.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await app.db.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
        await app.db.commit(dhrid)
        return {"token": stoken, "mfa": True}

    await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR steamid = {steamid}")
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

    username = (await GetUserInfo(request, uid = uid))["name"]
    language = await GetUserLanguage(request, uid)
    await AuditLog(request, uid, ml.ctr(request, "steam_login", var = {"country": getRequestCountry(request)}))
    await notification(request, "login", uid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language),
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language),
                         "description": "",
                         "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                                    {"name": ml.tr(request, "ip", force_lang = language), "value": f"`{request.client.host}`", "inline": True}]
        }
    )

    return {"token": stoken, "mfa": False}
