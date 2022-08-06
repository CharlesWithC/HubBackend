# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from pysteamsignin.steamsignin import SteamSignIn
from uuid import uuid4
import json, time, requests
import bcrypt, re
import hashlib

from app import app, config
from db import newconn
from functions import *
import multilang as ml

client_id = config.discord_client_id
client_secret = config.discord_client_secret
oauth2_url = config.discord_oauth2_url
callback_url = config.discord_callback_url
dhdomain = config.domain

discord_auth = DiscordAuth(client_id, client_secret, callback_url)

@app.get(f'/{config.vtc_abbr}/user/login', response_class=RedirectResponse)
async def userLogin(request: Request):
    # login_url = discord_auth.login()
    return RedirectResponse(url=oauth2_url, status_code=302)
    
@app.get(f'/{config.vtc_abbr}/user/callback')
async def userCallback(request: Request, response: Response, code: Optional[str] = "", error: Optional[str] = "", error_description: Optional[str] = ""):
    referer = request.headers.get("Referer")
    if referer != "https://discord.com/":
        return RedirectResponse(url=config.discord_oauth2_url, status_code=302)
    
    if code == "":
        return RedirectResponse(url=f"https://{dhdomain}/auth?message={error_description}", status_code=302)

    rl = ratelimit(request.client.host, 'GET /user/callback', 60, 3)
    if rl > 0:
        return RedirectResponse(url=f"https://{dhdomain}/auth?message=" + f"Rate limit: Wait {rl} seconds", status_code=302)

    tokens = discord_auth.get_tokens(code)
    if "access_token" in tokens.keys():
        user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
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
            return RedirectResponse(url=f"https://{dhdomain}/auth?message=" + ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire}), status_code=302)

        cur.execute(f"SELECT * FROM user WHERE discordid = '{user_data['id']}'")
        t = cur.fetchall()
        username = str(user_data['username'])
        username = username.replace("'", "''").replace(",","")
        email = str(user_data['email'])
        email = email.replace("'", "''")
        if not "@" in email: # make sure it's not empty
            return RedirectResponse(url=f"https://{dhdomain}/auth?message=" + ml.tr(request, "invalid_email"), status_code=302)
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
                return RedirectResponse(url=f"https://{dhdomain}/auth?message=" + ml.tr(request, "discord_check_fail"), status_code=302)
            d = json.loads(r.text)
            if not "user" in d.keys():
                return RedirectResponse(url=f"https://{dhdomain}/auth?message=" + ml.tr(request, "not_in_discord_server"), status_code=302)

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
        return RedirectResponse(url=f"https://{dhdomain}/auth?token="+stoken, status_code=302)
        
    return RedirectResponse(url=f"https://{dhdomain}/auth?message={tokens['error_description']}", status_code=302)

@app.post(f'/{config.vtc_abbr}/user/login/password')
async def passwordLogin(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/login/password', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}
    
    form = await request.form()
    email = form["email"].replace("'", "''")    
    password = form["password"].encode('utf-8')
    hcaptcha_response = form["h-captcha-response"]

    r = requests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response})
    d = json.loads(r.text)
    if not d["success"]:
        response.status_code = 401
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
    cur.execute(f"SELECT COUNT(*) FROM session WHERE discordid = '{user_data['id']}'")
    r = cur.fetchall()
    scnt = r[0][0]
    if scnt >= 10:
        cur.execute(f"DELETE FROM session WHERE discordid = '{user_data['id']}' LIMIT {scnt - 9}")
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}')")
    conn.commit()

    return {"error": False, "response": {"token": stoken}}
    
@app.patch(f'/{config.vtc_abbr}/user/password')
async def patchPassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/password', 60, 3)
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
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_to_change_password")}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    form = await request.form()
    password = form["password"]
    if password == "":
        cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
        conn.commit()
        return {"error": False}

    if not "@" in email: # make sure it's not empty
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "invalid_email")}
        
    cur.execute(f"SELECT userid FROM user WHERE email = '{email}'")
    t = cur.fetchall()
    if len(t) > 1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "too_many_user_with_same_email")}
        
    if len(password)>=8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": True, "descriptor": ml.tr(request, "weak_password")}
    else:
        return {"error": True, "descriptor": ml.tr(request, "weak_password")}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    cur.execute(f"INSERT INTO user_password VALUES ({discordid}, '{email}', '{b64e(pwdhash)}')")
    conn.commit()

    return {"error": False}

