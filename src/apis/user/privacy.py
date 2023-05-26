# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC


from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_privacy(request: Request, response: Response, authorization: str = Header(None)):
    """Returns the privacy settings of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/privacy', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    return (await GetUserPrivacy(request, uid, nocache = True))

async def patch_privacy(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the privacy settings of the authorized user, returns 204

    JSON: `{"role_history": bool, "ban_history": bool}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/privacy', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        role_history = int(bool(data["role_history"]))
        ban_history = int(bool(data["ban_history"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["privacy"])}

    await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'privacy'")
    await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'privacy', '{role_history},{ban_history}')")
    await app.db.commit(dhrid)

    return Response(status_code=204)
