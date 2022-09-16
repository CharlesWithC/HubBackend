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
import bcrypt, re

from app import app, config
from db import newconn
from functions import *
import multilang as ml

discord_auth = DiscordAuth(config.discord_client_id, config.discord_client_secret, config.discord_callback_url)

# Password Auth
@app.post(f'/{config.vtc_abbr}/auth/password')
async def postAuthPassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /auth/password', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}
    
    form = await request.form()
    try:
        email = str(form["email"]).replace("'", "''")    
        password = str(form["password"]).encode('utf-8')
        hcaptcha_response = form["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

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
    
    stoken = str(uuid4())
    stoken = "e" + stoken[1:]
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 10:
        cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 9}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}')")
    conn.commit()

    return {"error": False, "response": {"token": stoken}}

# Discord Auth
@app.get(f'/{config.vtc_abbr}/auth/discord/redirect', response_class=RedirectResponse)
async def getAuthDiscordRedirect(request: Request):
    # login_url = discord_auth.login()
    return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
@app.get(f'/{config.vtc_abbr}/auth/discord/callback')
async def getAuthDiscordCallback(request: Request, response: Response, code: Optional[str] = "", error_description: Optional[str] = ""):
    referer = request.headers.get("Referer")
    if referer != "https://discord.com/":
        return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
    if code == "":
        return RedirectResponse(url=f"https://{config.domain}/auth?message={error_description}", status_code=302)

    rl = ratelimit(request.client.host, 'GET /auth/discord/callback', 150, 3)
    if rl > 0:
        return RedirectResponse(url=f"https://{config.domain}/auth?message=" + f"Rate limit: Wait {rl} seconds", status_code=302)

    tokens = discord_auth.get_tokens(code)
    if "access_token" in tokens.keys():
        user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
        if not 'id' in user_data:
            return RedirectResponse(url=f"https://{config.domain}/auth?message=Discord Error: " + user_data['message'], status_code=302)

        tokens = {**tokens, **user_data}
        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 7}")
        cur.execute(f"DELETE FROM banned WHERE expire < {int(time.time())}")
        cur.execute(f"SELECT reason, expire FROM banned WHERE discordid = '{user_data['id']}'")
        t = cur.fetchall()
        if len(t) > 0:
            reason = t[0][0]
            expire = t[0][1]
            expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
            return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire}), status_code=302)

        cur.execute(f"SELECT * FROM user WHERE discordid = '{user_data['id']}'")
        t = cur.fetchall()
        username = str(user_data['username'])
        username = username.replace("'", "''").replace(",","")
        email = str(user_data['email'])
        email = email.replace("'", "''")
        if not "@" in email: # make sure it's not empty
            return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "invalid_email"), status_code=302)
        avatar = str(user_data['avatar'])
        if len(t) == 0:
            cur.execute(f"INSERT INTO user VALUES (-1, {user_data['id']}, '{username}', '{avatar}', '',\
                '{email}', -1, -1, '', {int(time.time())})")
            await AuditLog(-999, f"User register: {username} (`{user_data['id']}`)")
        else:
            cur.execute(f"UPDATE user_password SET email = '{email}' WHERE discordid = '{user_data['id']}'")
            cur.execute(f"UPDATE user SET name = '{username}', avatar = '{avatar}', email = '{email}' WHERE discordid = '{user_data['id']}'")
        conn.commit()
        
        if config.in_guild_check:
            r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{user_data['id']}", headers={"Authorization": f"Bot {config.discord_bot_token}"})
            if r.status_code != 200:
                return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "discord_check_fail"), status_code=302)
            d = json.loads(r.text)
            if not "user" in d.keys():
                return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "not_in_discord_server"), status_code=302)

        stoken = str(uuid4())
        while stoken[0] == "e":
            stoken = str(uuid4())
        cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{user_data['id']}'")
        r = cur.fetchall()
        scnt = r[0][0]
        if scnt >= 10:
            cur.execute(f"DELETE FROM session WHERE discordid = '{user_data['id']}' LIMIT {scnt - 9}")
        cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{user_data['id']}', '{int(time.time())}', '{request.client.host}')")
        conn.commit()
        return RedirectResponse(url=f"https://{config.domain}/auth?token="+stoken, status_code=302)
        
    return RedirectResponse(url=f"https://{config.domain}/auth?message={tokens['error_description']}", status_code=302)

# Steam Auth (Only for connecting account)
@app.get(f"/{config.vtc_abbr}/auth/steam/redirect")
async def getSteamOAuth(request: Request, response: Response, connect_account: Optional[bool] = False):
    steamLogin = SteamSignIn()
    encodedData = ""
    if not connect_account:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.vtc_abbr}/auth/steam/callback')
    else:
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.vtc_abbr}/auth/steam/connect')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

