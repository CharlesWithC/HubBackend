# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
import uuid
from hashlib import sha256
from typing import Optional

import bcrypt
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *


@app.post(f"/auth/ticket")
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

@app.get(f"/auth/ticket")
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
        return {"error": ml.tr(request, "invalid_authorization_token")}
    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE token = '{token}'")
    await aiosql.commit(dhrid)
    return (await GetUserInfo(dhrid, request, uid = t[0][0]))