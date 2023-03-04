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
from functions import *

discord_auth = DiscordAuth(config.discord_client_id, config.discord_client_secret, config.discord_callback_url)

def getUrl4Msg(message):
    return config.frontend_urls.auth_message.replace("{message}", str(message))

def getUrl4Token(token):
    return config.frontend_urls.auth_token.replace("{token}", str(token))

def getUrl4MFA(token):
    return config.frontend_urls.auth_mfa.replace("{token}", str(token))

# Password Auth
@app.post(f'/{config.abbr}/auth/password')
async def postAuthPassword(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /auth/password', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    form = await request.form()
    try:
        email = convert_quotation(form["email"])  
        password = str(form["password"]).encode('utf-8')
        hcaptcha_response = form["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form")}

    try:
        r = await arequests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response}, dhrid = dhrid)
        d = json.loads(r.text)
        if not d["success"]:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "invalid_captcha")}
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": True, "descriptor": "Service Unavailable"}
    await aiosql.execute(dhrid, f"SELECT discordid, password FROM user_password WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_email_or_password")}
    discordid = t[0][0]
    pwdhash = t[0][1]
    ok = bcrypt.checkpw(password, b64d(pwdhash).encode())
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_email_or_password")}
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    if (config.in_guild_check or config.use_server_nickname) and config.discord_bot_token != "":
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
        except:
            traceback.print_exc()
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "discord_check_fail")}
        if r.status_code == 404:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "must_join_discord")}
        if r.status_code // 100 != 2:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "discord_check_fail")}
        d = json.loads(r.text)
        if config.use_server_nickname and d["nick"] != None:
            username = d["nick"]
            await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}' WHERE discordid = '{discordid}'")
            await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await aiosql.execute(dhrid, f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
        await aiosql.commit(dhrid)
        return {"error": False, "response": {"token": stoken, "mfa": True}}

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
        
    stoken = str(uuid.uuid4())
    stoken = "e" + stoken[1:]
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await getUserInfo(dhrid, discordid = discordid))["name"]
    language = await GetUserLanguage(dhrid, discordid)
    await AuditLog(dhrid, -999, f"Password login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", discordid, \
        ml.tr(request, "new_login", \
            var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
            "description": "", \
            "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"error": False, "response": {"token": stoken, "mfa": False}}

# Discord Auth
@app.get(f'/{config.abbr}/auth/discord/redirect', response_class=RedirectResponse)
async def getAuthDiscordRedirect(request: Request):
    # login_url = discord_auth.login()
    return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
@app.get(f'/{config.abbr}/auth/discord/callback')
async def getAuthDiscordCallback(request: Request, response: Response, code: Optional[str] = "", error_description: Optional[str] = ""):
    referer = request.headers.get("Referer")
    if referer in ["", "-", None]:
        return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
    if code == "":
        return RedirectResponse(url=getUrl4Msg(error_description), status_code=302)
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /auth/discord/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "rate_limit")), status_code=302)

    try:
        tokens = discord_auth.get_tokens(code)
        if "access_token" in tokens.keys():
            user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
            if not 'id' in user_data:
                return RedirectResponse(url=getUrl4Msg("Discord Error: " + user_data['message']), status_code=302)
            discordid = user_data['id']
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

            await aiosql.execute(dhrid, f"SELECT * FROM user WHERE discordid = '{discordid}'")
            t = await aiosql.fetchall(dhrid)
            username = str(user_data['username'])
            username = convert_quotation(username).replace(",","")
            if not "email" in user_data.keys():
                return RedirectResponse(url=getUrl4Msg(ml.tr(request, "invalid_email")), status_code=302)
            email = str(user_data['email'])
            email = convert_quotation(email)
            if not "@" in email: # make sure it's not empty
                return RedirectResponse(url=getUrl4Msg(ml.tr(request, "invalid_email")), status_code=302)
            avatar = str(user_data['avatar'])
            if len(t) == 0:
                await aiosql.execute(dhrid, f"INSERT INTO user VALUES (-1, {discordid}, '{username}', '{avatar}', '',\
                    '{email}', -1, -1, '', {int(time.time())}, '')")
                await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{discordid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,event,')")
                await AuditLog(dhrid, -999, f"User register: `{username}` (Discord ID: `{discordid}`)")
            else:
                await aiosql.execute(dhrid, f"UPDATE user_password SET email = '{email}' WHERE discordid = '{discordid}'")
                await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}', avatar = '{avatar}', email = '{email}' WHERE discordid = '{discordid}'")
            await aiosql.commit(dhrid)
            
            if (config.in_guild_check or config.use_server_nickname) and config.discord_bot_token != "":
                try:
                    r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
                except:
                    traceback.print_exc()
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
                if r.status_code == 404:
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)
                if r.status_code // 100 != 2:
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
                d = json.loads(r.text)
                if config.use_server_nickname and d["nick"] != None:
                    username = d["nick"]
                    await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}' WHERE discordid = '{discordid}'")
                    await aiosql.commit(dhrid)

            await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
            t = await aiosql.fetchall(dhrid)
            mfa_secret = t[0][0]
            if mfa_secret != "":
                stoken = str(uuid.uuid4())
                stoken = "f" + stoken[1:]
                await aiosql.execute(dhrid, f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
                await aiosql.commit(dhrid)
                return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

            stoken = str(uuid.uuid4())
            while stoken[0] == "e":
                stoken = str(uuid.uuid4())
            await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
            await aiosql.commit(dhrid)
            username = (await getUserInfo(dhrid, discordid = discordid))["name"]
            language = await GetUserLanguage(dhrid, discordid)
            await AuditLog(dhrid, -999, f"Discord login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
            await notification(dhrid, "login", discordid, \
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
async def getSteamOAuth(request: Request, response: Response, connect_account: Optional[bool] = False):
    steamLogin = SteamSignIn()
    encodedData = ""
    if not connect_account:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/callback')
    else:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/connect')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

@app.get(f"/{config.abbr}/auth/steam/connect")
async def getSteamConnect(request: Request, response: Response):
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/connect')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)

    return RedirectResponse(url=config.frontend_urls.steam_callback + f"?{str(request.query_params)}", status_code=302)

@app.get(f"/{config.abbr}/auth/steam/callback")
async def getSteamCallback(request: Request, response: Response):
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer in ["", "-", None] or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.abbr}/auth/steam/callback')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /auth/steam/callback', 60, 10)
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
    
    await aiosql.execute(dhrid, f"SELECT discordid FROM user WHERE steamid = '{steamid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "user_not_found")), status_code=302)
    discordid = t[0][0]
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)

    if (config.in_guild_check or config.use_server_nickname) and config.discord_bot_token != "":
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
        except:
            traceback.print_exc()
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        if r.status_code == 404:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)
        if r.status_code // 100 != 2:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        d = json.loads(r.text)
        if config.use_server_nickname and d["nick"] != None:
            username = d["nick"]
            await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}' WHERE discordid = '{discordid}'")
            await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await aiosql.execute(dhrid, f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
        await aiosql.commit(dhrid)
        return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)
    username = (await getUserInfo(dhrid, discordid = discordid))["name"]
    language = await GetUserLanguage(dhrid, discordid)
    await AuditLog(dhrid, -999, f"Steam login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", discordid, \
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
async def getToken(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /token', 60, 120)
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

    return {"error": False, "response": {"token_type": token_type}}

@app.patch(f"/{config.abbr}/token")
async def patchToken(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]

    await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.abbr}/token')
async def deleteToken(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /token', 60, 30)
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

    return {"error": False}

@app.get(f'/{config.abbr}/token/list')
async def getTokenList(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /token/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
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
        WHERE discordid = {discordid} ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        tk = tt[0]
        tk = sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "country": getFullCountry(tt[3]), "user_agent": tt[4], "create_timestamp": str(tt[2]), "last_used_timestamp": str(tt[5])})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM session WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.delete(f'/{config.abbr}/token/hash')
async def deleteTokenHash(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /token/hash', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    form = await request.form()
    try:
        hsh = form["hash"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    ok = False
    await aiosql.execute(dhrid, f"SELECT token FROM session WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{tt[0]}' AND discordid = {discordid}")
            await aiosql.commit(dhrid)
            break

    if ok:
        return {"error": False}
    else:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "hash_does_not_match_any_token", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/token/all')
async def deleteAllToken(request: Request, response: Response, authorization: str = Header(None), \
        last_used_before: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /token/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if last_used_before == -1:
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE discordid = {discordid}")
        await aiosql.commit(dhrid)
    else:
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE discordid = {discordid} AND last_used_timestamp <= {last_used_before}")
        await aiosql.commit(dhrid)

    return {"error": False}

@app.get(f'/{config.abbr}/token/application/list')
async def getApplicationTokenList(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /token/application/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
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
        WHERE discordid = {discordid} ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        tk = sha256(tt[1].encode()).hexdigest()
        ret.append({"app_name": tt[0], "hash": tk, "create_timestamp": str(tt[2]), "last_used_timestamp": str(tt[3])})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application_token WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.post(f'/{config.abbr}/token/application')
async def postApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    form = await request.form()

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    try:
        app_name = convert_quotation(form["app_name"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    
    if len(app_name) >= 128:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "app_name", "limit": "128"}, force_lang = au["language"])}

    stoken = str(uuid.uuid4())
    await aiosql.execute(dhrid, f"INSERT INTO application_token VALUES ('{app_name}', '{stoken}', {discordid}, {int(time.time())}, 0)")
    await aiosql.commit(dhrid)
    
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.abbr}/token/application')
async def deleteApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    form = await request.form()
    try:
        hsh = form["hash"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    ok = False
    await aiosql.execute(dhrid, f"SELECT token FROM application_token WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE token = '{tt[0]}' AND discordid = {discordid}")
            await aiosql.commit(dhrid)
            break
    
    if ok:
        return {"error": False}
    else:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "hash_does_not_match_any_token", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/token/application/all')
async def deleteAllApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /token/application/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE discordid = {discordid}")
    await aiosql.commit(dhrid)

    return {"error": False}

# Multiple Factor Authentication
@app.post(f"/{config.abbr}/auth/mfa")
async def postMFA(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /auth/mfa', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    form = await request.form()
    try:
        tip = form["token"]
        otp = int(form["otp"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form")}

    await aiosql.execute(dhrid, f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT discordid FROM temp_identity_proof WHERE token = '{tip}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0 or not tip.startswith("f"):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_token")}
    discordid = t[0][0]
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    secret = t[0][0]
    if secret == "":
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "mfa_not_enabled")}
        
    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp")}

    await aiosql.execute(dhrid, f"DELETE FROM temp_identity_proof WHERE token = '{tip}'")
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}

    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4()) # All MFA logins won't be counted as unsafe
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)
    username = (await getUserInfo(dhrid, discordid = discordid))["name"]
    language = await GetUserLanguage(dhrid, discordid)
    await AuditLog(dhrid, -999, f"MFA login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    await notification(dhrid, "login", discordid, \
        ml.tr(request, "new_login", \
            var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), \
            "description": "", \
            "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"error": False, "response": {"token": stoken}}