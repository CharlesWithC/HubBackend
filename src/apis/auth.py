# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
import uuid
from hashlib import sha256
from typing import Optional

import bcrypt
from discord_oauth2 import DiscordAuth
from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse
from pysteamsignin.steamsignin import SteamSignIn

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *

discord_auth = DiscordAuth(config.discord_client_id, config.discord_client_secret, config.discord_callback_url)

def getUrl4Msg(message):
    return config.frontend_urls.auth_message.replace("{message}", str(message))

def getUrl4Token(token):
    return config.frontend_urls.auth_token.replace("{token}", str(token))

def getUrl4MFA(token):
    return config.frontend_urls.auth_mfa.replace("{token}", str(token))

# Password Auth
@app.post(f'/{config.abbr}/auth/password')
async def post_auth_password(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/password', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        email = convertQuotation(data["email"])  
        password = str(data["password"]).encode('utf-8')
        hcaptcha_response = data["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    try:
        r = await arequests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response}, dhrid = dhrid)
        d = json.loads(r.text)
        if not d["success"]:
            response.status_code = 403
            return {"error": ml.tr(request, "invalid_captcha")}
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": "Service Unavailable"}
    
    await aiosql.execute(dhrid, f"SELECT uid, password FROM user_password WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_email_or_password")}
    uid = t[0][0]
    pwdhash = t[0][1]
    ok = bcrypt.checkpw(password, b64d(pwdhash).encode())
    if not ok:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_email_or_password")}
    discordid = (await GetUserInfo(dhrid, request, uid = uid))["discordid"]
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await aiosql.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
        await aiosql.commit(dhrid)
        return {"token": stoken, "mfa": True}

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        response.status_code = 403
        return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
        
    stoken = str(uuid.uuid4())
    stoken = "e" + stoken[1:]
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, -999, f"Password login: `{username}` (UID: `{uid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", uid, \
        ml.tr(request, "new_login", \
            var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
            "description": "", \
            "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"token": stoken, "mfa": False}

# Discord Auth
@app.get(f'/{config.abbr}/auth/discord/redirect', response_class=RedirectResponse)
async def get_auth_discord_redirect():
    # login_url = discord_auth.login()
    return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
@app.get(f'/{config.abbr}/auth/discord/callback')
async def get_auth_discord_callback(request: Request, code: Optional[str] = "", error_description: Optional[str] = ""):
    referer = request.headers.get("Referer")
    if referer in ["", "-", None]:
        return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
    if code == "":
        return RedirectResponse(url=getUrl4Msg(error_description), status_code=302)
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /auth/discord/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "rate_limit")), status_code=302)

    try:
        tokens = discord_auth.get_tokens(code)
        if "access_token" in tokens.keys():
            user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
            if not 'id' in user_data:
                return RedirectResponse(url=getUrl4Msg("Discord Error: " + user_data['message']), status_code=302)
            discordid = user_data['id']
            username = str(user_data['username'])
            username = convertQuotation(username).replace(",","")
            email = ""
            if "email" in user_data.keys():
                email = convertQuotation(user_data['email'])
            avatar = getAvatarSrc(discordid, user_data['avatar'])
            tokens = {**tokens, **user_data}

            await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
            await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

            await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
            t = await aiosql.fetchall(dhrid)
            if len(t) > 0:
                reason = t[0][0]
                expire = t[0][1]
                expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
                return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)
            uid = -1

            await aiosql.execute(dhrid, f"SELECT uid, mfa_secret FROM user WHERE discordid = '{discordid}'")
            t = await aiosql.fetchall(dhrid)
            mfa_secret = ""
            if len(t) == 0:
                if config.use_server_nickname:
                    try:
                        r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
                        if r.status_code == 200:
                            d = json.loads(r.text)
                            if d["nick"] is not None:
                                username = convertQuotation(d["nick"])
                    except:
                        traceback.print_exc()
                        
                await aiosql.execute(dhrid, f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES (-1, '{username}', '{email}', '{avatar}', '', '', {discordid}, NULL, NULL, {int(time.time())}, '')")
                await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
                uid = (await aiosql.fetchone(dhrid))[0]
                await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,event,')")
                await aiosql.commit(dhrid)
                await AuditLog(dhrid, -999, f"User register: `{username}` (UID: `{uid}`)")
            else:
                uid = t[0][0]
                mfa_secret = t[0][1]
            if mfa_secret != "":
                stoken = str(uuid.uuid4())
                stoken = "f" + stoken[1:]
                await aiosql.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
                await aiosql.commit(dhrid)
                return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

            stoken = str(uuid.uuid4())
            while stoken[0] == "e":
                stoken = str(uuid.uuid4())
            await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
            await aiosql.commit(dhrid)

            username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
            language = await GetUserLanguage(dhrid, uid)
            await AuditLog(dhrid, -999, f"Discord login: `{username}` (UID: `{uid}`) from `{getRequestCountry(request)}`")
            await notification(dhrid, "login", uid, \
                ml.tr(request, "new_login", \
                    var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
                discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
                    "description": "", \
                    "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                            {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
                }
            )
            return RedirectResponse(url=getUrl4Token(stoken), status_code=302)
        
        if 'error_description' in tokens.keys():
            return RedirectResponse(url=getUrl4Msg(tokens['error_description']), status_code=302)
        else:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "unknown_error")), status_code=302)

    except:
        traceback.print_exc()
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "unknown_error")), status_code=302)

