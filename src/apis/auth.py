# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from pysteamsignin.steamsignin import SteamSignIn
from uuid import uuid4
from hashlib import sha256
import json, time, requests
import bcrypt, re, base64

from app import app, config
from db import newconn
from functions import *
import multilang as ml

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
    rl = ratelimit(request, request.client.host, 'POST /auth/password', 60, 3)
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

    r = requests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response})
    d = json.loads(r.text)
    if not d["success"]:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "invalid_captcha")}
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, password FROM user_password WHERE email = '{email}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_email_or_password")}
    discordid = t[0][0]
    pwdhash = t[0][1]
    ok = bcrypt.checkpw(password, b64d(pwdhash).encode())
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_email_or_password")}
    
    cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    if config.in_guild_check and config.discord_bot_token != "":
        try:
            r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"})
        except:
            import traceback
            traceback.print_exc()
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        if r.status_code == 404:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)
        if r.status_code != 200:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        d = json.loads(r.text)
        if not "user" in d.keys():
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid4())
        stoken = "f" + stoken[1:]
        cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
        conn.commit()
        return {"error": False, "response": {"token": stoken, "mfa": True}}

    cur.execute(f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)
        
    stoken = str(uuid4())
    stoken = "e" + stoken[1:]
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 50:
        cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 49}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    conn.commit()

    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(-999, f"Password login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    notification(discordid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = GetUserLanguage(discordid)))

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

    rl = ratelimit(request, request.client.host, 'GET /auth/discord/callback', 60, 10)
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
            conn = newconn()
            cur = conn.cursor()
            cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
            cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
            cur.execute(f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
            t = cur.fetchall()
            if len(t) > 0:
                reason = t[0][0]
                expire = t[0][1]
                expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
                return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)

            cur.execute(f"SELECT * FROM user WHERE discordid = '{discordid}'")
            t = cur.fetchall()
            username = str(user_data['username'])
            username = convert_quotation(username).replace(",","")
            email = str(user_data['email'])
            email = convert_quotation(email)
            if not "@" in email: # make sure it's not empty
                return RedirectResponse(url=getUrl4Msg(ml.tr(request, "invalid_email")), status_code=302)
            avatar = str(user_data['avatar'])
            if len(t) == 0:
                cur.execute(f"INSERT INTO user VALUES (-1, {discordid}, '{username}', '{avatar}', '',\
                    '{email}', -1, -1, '', {int(time.time())}, '')")
                await AuditLog(-999, f"User register: `{username}` (Discord ID: `{discordid}`)")
            else:
                cur.execute(f"UPDATE user_password SET email = '{email}' WHERE discordid = '{discordid}'")
                cur.execute(f"UPDATE user SET name = '{username}', avatar = '{avatar}', email = '{email}' WHERE discordid = '{discordid}'")
            conn.commit()
            
            if config.in_guild_check and config.discord_bot_token != "":
                try:
                    r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"})
                except:
                    import traceback
                    traceback.print_exc()
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
                if r.status_code == 404:
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)
                if r.status_code != 200:
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
                d = json.loads(r.text)
                if not "user" in d.keys():
                    return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)

            cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
            t = cur.fetchall()
            mfa_secret = t[0][0]
            if mfa_secret != "":
                stoken = str(uuid4())
                stoken = "f" + stoken[1:]
                cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
                conn.commit()
                return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

            stoken = str(uuid4())
            while stoken[0] == "e":
                stoken = str(uuid4())
            cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
            r = cur.fetchall()
            scnt = r[0][0]
            if scnt >= 50:
                cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 49}")
            cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
            conn.commit()
            username = getUserInfo(discordid = discordid)["name"]
            await AuditLog(-999, f"Discord login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
            notification(discordid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = GetUserLanguage(discordid)))
            return RedirectResponse(url=getUrl4Token(stoken), status_code=302)
        
        if 'error_description' in tokens.keys():
            return RedirectResponse(url=getUrl4Msg(tokens['error_description']), status_code=302)
        else:
            return RedirectResponse(url=getUrl4Msg(ml.tr("unknown_error")), status_code=302)

    except:
        import traceback
        traceback.print_exc()
        return RedirectResponse(url=getUrl4Msg(ml.tr("unknown_error")), status_code=302)

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

    rl = ratelimit(request, request.client.host, 'GET /auth/steam/callback', 60, 10)
    if rl[0]:
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "rate_limit")), status_code=302)

    r = requests.get("https://steamcommunity.com/openid/login?" + data)
    if r.status_code != 200:
        response.status_code = 503
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "steam_api_error")), status_code=302)
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "invalid_steam_auth")), status_code=302)
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM user WHERE steamid = '{steamid}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "user_not_found")), status_code=302)
    discordid = t[0][0]
    
    cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
    cur.execute(f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)

    if config.in_guild_check and config.discord_bot_token != "":
        try:
            r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"})
        except:
            import traceback
            traceback.print_exc()
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        if r.status_code == 404:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)
        if r.status_code != 200:
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "discord_check_fail")), status_code=302)
        d = json.loads(r.text)
        if not "user" in d.keys():
            return RedirectResponse(url=getUrl4Msg(ml.tr(request, "must_join_discord")), status_code=302)

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid4())
        stoken = "f" + stoken[1:]
        cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+600})") # 10min tip
        conn.commit()
        return RedirectResponse(url=getUrl4MFA(stoken), status_code=302)

    stoken = str(uuid4())
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 50:
        cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 49}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    conn.commit()
    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(-999, f"Steam login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    notification(discordid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = GetUserLanguage(discordid)))

    return RedirectResponse(url=getUrl4Token(stoken), status_code=302)

# Token Management
@app.get(f'/{config.abbr}/token')
async def getToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'GET /token', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    token_type = authorization.split(" ")[0].lower()

    return {"error": False, "response": {"token_type": token_type}}

@app.patch(f"/{config.abbr}/token")
async def patchToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    stoken = authorization.split(" ")[1]

    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid4())
    while stoken[0] == "e":
        stoken = str(uuid4())
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    conn.commit()
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.abbr}/token')
async def deleteToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    conn = newconn()
    cur = conn.cursor()

    stoken = authorization.split(" ")[1]

    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    conn.commit()

    return {"error": False}