@app.get(f'/{config.vtc_abbr}/token')
async def getToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /token', 60, 60)
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

    cur.execute(f"SELECT steamid, truckersmpid, joints FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    steamid = t[0][0]
    truckersmpid = t[0][1]
    joints = t[0][2]
    extra = ""
    if truckersmpid <= 0:
        extra = "truckersmp"
        cur.execute(f"UPDATE user SET truckersmpid = 0 WHERE discordid = '{discordid}'")
    if steamid <= 0:
        extra = "steamauth"
        cur.execute(f"UPDATE user SET steamid = 0 WHERE discordid = '{discordid}'")
    conn.commit()
    if steamid == -1 or truckersmpid == -1:
        extra = ""
    if steamid > 0 and not config.truckersmp_bind:
        extra = ""
    return {"error": False, "response": {"discordid": f"{discordid}", "note": extra}}

@app.patch(f"/{config.vtc_abbr}/token")
async def patchToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /token', 60, 3)
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
    rl = ratelimit(request.client.host, 'DELETE /token', 60, 60)
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
async def deleteToken(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /token/all', 60, 60)
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
        tk = hashlib.sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "timestamp": tt[2]})

    return {"error": False, "response": {"list": ret}}

@app.delete(f'/{config.vtc_abbr}/token/hash')
async def deleteTokenHash(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token/hash', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    form = await request.form()
    hsh = form["hash"]

    conn = newconn()
    cur = conn.cursor()
    ok = False
    cur.execute(f"SELECT token FROM session WHERE discordid = {discordid}")
    t = cur.fetchall()
    for tt in t:
        thsh = hashlib.sha256(tt[0].encode()).hexdigest()
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
async def deleteTokenAll(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /token/all', 60, 60)
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

    cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False}

@app.get(f"/{config.vtc_abbr}/user/steam/oauth")
async def getSteamOAuth(request: Request, response: Response):
    rl = ratelimit(request.client.host, 'GET /user/steam/oauth', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    steamLogin = SteamSignIn()
    encodedData = steamLogin.ConstructURL(f'https://{config.apidomain}/{config.vtc_abbr}/user/steam/callback')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

@app.get(f"/{config.vtc_abbr}/user/steam/callback")
async def getSteamCallback(request: Request, response: Response):
    return RedirectResponse(url=config.steam_callback_url + f"?{str(request.query_params)}", status_code=302)

@app.patch(f"/{config.vtc_abbr}/user/steam")
async def patchSteam(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/steam', 180, 3)
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

    form = await request.form()
    openid = form["openid"].replace("openid.mode=id_res", "openid.mode=check_authentication")
    r = requests.get("https://steamcommunity.com/openid/login?" + openid)
    if r.status_code != 200:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "steam_api_error")}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_steam_auth")}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    cur.execute(f"SELECT * FROM user WHERE discordid != '{discordid}' AND steamid = {steamid}")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "steam_bound_to_other_account")}

    cur.execute(f"SELECT roles, steamid, userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    while "" in roles:
        roles.remove("")
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid != 0 and userid >= 0:
        cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%Steam ID updated from%' AND userid = {userid} AND timestamp >= {int(time.time() - 86400 * 7)}")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 429
            return {"error": True, "descriptor": ml.tr(request, "steam_updated_within_7d")}

        for role in roles:
            if role == "100":
                requests.delete(f"https://api.navio.app/v1/drivers/{orgsteamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
                requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
                await AuditLog(userid, f"Steam ID updated from `{orgsteamid}` to `{steamid}`")

    cur.execute(f"UPDATE user SET steamid = {steamid} WHERE discordid = '{discordid}'")
    conn.commit()

    r = requests.get(f"https://api.truckersmp.com/v2/player/{steamid}")
    if r.status_code == 200:
        d = json.loads(r.text)
        if not d["error"]:
            truckersmpid = d["response"]["id"]
            cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
            conn.commit()
            return {"error": False, "response": {"steamid": str(steamid), "skiptmp": True}}

    # in case user changed steam
    cur.execute(f"UPDATE user SET truckersmpid = 0 WHERE discordid = '{discordid}'")
    conn.commit()
    
    return {"error": False, "response": {"steamid": str(steamid)}}

@app.patch(f"/{config.vtc_abbr}/user/truckersmp")
async def patchTruckersMP(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/truckersmp', 180, 3)
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

    form = await request.form()
    truckersmpid = form["truckersmpid"]
    try:
        truckersmpid = int(truckersmpid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id")}

    r = requests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid))
    if r.status_code != 200:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_api_error")}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id")}

    cur.execute(f"SELECT steamid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "steam_not_bound_before_truckersmp")}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    tmpname = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_steam_mismatch", var = {"tmpname": tmpname, "truckersmpid": str(truckersmpid)})}

    cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
    conn.commit()
    return {"error": False, "response": {"truckersmpid": str(truckersmpid)}}

@app.patch(f'/{config.vtc_abbr}/token/application')
async def userBot(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/apptoken', 60, 10)
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