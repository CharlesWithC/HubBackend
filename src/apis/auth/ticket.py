# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
import uuid
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_ticket(request: Request, response: Response, token: Optional[str] = None):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /auth/ticket', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    if token is None:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_authorization_token")}

    token = convertQuotation(token)

    await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await app.db.execute(dhrid, f"SELECT uid FROM auth_ticket WHERE token = '{token}'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_authorization_token")}
    await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE token = '{token}'")
    await app.db.commit(dhrid)
    return (await GetUserInfo(request, uid = t[0][0]))

async def post_ticket(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /auth/ticket', 180, 20)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = str(uuid.uuid4())
    while stoken[0] == "f":
        stoken = str(uuid.uuid4())
    await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await app.db.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+180})")
    await app.db.commit(dhrid)

    return {"token": stoken}
