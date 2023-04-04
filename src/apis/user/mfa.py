# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def post_enable(request: Request, response: Response, authorization: str = Header(None)):
    """Enables MFA for the authorized user, returns 204
    
    JSON: `{"secret": str, "otp": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /user/mfa', 60, 10)
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

    await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    secret = t[0][0]
    if secret != "":
        response.status_code = 409
        return {"error": ml.tr(request, "mfa_already_enabled", force_lang = au["language"])}
    
    data = await request.json()
    try:
        secret = data["secret"]
        otp = data["otp"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if len(secret) != 16 or not secret.isalnum():
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_mfa_secret", force_lang = au["language"])}
    
    try:
        base64.b32decode(secret)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_mfa_secret", force_lang = au["language"])}

    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"UPDATE user SET mfa_secret = '{secret}' WHERE uid = {uid}")
    await app.db.commit(dhrid)
        
    username = (await GetUserInfo(request, uid = uid))["name"]

    return Response(status_code=204)

async def post_disable(request: Request, response: Response, authorization: str = Header(None), uid: Optional[str] = -1):
    """Disables MFA for a specific user, returns 204
    
    If `uid` in request param is not provided, then disables MFA for the authorized user."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /user/mfa/disable', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if uid == -1:
        # self-disable mfa
        au = await auth(authorization, request, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        uid = au["uid"]
        
        await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": ml.tr(request, "mfa_not_enabled", force_lang = au["language"])}
    
        data = await request.json()
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        
        if not valid_totp(otp, secret):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        
        await app.db.execute(dhrid, f"UPDATE user SET mfa_secret = '' WHERE uid = {uid}")
        await app.db.commit(dhrid)
        
        username = (await GetUserInfo(request, uid = uid))["name"]

        return Response(status_code=204)
    
    else:
        # admin / hrm disable user mfa
        au = await auth(authorization, request, required_permission = ["admin", "hrm", "disable_user_mfa"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au

        await app.db.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": ml.tr(request, "mfa_not_enabled")}
        
        await app.db.execute(dhrid, f"UPDATE user SET mfa_secret = '' WHERE uid = {uid}")
        await app.db.commit(dhrid)
        
        username = (await GetUserInfo(request, uid = uid))["name"]
        await AuditLog(request, au["uid"], ml.ctr(request, "disabled_mfa", var = {"username": username, "uid": uid}))

        return Response(status_code=204)
        