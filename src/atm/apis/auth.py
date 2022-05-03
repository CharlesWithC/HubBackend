# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from uuid import uuid4
import json

from app import app, config
from db import newconn
from functions import *

client_id = config.discord_client_id
client_secret = config.discord_client_secret
oauth2_url = config.discord_oauth2_url
callback_url = config.discord_callback_url

discord_auth = DiscordAuth(client_id, client_secret, callback_url)

@app.get('/atm/user/login', response_class=RedirectResponse)
async def home():
    # login_url = discord_auth.login()
    return oauth2_url

@app.get('/atm/user/callback    ')
async def login(code: str, response: Response):
    tokens = discord_auth.get_tokens(code)
    if "access_token" in tokens.keys():
        user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
        tokens = {**tokens, **user_data}
        conn = newconn()
        cur = conn.cursor()
        stoken = str(uuid4())
        cur.execute(f"INSERT INTO session (token, discordid, discordname, email, data) VALUES \
            ('{stoken}', '{user_data['id']}', '{b64e(user_data['username'])}', '{b64e(user_data['email'])}', '{b64e(json.dumps(tokens))}')")
        conn.commit()
        user_data["token"] = stoken
        return {"error": False, "response": {"token": stoken}}
    response.status_code = 401
    return {"error": True, "descriptor": tokens["error_description"].replace('\\"', "'")}

@app.post('/atm/user')
async def user(request: Request, response: Response):
    form = await request.form()
    stoken = form["token"]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT data FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    data = json.loads(b64d(t[0][0]))
    access_token = data["access_token"]
    user_data = discord_auth.get_user_data_from_token(access_token)
    if "message" in user_data.keys():
        response.status_code = 401
        return {"error": True, "descriptor": user_data["message"]}
    return {"error": False, "response": user_data}

@app.post('/atm/user/revoke')
async def revoke(request: Request, response: Response):
    form = await request.form()
    stoken = form["token"]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
    conn.commit()
    return {"error": False, "response": {"response_message": "Token revoked"}}