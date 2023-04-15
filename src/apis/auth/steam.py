# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
import uuid
from typing import Optional

from fastapi import Request, Response
from fastapi.responses import RedirectResponse
from pysteamsignin.steamsignin import SteamSignIn

import multilang as ml
from functions import *


async def get_redirect(request: Request, connect_account: Optional[bool] = False):
    app = request.app
    steamLogin = SteamSignIn()
    encodedData = ""
    if not connect_account:
        encodedData = steamLogin.ConstructURL(f'https://{app.config.apidomain}/{app.config.abbr}/auth/steam/callback')
    else:
        encodedData = steamLogin.ConstructURL(f'https://{app.config.apidomain}/{app.config.abbr}/auth/steam/connect')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

async def get_connect(request: Request):
    app = request.app
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{app.config.apidomain}/{app.config.abbr}/auth/steam/connect')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)

    return RedirectResponse(url=app.config.frontend_urls.steam_callback + f"?{str(request.query_params)}", status_code=302)

async def get_callback(request: Request, response: Response):
    app = request.app
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{app.config.apidomain}/{app.config.abbr}/auth/steam/callback')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /auth/steam/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "rate_limit")), status_code=302)

    r = None
    try:
        r = await arequests.get(app, "https://steamcommunity.com/openid/login?" + data, dhrid = dhrid)
    except:
        response.status_code = 503
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "steam_api_error")), status_code=302)
    if r.status_code // 100 != 2:
        response.status_code = 503
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "steam_api_error")), status_code=302)
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "invalid_steam_auth")), status_code=302)
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])
    
    await app.db.execute(dhrid, f"SELECT uid, discordid FROM user WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        if not "steam" in app.config.register_methods:
            response.status_code = 404
            return RedirectResponse(url=getUrl4Msg(app, ml.tr(request, "user_not_found")), status_code=302)
        
        username = f"Steam User {steamid}"
        avatar = ""

        if app.config.steam_api_key != "":
            try:
                r = await arequests.get(app, f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={app.config.steam_api_key}&steamids={steamid}", dhrid = dhrid)
                d = json.loads(r.text)
                username = convertQuotation(d["response"]["players"][0]["personaname"])
                avatar = convertQuotation(d["response"]["players"][0]["avatarfull"])
            except:
                pass
        
        # register user
        await app.db.execute(dhrid, f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES (-1, '{username}', '', '{avatar}', '', '', NULL, {steamid}, NULL, {int(time.time())}, '')")
        await app.db.execute(dhrid, f"SELECT LAST_INSERT_ID();")
        uid = (await app.db.fetchone(dhrid))[0]
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,economy,event,')")
        await app.db.commit(dhrid)
        await AuditLog(request, uid, ml.ctr(request, "steam_register", var = {"country": getRequestCountry(request)}))
    else:
        uid = t[0][0]
    
    await app.db.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR steamid = {steamid}")
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

    await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await app.db.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
        await app.db.commit(dhrid)
        return RedirectResponse(url=getUrl4MFA(app, stoken), status_code=302)

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
                                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return RedirectResponse(url=getUrl4Token(app, stoken), status_code=302)
