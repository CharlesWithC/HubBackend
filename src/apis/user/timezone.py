# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC


from fastapi import Header, Request, Response

import multilang as ml
from functions import *
import pytz


async def get_timezone(request: Request, response: Response, authorization: str = Header(None)):
    """Returns the timezone of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/timezone', 60, 120)
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

    return {"timezone": await GetUserTimezone(request, uid)}

async def patch_timezone(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the timezone of the authorized user, returns 204

    JSON: `{"timezone": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/timezone', 60, 10)
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
        timezone = data["timezone"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if timezone not in pytz.all_timezones:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_timezone", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'timezone'")
    await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'timezone', '{convertQuotation(timezone)}')")
    await app.db.commit(dhrid)

    app.redis.set(f"utz:{uid}", timezone)
    app.redis.expire(f"utz:{uid}", 60)

    return Response(status_code=204)