@app.get(f'/{config.abbr}/token/list')
async def getAllToken(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    rl = ratelimit(request, request.client.host, 'GET /token/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
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
        
    conn = newconn()
    cur = conn.cursor()

    ret = []
    cur.execute(f"SELECT token, ip, timestamp, country, user_agent, last_used_timestamp FROM session \
        WHERE discordid = {discordid} ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    for tt in t:
        tk = tt[0]
        tk = sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "country": getFullCountry(tt[3]), "user_agent": tt[4], "create_timestamp": str(tt[2]), "last_used_timestamp": str(tt[5])})
    
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = {discordid}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.delete(f'/{config.abbr}/token/hash')
async def deleteTokenHash(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /token/hash', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
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

    conn = newconn()
    cur = conn.cursor()
    ok = False
    cur.execute(f"SELECT token FROM session WHERE discordid = {discordid}")
    t = cur.fetchall()
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            cur.execute(f"DELETE FROM session WHERE token = '{tt[0]}' AND discordid = {discordid}")
            conn.commit()

    if ok:
        return {"error": False}
    else:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "hash_does_not_match_any_token", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/token/all')
async def deleteAllToken(request: Request, response: Response, authorization: str = Header(None), \
        last_used_before: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /token/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()

    if last_used_before == -1:
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()
    else:
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid} AND last_used_timestamp <= {last_used_before}")
        conn.commit()

    return {"error": False}

@app.patch(f'/{config.abbr}/token/application')
async def patchApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    stoken = str(uuid4())
    cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
    cur.execute(f"INSERT INTO appsession VALUES ('{stoken}', {discordid}, {int(time.time())})")
    conn.commit()
    
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.abbr}/token/application')
async def deleteApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
    conn.commit()
    
    return {"error": False}

# Temporary Identity Proof
@app.put(f"/{config.abbr}/auth/tip")
async def putTemporaryIdentityProof(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PUT /auth/tip', 180, 20)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    stoken = str(uuid4())
    while stoken[0] == "f":
        stoken = str(uuid4())
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+180})")
    conn.commit()

    return {"error": False, "response": {"token": stoken}}

