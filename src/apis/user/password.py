# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import bcrypt
from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def patch_password(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the password of the authorized user, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/password', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    email = convertQuotation(t[0][0])

    data = await request.json()
    try:
        password = str(data["password"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if email is None or "@" not in email: # make sure it's valid
        response.status_code = 403
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Email"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid FROM user WHERE email = '{email}'")
    t = await app.db.fetchall(dhrid)
    if len(t) > 1:
        response.status_code = 409
        return {"error": ml.tr(request, "email_not_unique", force_lang = au["language"])}

    if len(password) >= 8:
        if bool(re.match('((?=.*\\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})', password)) is not True and \
            (bool(re.match('((\\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})', password)) is True):
            response.status_code = 400
            return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}
    else:
        response.status_code = 400
        return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await app.db.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await app.db.execute(dhrid, f"INSERT INTO user_password VALUES ({uid}, '{convertQuotation(email)}', '{b64e(pwdhash)}')")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_password_disable(request: Request, response: Response, authorization: str = Header(None)):
    """Disables password login for the authorized user, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /user/password/disable', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT email, steamid, discordid, mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    (email, steamid, discordid, mfa_secret) = (t[0][0], t[0][1], t[0][2], t[0][3])
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}

    if abs(nint(steamid)) <= 1 and abs(nint(discordid)) <= 1:
        response.status_code = 403
        return {"error": ml.tr(request, "connect_more_to_disable_password", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await app.db.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await app.db.commit(dhrid)

    return Response(status_code=204)
