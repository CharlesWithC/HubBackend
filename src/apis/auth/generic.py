# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
import uuid

import bcrypt
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *


@app.post(f'/{config.abbr}/auth/password')
async def post_auth_password(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/password', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        email = convertQuotation(data["email"])  
        password = str(data["password"]).encode('utf-8')
        hcaptcha_response = data["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    try:
        r = await arequests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response}, dhrid = dhrid)
        d = json.loads(r.text)
        if not d["success"]:
            response.status_code = 403
            return {"error": ml.tr(request, "invalid_captcha")}
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": "Service Unavailable"}
    
    await aiosql.execute(dhrid, f"SELECT uid, password FROM user_password WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_email_or_password")}
    uid = t[0][0]
    pwdhash = t[0][1]
    ok = bcrypt.checkpw(password, b64d(pwdhash).encode())
    if not ok:
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_email_or_password")}
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        stoken = str(uuid.uuid4())
        stoken = "f" + stoken[1:]
        await aiosql.execute(dhrid, f"INSERT INTO auth_ticket VALUES ('{stoken}', {uid}, {int(time.time())+600})") # 10min ticket
        await aiosql.commit(dhrid)
        return {"token": stoken, "mfa": True}

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        if expire != 253402272000:
            expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        else:
            expire = ml.tr(request, "forever")
        response.status_code = 403
        if reason != "":
            return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "duration": expire})}
        else:
            return {"error": ml.tr(request, "ban_with_expire", var = {"duration": expire})}
        
    stoken = str(uuid.uuid4())
    stoken = "e" + stoken[1:]
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, uid, ml.ctr("password_login", var = {"country": getRequestCountry(request)}))

    await notification(dhrid, "login", uid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), 
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), 
                         "description": "", 
                         "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"token": stoken, "mfa": False}

@app.post(f'/{config.abbr}/auth/register')
async def post_auth_register(request: Request, response: Response):
    if not "email" in config.register_methods:
        response.status_code = 404
        return {"error": "Not Found"}
        
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/register', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        email = convertQuotation(data["email"])  
        password = str(data["password"])
        hcaptcha_response = data["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    try:
        r = await arequests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response}, dhrid = dhrid)
        d = json.loads(r.text)
        if not d["success"]:
            response.status_code = 403
            return {"error": ml.tr(request, "invalid_captcha")}
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": "Service Unavailable"}

    if len(password) >= 8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": ml.tr(request, "weak_password")}
    else:
        return {"error": ml.tr(request, "weak_password")}

    await aiosql.execute(dhrid, f"SELECT uid FROM user WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Email"})}
    
    await aiosql.execute(dhrid, f"SELECT uid FROM email_confirmation WHERE operation = 'register/{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Email"})}
    
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        if expire != 253402272000:
            expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        else:
            expire = ml.tr(request, "forever")
        response.status_code = 403
        if reason != "":
            return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "duration": expire})}
        else:
            return {"error": ml.tr(request, "ban_with_expire", var = {"duration": expire})}

    if not emailConfigured():
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid")}
    
    rl = await ratelimit(dhrid, request, 'POST /auth/register', 60, 2)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()
    username = convertQuotation(email.split("@")[0])

    # register user
    await aiosql.execute(dhrid, f"INSERT INTO user(userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, join_timestamp, mfa_secret) VALUES (-1, '{username}', 'pending', '', '', '', NULL, NULL, NULL, {int(time.time())}, '')")
    await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    uid = (await aiosql.fetchone(dhrid))[0]
    await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',drivershub,login,dlog,member,application,challenge,division,economy,event,')")
    await aiosql.commit(dhrid)
    await AuditLog(dhrid, uid, ml.ctr("password_register", var = {"country": getRequestCountry(request)}))

    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await aiosql.execute(dhrid, f"INSERT INTO user_password VALUES ({uid}, '{email}', '{b64e(pwdhash)}')")

    secret = "rg" + gensecret(length = 30)
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'register/{email}', {int(time.time() + 86400)})")
    await aiosql.commit(dhrid)
    
    link = config.frontend_urls.email_confirm.replace("{secret}", secret)
    await aiosql.extend_conn(dhrid, 15)
    ok = (await sendEmail(username, email, "register", link))
    await aiosql.extend_conn(dhrid, 2)
    if not ok:
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE secret = '{secret}'")
        await aiosql.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid")}

    stoken = str(uuid.uuid4())
    stoken = "e" + stoken[1:]
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, uid, ml.ctr("password_login", var = {"country": getRequestCountry(request)}))
    await notification(dhrid, "login", uid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), 
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), 
                         "description": "", 
                         "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                                    {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"token": stoken, "mfa": False}