@app.get(f"/{config.abbr}/auth/tip")
async def getTemporaryIdentityProof(request: Request, response: Response, token: Optional[str] = ""):
    rl = ratelimit(request, request.client.host, 'GET /auth/tip', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    token = token.replace("'","")

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"SELECT discordid FROM temp_identity_proof WHERE token = '{token}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_token")}
    cur.execute(f"DELETE FROM temp_identity_proof WHERE token = '{token}'")
    conn.commit()
    return {"error": False, "response": {"user": getUserInfo(discordid = t[0][0])}}

# Multiple Factor Authentication
@app.put(f"/{config.abbr}/auth/mfa")
async def putMFA(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PUT /auth/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    secret = t[0][0]
    if secret != "":
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "mfa_already_enabled", force_lang = au["language"])}
    
    form = await request.form()
    try:
        secret = form["secret"]
        otp = int(form["otp"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if len(secret) != 16 or not secret.isalnum():
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}
    
    try:
        base64.b32decode(secret)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}

    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    cur.execute(f"UPDATE user SET mfa_secret = '{secret}' WHERE discordid = {discordid}")
    conn.commit()
        
    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(-999, f"Enabled MFA for `{username}` (Discord ID: `{discordid}`)")

    return {"error": False}

@app.post(f"/{config.abbr}/auth/mfa")
async def postMFA(request: Request, response: Response):
    rl = ratelimit(request, request.client.host, 'POST /auth/mfa', 60, 3)
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
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"SELECT discordid FROM temp_identity_proof WHERE token = '{tip}'")
    t = cur.fetchall()
    if len(t) == 0 or not tip.startswith("f"):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_token")}
    discordid = t[0][0]
    
    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
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

    cur.execute(f"DELETE FROM temp_identity_proof WHERE token = '{tip}'")
    cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
    cur.execute(f"SELECT reason, expire_timestamp FROM banned WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
        return RedirectResponse(url=getUrl4Msg(ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})), status_code=302)

    stoken = str(uuid4())
    while stoken.startswith("e"):
        stoken = str(uuid4()) # All MFA logins won't be counted as unsafe
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 50:
        cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 49}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    conn.commit()
    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(-999, f"2FA login: `{username}` (Discord ID: `{discordid}`) from `{getRequestCountry(request)}`")
    notification(discordid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = GetUserLanguage(discordid)))

    return {"error": False, "response": {"token": stoken}}

@app.delete(f"/{config.abbr}/auth/mfa")
async def deleteMFA(request: Request, response: Response, authorization: str = Header(None), discordid: Optional[str] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /auth/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if discordid == -1:
        # self-disable mfa
        au = auth(authorization, request, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        discordid = au["discordid"]
        
        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "mfa_not_enabled", force_lang = au["language"])}
    
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        if not valid_totp(otp, secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        cur.execute(f"UPDATE user SET mfa_secret = '' WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(-999, f"Disabled MFA for `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}
    
    else:
        # admin / hrm disable user mfa
        au = auth(authorization, request, required_permission = ["admin", "hrm", "disable_user_mfa"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "mfa_not_enabled")}
        
        cur.execute(f"UPDATE user SET mfa_secret = '' WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(adminid, f"Disabled MFA for `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}