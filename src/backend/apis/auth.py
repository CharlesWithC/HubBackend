# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from pysteamsignin.steamsignin import SteamSignIn
from uuid import uuid4
import json, time, requests, validators

from app import app, config
from db import newconn
from functions import *

client_id = config.discord_client_id
client_secret = config.discord_client_secret
oauth2_url = config.discord_oauth2_url
callback_url = config.discord_callback_url
dhdomain = config.dhdomain

discord_auth = DiscordAuth(client_id, client_secret, callback_url)

@app.get('/atm/user/login', response_class=RedirectResponse)
async def userLogin(request: Request):
    # login_url = discord_auth.login()
    return RedirectResponse(url=oauth2_url, status_code=302)
    
@app.get('/atm/user/callback')
async def userCallback(code: str, request: Request, response: Response):
    tokens = discord_auth.get_tokens(code)
    if "access_token" in tokens.keys():
        user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
        tokens = {**tokens, **user_data}
        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 7}")
        cur.execute(f"DELETE FROM banned WHERE expire < {int(time.time())}")
        stoken = str(uuid4())
        cur.execute(f"SELECT reason, expire FROM banned WHERE discordid = '{user_data['id']}'")
        t = cur.fetchall()
        if len(t) > 0:
            reason = t[0][0]
            expire = t[0][1]
            expire = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))
            return RedirectResponse(url=f"https://{dhdomain}/auth?message=You are banned for {reason} until {expire} UTC", status_code=302)

        r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild}/members/{user_data['id']}", headers={"Authorization": f"Bot {config.bottoken}"})
        if r.status_code != 200:
            return RedirectResponse(url=f"https://{dhdomain}/auth?message=Failed to check if you are in discord.", status_code=302)
        d = json.loads(r.text)
        if not "user" in d.keys():
            return RedirectResponse(url=f"https://{dhdomain}/auth?message=You are not in our discord server.", status_code=302)

        cur.execute(f"SELECT * FROM user WHERE discordid = '{user_data['id']}'")
        t = cur.fetchall()
        username = user_data['username']
        username = username.replace("'", "''").replace(",","")
        email = user_data['email']
        email = email.replace("'", "''")
        if len(t) == 0:
            cur.execute(f"INSERT INTO user VALUES (-1, {user_data['id']}, '{username}', '{user_data['avatar']}', '',\
                '{email}', 0, 0, '', {int(time.time())})")
            await AuditLog(-999, f"User register: {username} (`{user_data['id']}`)\nUser must be added to member list by staff manually.")
        else:
            cur.execute(f"UPDATE user SET name = '{username}', avatar = '{user_data['avatar']}', email = '{email}' WHERE discordid = '{user_data['id']}'")
        cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{user_data['id']}', '{int(time.time())}', '{request.client.host}')")
        conn.commit()
        user_data["token"] = stoken
        return RedirectResponse(url=f"https://{dhdomain}/auth?token="+stoken, status_code=302)
    # response.status_code = 401
    return RedirectResponse(url=f"https://{dhdomain}/auth?message={tokens['error_description']}", status_code=302)

@app.get("/atm/user/refresh")
async def userRefreshToken(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid4())
    cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{discordid}', '{int(time.time())}', '{request.client.host}')")
    conn.commit()
    return {"error": False, "response": {"token": stoken}}

@app.get('/atm/user/validate')
async def userValidate(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT steamid, truckersmpid FROM user WHERE discordid = '{t[0][0]}'")
    t = cur.fetchall()
    steamid = t[0][0]
    truckersmpid = t[0][1]
    extra = ""
    if steamid == 0:
        extra = "steamauth"
    elif truckersmpid == 0:
        extra = "truckersmp"
    return {"error": False, "response": {"message": "Validated", "discordid": f"{discordid}", "ip": ip, "extra": extra}}

@app.get("/atm/user/steamauth")
async def steamOpenid(request: Request, response: Response):
    steamLogin = SteamSignIn()
    encodedData = steamLogin.ConstructURL('https://drivershub.charlws.com/atm/user/steamcallback')
    url = 'https://steamcommunity.com/openid/login?' + encodedData
    return RedirectResponse(url=url, status_code=302)

@app.get("/atm/user/steamcallback")
async def steamCallback(request: Request, response: Response):
    return RedirectResponse(url=f"https://{dhdomain}/steamcallback?{str(request.query_params)}", status_code=302)

@app.post("/atm/user/steambind")
async def steamBind(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    openid = form["openid"].replace("openid.mode=id_res", "openid.mode=check_authentication")
    r = requests.get("https://steamcommunity.com/openid/login?" + openid)
    if r.status_code != 200:
        # response.status_code = 503
        return {"error": True, "descriptor": "503: Steam servers are down"}
    if r.text.find("is_valid:true") == -1:
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid steam authentication."}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    cur.execute(f"SELECT * FROM user WHERE discordid != '{discordid}' AND steamid = {steamid}")
    t = cur.fetchall()
    if len(t) > 0:
        return {"error": True, "descriptor": "Steam account already bound to another user."}

    cur.execute(f"UPDATE user SET steamid = {steamid} WHERE discordid = '{discordid}'")
    conn.commit()

    r = requests.get(f"https://api.truckyapp.com/v2/truckersmp/player?playerID={steamid}")
    if r.status_code == 200:
        d = json.loads(r.text)
        if not d["response"]["error"]:
            truckersmpid = d["response"]["response"]["id"]
            r = requests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid))
            if r.status_code == 200:
                d = json.loads(r.text)
                if not d["error"]:
                    tmpsteamid = d["response"]["steamID64"]
                    if str(tmpsteamid) == str(steamid):
                        cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
                        conn.commit()
                        return {"error": False, "response": {"message": "Steam account bound.", "steamid": steamid, "skiptmp": True}}

    return {"error": False, "response": {"message": "Steam account bound.", "steamid": steamid}}

@app.post("/atm/user/truckersmpbind")
async def truckersmpBind(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    truckersmpid = form["truckersmpid"]
    try:
        truckersmpid = int(truckersmpid)
    except:
        # response.status_code = 400
        return {"error": True, "descriptor": "Invalid TruckersMP ID."}

    r = requests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid))
    if r.status_code != 200:
        # response.status_code = 503
        return {"error": True, "descriptor": "503: TruckersMP servers are down"}
    d = json.loads(r.text)
    if d["error"]:
        # response.status_code = 400
        return {"error": True, "descriptor": "Invalid TruckersMP ID."}

    cur.execute(f"SELECT steamid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 400
        return {"error": True, "descriptor": "Steam account not bound."}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    tmpname = d["response"]["name"]
    if tmpsteamid != steamid:
        # response.status_code = 400
        return {"error": True, "descriptor": f"Steam account bound to TruckersMP User {tmpname} ({truckersmpid}) does not match your steam account."}

    cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
    conn.commit()
    return {"error": False, "response": {"message": "TruckersMP account bound.", "truckersmpid": truckersmpid}}

@app.post('/atm/user/revoke')
async def userRevoke(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    conn.commit()
    return {"error": False, "response": {"message": "Token revoked"}}

@app.post('/atm/user/apptoken')
async def userBot(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    stoken = str(uuid4())
    cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
    cur.execute(f"INSERT INTO appsession VALUES ('{stoken}', {discordid}, {int(time.time())})")
    conn.commit()
    return {"error": False, "response": {"message": "Application token updated", "token": stoken}}