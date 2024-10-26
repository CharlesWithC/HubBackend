# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC


from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_privacy(request: Request, response: Response, authorization: str = Header(None)):
    """Returns the privacy settings of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /user/privacy', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    return (await GetUserPrivacy(request, uid))

async def patch_privacy(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the privacy settings of the authorized user, returns 204

    JSON: `{"role_history": bool, "ban_history": bool, "email": bool, "account_connections": bool, "activity": bool, "public_profile": bool}`"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/privacy', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    privacy = (await GetUserPrivacy(request, uid))
    try:
        role_history = int(bool(data["role_history"])) if "role_history" in data.keys() else int(privacy["role_history"])
        ban_history = int(bool(data["ban_history"])) if "ban_history" in data.keys() else int(privacy["ban_history"])
        email = int(bool(data["email"])) if "email" in data.keys() else int(privacy["email"])
        account_connections = int(bool(data["account_connections"])) if "account_connections" in data.keys() else int(privacy["account_connections"])
        activity = int(bool(data["activity"])) if "activity" in data.keys() else int(privacy["activity"])
        public_profile = int(bool(data["public_profile"])) if "public_profile" in data.keys() else int(privacy["public_profile"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["privacy"])}

    await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'privacy'")
    await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'privacy', '{role_history},{ban_history},{email},{account_connections},{activity},{public_profile}')")
    await app.db.commit(dhrid)

    app.redis.set(f"uprivacy:{uid}", f"{role_history},{ban_history},{email},{account_connections},{activity},{public_profile}")
    app.redis.expire(f"uprivacy:{uid}", 60)

    return Response(status_code=204)
