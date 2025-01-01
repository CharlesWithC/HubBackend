# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC


from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_language(request: Request, response: Response, authorization: str = Header(None)):
    """Returns the language of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /user/language', 60, 60)
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

    return {"language": await GetUserLanguage(request, uid)}

async def patch_language(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the language of the authorized user, returns 204

    JSON: `{"language": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/language', 60, 60)
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
    try:
        language = data["language"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if language not in ml.LANGUAGES:
        response.status_code = 400
        return {"error": ml.tr(request, "language_not_supported", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'language'")
    await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'language', '{convertQuotation(language)}')")
    await app.db.commit(dhrid)

    app.redis.set(f"ulang:{uid}", language)
    app.redis.expire(f"ulang:{uid}", 60)

    return Response(status_code=204)
