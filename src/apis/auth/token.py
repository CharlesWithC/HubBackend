# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
import uuid
from hashlib import sha256
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_token(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /token', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    token_type = authorization.split(" ")[0].lower()

    return {"token_type": token_type}

async def patch_token(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]

    await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4())
    await app.db.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await app.db.commit(dhrid)

    return {"token": stoken}

async def delete_token(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /token', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    stoken = authorization.split(" ")[1]

    await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /token/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order_by not in ['ip', 'timestamp', 'country_code', 'user_agent', 'last_used_timestamp']:
        order_by = "last_used_timestamp"
        order = "desc"
    if order_by == "country_code":
        order_by = "country"
    order = order.lower()
    if order not in ['asc', 'desc']:
        order = "asc"

    ret = []
    await app.db.execute(dhrid, f"SELECT token, ip, timestamp, country, user_agent, last_used_timestamp FROM session \
        WHERE uid = {uid} ORDER BY {order_by} {order}, last_used_timestamp DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        tk = tt[0]
        tk = sha256(tk.encode()).hexdigest()
        ret.append({"hash": tk, "ip": tt[1], "country": getFullCountry(tt[3]), "user_agent": tt[4], "create_timestamp": tt[2], "last_used_timestamp": tt[5]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM session WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def delete_hash(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /token/hash', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    data = await request.json()
    try:
        hsh = data["hash"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    ok = False
    await app.db.execute(dhrid, f"SELECT token FROM session WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{tt[0]}' AND uid = {uid}")
            await app.db.commit(dhrid)
            break

    if ok:
        return Response(status_code=204)
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "invalid_hash", force_lang = au["language"])}

async def delete_all(request: Request, response: Response, authorization: str = Header(None), \
        last_used_before: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /token/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if last_used_before is None:
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
    else:
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid} AND last_used_timestamp <= {last_used_before}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def get_application_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "last_used_timestamp", order: Optional[str] = "desc"):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /token/application/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order_by not in ['timestamp', 'last_used_timestamp']:
        order_by = "last_used_timestamp"
        order = "desc"
    order = order.lower()
    if order not in ['asc', 'desc']:
        order = "asc"

    ret = []
    await app.db.execute(dhrid, f"SELECT app_name, token, timestamp, last_used_timestamp FROM application_token \
        WHERE uid = {uid} ORDER BY {order_by} {order}, last_used_timestamp DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        tk = sha256(tt[1].encode()).hexdigest()
        ret.append({"app_name": tt[0], "hash": tk, "create_timestamp": tt[2], "last_used_timestamp": tt[3]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM application_token WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def post_application(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    data = await request.json()

    await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}

    try:
        app_name = convertQuotation(data["app_name"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if len(app_name) >= 128:
        response.status_code = 400
        return {"error": ml.tr(request, "content_too_long", var = {"item": "app_name", "limit": "128"}, force_lang = au["language"])}

    stoken = str(uuid.uuid4())
    await app.db.execute(dhrid, f"INSERT INTO application_token VALUES ('{app_name}', '{stoken}', {uid}, {int(time.time())}, 0)")
    await app.db.commit(dhrid)

    return {"token": stoken}

async def delete_application(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /token/application', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        hsh = data["hash"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    ok = False
    await app.db.execute(dhrid, f"SELECT token FROM application_token WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        thsh = sha256(tt[0].encode()).hexdigest()
        if thsh == hsh:
            ok = True
            await app.db.execute(dhrid, f"DELETE FROM application_token WHERE token = '{tt[0]}' AND uid = {uid}")
            await app.db.commit(dhrid)
            break

    if ok:
        return Response(status_code=204)
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "invalid_hash", force_lang = au["language"])}

async def delete_application_all(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /token/application/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)
