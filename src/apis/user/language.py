# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os

from fastapi import Header, Request, Response

import multilang as ml
from app import app
from functions import *


async def get_language(request: Request, response: Response, authorization: str = Header(None)):
    """Returns the language of the authorized user"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user/language', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    return {"language": await GetUserLanguage(dhrid, uid)}

async def patch_language(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the language of the authorized user, returns 204
    
    JSON: `{"language": str}`"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/language', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        language = convertQuotation(data["language"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if not os.path.exists(app.config.language_dir + "/" + language + ".json"):
        response.status_code = 400
        return {"error": ml.tr(request, "language_not_supported", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'language'")
    await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'language', '{language}')")
    await app.db.commit(dhrid)

    return Response(status_code=204)