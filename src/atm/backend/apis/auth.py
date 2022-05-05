# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from uuid import uuid4
import json, time

from app import app, config
from db import newconn
from functions import *

client_id = config.discord_client_id
client_secret = config.discord_client_secret
oauth2_url = config.discord_oauth2_url
callback_url = config.discord_callback_url
dhdomain = config.dhdomain

discord_auth = DiscordAuth(client_id, client_secret, callback_url)

@app.get('/atm/user/info')
async def user(response: Response, authorization: Optional[str] = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT data FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    data = json.loads(b64d(t[0][0]))
    access_token = data["access_token"]
    user_data = discord_auth.get_user_data_from_token(access_token)
    cur.execute(f"SELECT memberid FROM member WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) > 0:
        user_data["memberid"] = t[0][0]
    else:
        user_data["memberid"] = None
    if "message" in user_data.keys():
        response.status_code = 401
        return {"error": True, "descriptor": user_data["message"]}
    return {"error": False, "response": user_data}

@app.get('/atm/user/login', response_class=RedirectResponse)
async def home():
    # login_url = discord_auth.login()
    return RedirectResponse(url=oauth2_url, status_code=302)

@app.get('/atm/user/callback')
async def login(code: str, response: Response):
    tokens = discord_auth.get_tokens(code)
    if "access_token" in tokens.keys():
        user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
        tokens = {**tokens, **user_data}
        conn = newconn()
        cur = conn.cursor()
        stoken = str(uuid4())
        cur.execute(f"DELETE FROM user WHERE discordid = {user_data['id']}")
        cur.execute(f"INSERT INTO user VALUES ('{user_data['id']}', '{b64e(user_data['username'])}', '{b64e(user_data['email'])}', '{b64e(json.dumps(tokens))}')")
        cur.execute(f"INSERT INTO session VALUES ('{stoken}', '{user_data['id']}', '{int(time.time())}')")
        conn.commit()
        user_data["token"] = stoken
        return RedirectResponse(url=f"https://{dhdomain}/auth?token="+stoken, status_code=302)
    response.status_code = 401
    return {"error": True, "descriptor": tokens["error_description"].replace('\\"', "'")}

@app.post('/atm/user/revoke')
async def user(response: Response, authorization: Optional[str] = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    conn.commit()
    return {"error": False, "response": {"response_message": "Token revoked"}}