@app.get(f"/{config.vtc_abbr}/auth/steam/connect")
async def getSteamConnect(request: Request, response: Response):
    return RedirectResponse(url=config.steam_callback_url + f"?{str(request.query_params)}", status_code=302)

@app.get(f"/{config.vtc_abbr}/auth/steam/callback")
async def getSteamCallback(request: Request, response: Response):
    referer = request.headers.get("Referer")
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if referer != "https://steamcommunity.com/" or data == "":
        steamLogin = SteamSignIn()
        encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.vtc_abbr}/auth/steam/callback')
        url = 'https://steamcommunity.com/openid/login?' + encodedData
        return RedirectResponse(url=url, status_code=302)

    rl = ratelimit(request.client.host, 'GET /auth/steam/callback', 150, 3)
    if rl > 0:
        return RedirectResponse(url=f"https://{config.domain}/auth?message=" + f"Rate limit: Wait {rl} seconds", status_code=302)

    r = requests.get("https://steamcommunity.com/openid/login?" + data)
    if r.status_code != 200:
        response.status_code = 503
        return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "steam_api_error"), status_code=302)
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "invalid_steam_auth"), status_code=302)
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM user WHERE steamid = '{steamid}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return RedirectResponse(url=f"https://{config.domain}/auth?message=" + ml.tr(request, "user_not_found"), status_code=302)
    discordid = t[0][0]

    stoken = str(uuid4())
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{discordid}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 10:
        cur.execute(f"DELETE FROM session WHERE discordid = '{discordid}' LIMIT {scnt - 9}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}')")
    conn.commit()

    return RedirectResponse(url=f"https://{config.domain}/auth?token=" + stoken, status_code=302)

# Token Management
@app.get(f'/{config.vtc_abbr}/token')
async def getToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /token', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au

    token_type = authorization.split(" ")[0].lower()

    return {"error": False, "response": {"token_type": token_type}}

@app.patch(f"/{config.vtc_abbr}/token")
async def patchToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /token', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    stoken = authorization.split(" ")[1]

    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid4())
    while stoken[0] == "e":
        stoken = str(uuid4())
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}')")
    conn.commit()
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.vtc_abbr}/token')
async def deleteToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()

    stoken = authorization.split(" ")[1]

    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    conn.commit()

    return {"error": False}

@app.get(f'/{config.vtc_abbr}/token/all')
async def getAllToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /token/all', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    ret = []
    cur.execute(f"SELECT token, ip, timestamp FROM session WHERE discordid = {discordid}")
    t = cur.fetchall()
    for tt in t:
        tk = tt[0]
        tk = sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "timestamp": str(tt[2])})

    return {"error": False, "response": {"list": ret}}

@app.delete(f'/{config.vtc_abbr}/token/hash')
async def deleteTokenHash(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token/hash', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "oauth_login_required")}

    form = await request.form()
    try:
        hsh = form["hash"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

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
        return {"error": True, "descriptor": ml.tr(request, "hash_does_not_match_any_token")}

@app.delete(f'/{config.vtc_abbr}/token/all')
async def deleteAllToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token/all', 180, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "oauth_login_required")}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False}

@app.patch(f'/{config.vtc_abbr}/token/application')
async def patchApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /token/application', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    stoken = str(uuid4())
    cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
    cur.execute(f"INSERT INTO appsession VALUES ('{stoken}', {discordid}, {int(time.time())})")
    conn.commit()
    
    return {"error": False, "response": {"token": stoken}}

@app.delete(f'/{config.vtc_abbr}/token/application')
async def deleteApplicationToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token/application', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
    conn.commit()
    
    return {"error": False}

# Temporary Identity Proof
@app.put(f"/{config.vtc_abbr}/auth/tip")
async def putTemporaryIdentityProof(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PUT /auth/tip', 180, 5)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    stoken = str(uuid4())
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+180})")
    conn.commit()

    return {"error": False, "response": {"token": stoken}}

@app.get(f"/{config.vtc_abbr}/auth/tip")
async def getTemporaryIdentityProof(request: Request, response: Response, token: Optional[str] = ""):
    rl = ratelimit(request.client.host, 'GET /auth/tip', 60, 120)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    token = token.replace("'","")

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM temp_identity_proof WHERE token = '{token}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid token"}
    cur.execute(f"DELETE FROM temp_identity_proof WHERE token = '{token}'")
    conn.commit()
    return {"error": False, "response": {"discordid": int(t[0][0])}}