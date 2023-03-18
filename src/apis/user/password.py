# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import bcrypt
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *


@app.patch(f'/{config.abbr}/user/password')
async def patch_user_password(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the password of the authorized user, returns 204
    
    [DEPRECATED] This function will be moved or removed when the user system no longer relies on Discord."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/password', 60, 10)
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

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    email = t[0][0]

    data = await request.json()
    try:
        password = str(data["password"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if email == "" or "@" not in email: # make sure it's not empty
        response.status_code = 403
        return {"error": ml.tr(request, "invalid_email", force_lang = au["language"])}
        
    await aiosql.execute(dhrid, f"SELECT userid FROM user WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 1:
        response.status_code = 409
        return {"error": ml.tr(request, "too_many_user_with_same_email", force_lang = au["language"])}
        
    if len(password) >= 8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}
    else:
        return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await aiosql.execute(dhrid, f"INSERT INTO user_password VALUES ({uid}, '{email}', '{b64e(pwdhash)}')")
    await aiosql.commit(dhrid)

    return Response(status_code=204)
    
@app.post(f'/{config.abbr}/user/password/disable')
async def post_user_password_disable(request: Request, response: Response, authorization: str = Header(None)):
    """Disables password login for the authorized user, returns 204
    
    [DEPRECATED] This function will be moved or removed when the user system no longer relies on Discord."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /user/password/disable', 60, 10)
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

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    email = t[0][0]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await aiosql.commit(dhrid)

    return Response(status_code=204)