@app.post(f'/{config.abbr}/auth/reset')
async def post_auth_reset(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/reset', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        email = convertQuotation(data["email"])
        hcaptcha_response = data["h-captcha-response"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    try:
        r = await arequests.post("https://hcaptcha.com/siteverify", data = {"secret": config.hcaptcha_secret, "response": hcaptcha_response}, dhrid = dhrid)
        d = json.loads(r.text)
        if not d["success"]:
            response.status_code = 403
            return {"error": ml.tr(request, "invalid_captcha")}
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": "Service Unavailable"}

    if not emailConfigured():
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid")}

    rl = await ratelimit(dhrid, request, 'POST /auth/reset', 60, 2)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await aiosql.execute(dhrid, f"SELECT uid, name FROM user WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return Response(status_code=204)
    uid = t[0][0]
    username = t[0][1]
    
    secret = "rp" + gensecret(length = 30)
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'reset-password/{email}', {int(time.time() + 3600)})")
    await aiosql.commit(dhrid)
    
    link = config.frontend_urls.email_confirm.replace("{secret}", secret)
    await aiosql.extend_conn(dhrid, 15)
    ok = (await sendEmail(username, email, "reset_password", link))
    await aiosql.extend_conn(dhrid, 2)
    if not ok:
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE secret = '{secret}'")
        await aiosql.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid")}

    return Response(status_code=204)

@app.post(f"/{config.abbr}/auth/mfa")
async def post_auth_mfa(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/mfa', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    data = await request.json()
    try:
        token = data["token"]
        otp = data["otp"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json")}

    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT uid FROM auth_ticket WHERE token = '{token}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0 or not token.startswith("f"):
        response.status_code = 401
        return {"error": ml.tr(request, "invalid_authorization_token")}
    uid = t[0][0]
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}
    secret = t[0][0]
    if secret == "":
        response.status_code = 428
        return {"error": ml.tr(request, "mfa_not_enabled")}
        
    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_otp")}

    await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE token = '{token}'")
    await aiosql.execute(dhrid, f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    await aiosql.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    await aiosql.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        reason = t[0][0]
        expire = t[0][1]
        if expire != 253402272000:
            expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        else:
            expire = ml.tr(request, "forever")
        response.status_code = 403
        if reason != "":
            return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "duration": expire})}
        else:
            return {"error": ml.tr(request, "ban_with_expire", var = {"duration": expire})}

    stoken = str(uuid.uuid4())
    while stoken[0] == "e":
        stoken = str(uuid.uuid4()) # All MFA logins won't be counted as unsafe
    await aiosql.execute(dhrid, f"INSERT INTO session VALUES ('{stoken}', '{uid}', '{int(time.time())}', '{request.client.host}', '{getRequestCountry(request, abbr = True)}', '{getUserAgent(request)}', '{int(time.time())}')")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    language = await GetUserLanguage(dhrid, uid)
    await AuditLog(dhrid, uid, ml.ctr("mfa_login", var = {"country": getRequestCountry(request)}))
    await notification(dhrid, "login", uid, ml.tr(request, "new_login", var = {"country": getRequestCountry(request), "ip": request.client.host}, force_lang = language), 
        discord_embed = {"title": ml.tr(request, "new_login_title", force_lang = language), 
                        "description": "", 
                        "fields": [{"name": ml.tr(request, "country", force_lang = language), "value": getRequestCountry(request), "inline": True},
                                   {"name": ml.tr(request, "ip", force_lang = language), "value": request.client.host, "inline": True}]
        }
    )

    return {"token": stoken}

@app.post(f"/{config.abbr}/auth/email")
async def get_auth_email(request: Request, response: Response, secret: str, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /auth/email', 60, 120)
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

    secret = convertQuotation(secret)

    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await aiosql.execute(dhrid, f"SELECT operation FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "auth_secret_invalid_or_expired")}
    operation = t[0][0]
    email = convertQuotation("/".join(operation.split("/")[1:]))

    await aiosql.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
        await aiosql.commit(dhrid)
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Email"}, force_lang = au["language"])}
    
    if operation.startswith("update-email/") or operation.startswith("register/"):
        # on email register, the email in user table is "pending"
        await aiosql.execute(dhrid, f"UPDATE user SET email = '{email}' WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
    
    elif operation.startswith("reset-password/"):
        data = await request.json()
        try:
            password = str(data["password"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json")}
    
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
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")

    await aiosql.commit(dhrid)
    
    return Response(status_code=204)