# Steam Auth (Only for connecting account)
@app.get(f"/{config.abbr}/auth/steam/redirect")
async def get_auth_steam_redirect(connect_account: Optional[bool] = False):
    steamLogin = SteamSignIn()
    encodedData = ""
    if not connect_account:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/callback')
    else:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/connect')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

@app.get(f"/{config.abbr}/auth/steam/connect")
async def get_auth_steam_connect(request: Request):
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/connect')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)

    return RedirectResponse(url=config.frontend_urls.steam_callback + f"?{str(request.query_params)}", status_code=302)

@app.get(f"/{config.abbr}/auth/steam/callback")
async def get_auth_steam_callback(request: Request, response: Response):
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/callback')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /auth/steam/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "rate_limit")), status_code=302)

    r = None
    try:
        r = await arequests.get("https://steamcommunity.com/openid/login?" + data, dhrid = dhrid)
    except:
        traceback.print_exc()
        response.status_code = 503
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "steam_api_error")), status_code=302)
    if r.status_code // 100 != 2:
        response.status_code = 503
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "steam_api_error")), status_code=302)
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "invalid_steam_auth")), status_code=302)
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])
    
    await aiosql.execute(dhrid, f"SELECT uid, discordid FROM user WHERE steamid = '{steamid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "user_not_found")), status_code=302)
    uid = t[0][0]
    discordid = t[0][1]
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await aiosql.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
        await aiosql.commit(dhrid)
        return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, -999, f"Steam login: `{username}` (Discord ID: `{uid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", uid, \
        ml.tr(request, "new_login", \
            var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
            "description": "", \
            "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return RedirectResponse(url=getUrl4Token(stoken), status_code=302)

# Token Management
@app.get(f'/{config.abbr}/token')
async def get_token(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /token', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    token_type = authorization.split(" ")[0].lower()

    return {"token_type": token_type}

@app.patch(f"/{config.abbr}/token")
async def patch_token(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]

    await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    return {"token": stoken}

@app.delete(f'/{config.abbr}/token')
async def delete_token(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    stoken = authorization.split(" ")[1]

    await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.get(f'/{config.abbr}/token/list')
async def get_token_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /token/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if not order_by in ["ip", "timestamp", "country_code", "user_agent", "last_used_timestamp"]:
        order_by = "last_used_timestamp"
        order = "desc"
    if order_by == "country_code":
        order_by = "country"
    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    ret = []
    await aiosql.execute(dhrid, f"SELECT token, ip, timestamp, country, user_agent, last_used_timestamp FROM session \
        WHERE uid = {uid} ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        tk = tt[0]
        tk = sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "country": getFullCountry(tt[3]), "user_agent": tt[4], "create_timestamp": tt[2], "last_used_timestamp": tt[5]})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM session WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.delete(f'/{config.abbr}/token/hash')
async def delete_token_hash(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /token/hash', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    data = await request.json()
    try:
        hsh = data["hash"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    ok = False
    await aiosql.execute(dhrid, f"SELECT token FROM session WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{tt[0]}' AND uid = {uid}")
            await aiosql.commit(dhrid)
            break

    if ok:
        return Response(status_code=204)
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "hash_does_not_match_any_token", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/token/all')
async def delete_token_all(request: Request, response: Response, authorization: str = Header(None), \
        last_used_before: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /token/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if last_used_before == -1:
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.commit(dhrid)
    else:
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid} AND last_used_timestamp <= {last_used_before}")
        await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.get(f'/{config.abbr}/token/application/list')
async def get_token_application_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /token/application/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if not order_by in ["timestamp", "last_used_timestamp"]:
        order_by = "last_used_timestamp"
        order = "desc"
    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    ret = []
    await aiosql.execute(dhrid, f"SELECT app_name, token, timestamp, last_used_timestamp FROM application_token \
        WHERE uid = {uid} ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        tk = sha256(tt[1].encode()).hexdigest()
        ret.append({"app_name": tt[0], "hash": tk, "create_timestamp": tt[2], "last_used_timestamp": tt[3]})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application_token WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.post(f'/{config.abbr}/token/application')
async def post_token_application(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    data = await request.json()

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    try:
        app_name = convertQuotation(data["app_name"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    if len(app_name) >= 128:
        response.status_code = 400
        return {"error": ml.tr(request, "content_too_long", var = {"item": "app_name", "limit": "128"}, force_lang = au["language"])}

    stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO application_token VALUES ('{app_name}', '{stoken}', {uid}, {int(time.time())}, 0)")
    await aiosql.commit(dhrid)
    
    return {"token": stoken}

@app.delete(f'/{config.abbr}/token/application')
async def delete_token_application(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    data = await request.json()
    try:
        hsh = data["hash"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    ok = False
    await aiosql.execute(dhrid, f"SELECT token FROM application_token WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE token = '{tt[0]}' AND uid = {uid}")
            await aiosql.commit(dhrid)
            break
    
    if ok:
        return Response(status_code=204)
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "hash_does_not_match_any_token", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/token/application/all')
async def delete_token_application_all(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /token/application/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

# Multiple Factor Authentication
@app.post(f"/{config.abbr}/auth/mfa")
async def post_auth_mfa(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/mfa', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        token = data["token"]
        otp = data["otp"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT uid FROM auth_ticket WHERE token = '{token}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0 or not token.startswith("f"):
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_token")}
    uid = t[0][0]
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}
    secret = t[0][0]
    if secret == "":
        response.status_code = 428
        return {"error": ml.tr(request, "mfa_not_enabled")}
        
    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": ml.tr(request, "mfa_invalid_otp")}

    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE token = '{token}'")
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        response.status_code = 403
        return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}

    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4()) # All MFA logins won't be counted as unsafe
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, -999, f"MFA login: `{username}` (Discord ID: `{uid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", uid, \
        ml.tr(request, "new_login", \
            var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
            "description": "", \
            "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"token": stoken}

@app.post(f"/{config.abbr}/auth/ticket")
async def post_auth_ticket(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/ticket', 180, 20)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = str(uuid.uuid4())
    while stoken[0] == "f":
        stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+180})")
    await aiosql.commit(dhrid)

    return {"token": stoken}

@app.get(f"/{config.abbr}/auth/ticket")
async def get_auth_ticket(request: Request, response: Response, token: Optional[str] = ""):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /auth/ticket', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    token = token.replace("'","")

    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT uid FROM auth_ticket WHERE token = '{token}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_token")}
    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE token = '{token}'")
    await aiosql.commit(dhrid)
    return {"user": await GetUserInfo(dhrid, request, uid = t[0][0])}