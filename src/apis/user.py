# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, requests, math, bcrypt

from app import app, config
from db import newconn
from functions import *
import multilang as ml

# User Info Section
@app.get(f'/{config.abbr}/user')
async def getUser(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /user', 60, 120)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    roles = []
    udiscordid = -1
    if userid == -1 and discordid == -1 and steamid == -1 and truckersmpid == -1:
        au = auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        else:
            discordid = au["discordid"]
            roles = au["roles"]
            udiscordid = discordid
            selfq = True
    else:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            if config.privacy:
                response.status_code = 401
                return au
        else:
            udiscordid = au["discordid"]
            roles = au["roles"]
    
    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True

    qu = ""
    if userid != -1:
        qu = f"userid = {userid}"
    elif discordid != -1:
        qu = f"discordid = {discordid}"
    elif steamid != -1:
        qu = f"steamid = {steamid}"
    elif truckersmpid != -1:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}

    cur.execute(f"SELECT userid, discordid FROM user WHERE {qu}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    userid = t[0][0]
    discordid = t[0][1]
    
    cur.execute(f"SELECT discordid, name, avatar, roles, join_timestamp, truckersmpid, steamid, bio, email, mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [str(i) for i in roles]

    mfa_secret = t[0][9]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True

    if userid != -1:
        activityUpdate(udiscordid, f"Viewing {t[0][1]}'s Profile (User ID: {userid})")
    else:
        activityUpdate(udiscordid, f"Viewing {t[0][1]}'s Profile")

    activity_last_seen = 0
    activity_name = "Offline"
    cur.execute(f"SELECT activity, timestamp FROM user_activity WHERE discordid = {t[0][0]}")
    ac = cur.fetchall()
    if len(ac) != 0:
        activity_name = ac[0][0]
        activity_last_seen = ac[0][1]
        if int(time.time()) - activity_last_seen >= 300:
            activity_name = "Offline"
        elif int(time.time()) - activity_last_seen >= 120:
            activity_name = "Online"

    if isAdmin or isHR or udiscordid == t[0][0]:
        return {"error": False, "response": {"user": {"name": t[0][1], "userid": str(userid), \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "activity": {"name": activity_name, "last_seen": str(activity_last_seen)}, \
                "email": t[0][8], "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
             "roles": roles, "bio": b64d(t[0][7]), "mfa": mfa_enabled, "join_timestamp": str(t[0][4])}}}
    else:
        return {"error": False, "response": {"user": {"name": t[0][1], "userid": str(userid), \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "activity": {"name": activity_name, "last_seen": str(activity_last_seen)}, \
                "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
                "roles": roles, "bio": b64d(t[0][7]), "join_timestamp": str(t[0][4])}}}

@app.get(f"/{config.abbr}/user/notification/list")
async def getUserNotificationList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, content: Optional[str] = '', status: Optional[int] = -1, \
        order_by: Optional[str] = "notificationid", order: Optional[str] = "desc"):
    rl = ratelimit(request.client.host, 'GET /user/notification/list', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    content = convert_quotation(content).lower()
    
    if not order_by in ["content", "notificationid"]:
        order_by = "notificationid"
        order = "desc"

    if not order in ["asc", "desc"]:
        if order_by == "notificationid":
            order = "desc"
        elif order_by == "content":
            order = "asc"
    order = order.upper()

    limit = ""
    if status == 0:
        limit += f"AND status = 0"
    elif status == 1:
        limit += f"AND status = 1"

    cur.execute(f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE discordid = {discordid} {limit} AND LOWER(content) LIKE '%{content}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"notificationid": str(tt[0]), "content": tt[1], "timestamp": str(tt[2]), "read": TF[tt[3]]})
    cur.execute(f"SELECT COUNT(*) FROM user_notification WHERE discordid = {discordid} {limit} AND LOWER(content) LIKE '%{content}%'")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.put(f"/{config.abbr}/user/notification/status")
async def putUserNotificationStatus(request: Request, response: Response, authorization: str = Header(None), \
        notificationids: Optional[str] = ""):
    rl = ratelimit(request.client.host, 'GET /user/notification/status', 60, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}
        
    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        read = 0
        if form["read"] == "true":
            read = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    if notificationids == "all":
        cur.execute(f"UPDATE user_notification SET status = {read} WHERE discordid = {discordid}")
        conn.commit()
        return {"error": False}

    notificationids = notificationids.split(",")
    
    for notificationid in notificationids:
        try:
            notificationid = int(notificationid)
            cur.execute(f"UPDATE user_notification SET status = {read} WHERE notificationid = {notificationid} AND discordid = {discordid}")
        except:
            pass
    conn.commit()
    
    return {"error": False}

@app.get(f"/{config.abbr}/user/list")
async def getUserList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, name: Optional[str] = '', \
        order_by: Optional[str] = "discord_id", order: Optional[str] = "asc"):
    rl = ratelimit(request.client.host, 'GET /user/list', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "get_pending_user_list"])
    if au["error"]:
        response.status_code = 401
        return au
    activityUpdate(au["discordid"], f"Viewing Pending Users")
    
    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
    
    name = convert_quotation(name).lower()
    
    if not order_by in ["name", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
        order = "asc"
    cvt = {"name": "user.name", "discord_id": "user.discordid", "join_timestamp": "user.join_timestamp"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    cur.execute(f"SELECT user.userid, user.name, user.discordid, user.join_timestamp, user.avatar, banned.reason FROM user LEFT JOIN banned ON banned.discordid = user.discordid WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{name}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        banreason = ""
        banned = False
        if tt[5] != None:
            banned = True
            banreason = tt[5]
        ret.append({"name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[4], "ban": {"is_banned": TF[banned], "reason": banreason}, "join_timestamp": tt[3]})
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid < 0 AND LOWER(name) LIKE '%{name}%'")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

# Self-Operation Section
@app.patch(f'/{config.abbr}/user/bio')
async def patchUserBio(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/bio', 60, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        bio = str(form["bio"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
        
    if len(bio) > 1000:
        response.status_code = 413
        return {"error": True, "descriptor": "Maximum length of 'bio' is 1,000 characters."}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False}

@app.patch(f'/{config.abbr}/user/password')
async def patchPassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/password', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp")}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp")}

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    form = await request.form()
    try:
        password = str(form["password"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    if not "@" in email: # make sure it's not empty
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "invalid_email")}
        
    cur.execute(f"SELECT userid FROM user WHERE email = '{email}'")
    t = cur.fetchall()
    if len(t) > 1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "too_many_user_with_same_email")}
        
    if len(password) >= 8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": True, "descriptor": ml.tr(request, "weak_password")}
    else:
        return {"error": True, "descriptor": ml.tr(request, "weak_password")}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    cur.execute(f"INSERT INTO user_password VALUES ({discordid}, '{email}', '{b64e(pwdhash)}')")
    conn.commit()

    return {"error": False}
    
@app.delete(f'/{config.abbr}/user/password')
async def deletePassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/password', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp")}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp")}

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}
    
    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    conn.commit()

    return {"error": False}
    
@app.patch(f"/{config.abbr}/user/steam")
async def patchSteam(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/steam', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        openid = str(form["callback"]).replace("openid.mode=id_res", "openid.mode=check_authentication")
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    r = requests.get("https://steamcommunity.com/openid/login?" + openid)
    if r.status_code != 200:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "steam_api_error")}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_steam_auth")}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    cur.execute(f"SELECT * FROM user WHERE discordid != '{discordid}' AND steamid = {steamid}")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "steam_bound_to_other_account")}

    cur.execute(f"SELECT roles, steamid, userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    while "" in roles:
        roles.remove("")
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid != 0 and userid >= 0:
        cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%Updated Steam ID%' AND userid = {userid} AND timestamp >= {int(time.time() - 86400 * 7)}")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 429
            return {"error": True, "descriptor": ml.tr(request, "steam_updated_within_7d")}

        for role in roles:
            if role == "100":
                requests.delete(f"https://api.navio.app/v1/drivers/{orgsteamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
                requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
                await AuditLog(userid, f"Updated Steam ID to `{steamid}`")

    cur.execute(f"UPDATE user SET steamid = {steamid} WHERE discordid = '{discordid}'")
    conn.commit()

    r = requests.get(f"https://api.truckersmp.com/v2/player/{steamid}")
    if r.status_code == 200:
        d = json.loads(r.text)
        if not d["error"]:
            truckersmpid = d["response"]["id"]
            cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
            conn.commit()
            return {"error": False}

    # in case user changed steam
    cur.execute(f"UPDATE user SET truckersmpid = 0 WHERE discordid = '{discordid}'")
    conn.commit()
    
    return {"error": False}

@app.patch(f"/{config.abbr}/user/truckersmp")
async def patchTruckersMP(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/truckersmp', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        truckersmpid = form["truckersmpid"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    try:
        truckersmpid = int(truckersmpid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id")}

    r = requests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid))
    if r.status_code != 200:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_api_error")}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id")}

    cur.execute(f"SELECT steamid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "steam_not_bound_before_truckersmp")}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    truckersmp_name = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_steam_mismatch", var = {"truckersmp_name": truckersmp_name, "truckersmpid": str(truckersmpid)})}

    cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
    conn.commit()
    return {"error": False}

# Manage User Section
@app.put(f'/{config.abbr}/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PUT /user/ban', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
        expire = int(form["expire"])
        reason = convert_quotation(form["reason"])
        if len(reason) > 256:
            response.status_code = 413
            return {"error": True, "descriptor": "Maximum length of 'reason' is 256 characters."}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    if expire == -1:
        expire = 9999999999999999
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid")}

    cur.execute(f"SELECT userid, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    username = "Unknown User"
    if len(t) > 0:
        userid = t[0][0]
        username = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "dismiss_before_ban")}

    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO banned VALUES ({discordid}, {expire}, '{reason}')")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()
        duration = "forever"
        if expire != 9999999999999999:
            duration = f'until `{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))}` UTC'
        await AuditLog(adminid, f"Banned `{username}` (Discord ID: `{discordid}`) {duration}.")
        return {"error": False}
    else:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_already_banned")}

@app.delete(f'/{config.abbr}/user/ban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/ban', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_not_banned")}
    else:
        cur.execute(f"DELETE FROM banned WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(adminid, f"Unbanned `{username}` (Discord ID: `{discordid}`)")
        return {"error": False}

# Higher Management Section
@app.patch(f"/{config.abbr}/user/discord")
async def patchUserDiscord(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/discord', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm", "update_user_discord"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        old_discord_id = int(form["old_discord_id"])
        new_discord_id = int(form["new_discord_id"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
        
    if old_discord_id == new_discord_id:
        return {"error": False}

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {old_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "user_must_register_first")}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) > 0 and t[0][0] != -1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_must_not_be_member")}

    cur.execute(f"DELETE FROM user WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM session WHERE discordid = {old_discord_id}")
    cur.execute(f"DELETE FROM session WHERE discordid = {new_discord_id}")
    cur.execute(f"UPDATE user SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    conn.commit()

    await AuditLog(adminid, f"Updated Discord ID from `{old_discord_id}` to `{new_discord_id}`")

    return {"error": False}
    
@app.delete(f"/{config.abbr}/user/connections")
async def deleteUserConnection(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/connections', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm", "delete_account_connections"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "dismiss_before_unbind")}
    
    cur.execute(f"UPDATE user SET steamid = -1, truckersmpid = -1 WHERE discordid = {discordid}")
    conn.commit()

    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(adminid, f"Deleted connections of `{username}` (Discord ID: `{discordid}`)")

    return {"error": False}
    
@app.delete(f"/{config.abbr}/user")
async def deleteUser(request: Request, response: Response, authorization: str = Header(None), discordid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'DELETE /user', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    auth_discordid = au["discordid"]
    if discordid == auth_discordid:
        discordid = -1

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data")}

    if discordid != -1:
        au = auth(authorization, request, required_permission = ["admin", "hrm", "delete_user"])
        if au["error"]:
            response.status_code = 401
            return au
        adminid = au["userid"]

        conn = newconn()
        cur = conn.cursor()
        
        cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
        userid = t[0][0]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "dismiss_before_delete")}
        
        username = getUserInfo(discordid = discordid)["name"]
        cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()

        await AuditLog(adminid, f"Deleted account: `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}
    
    else:
        discordid = auth_discordid
        
        conn = newconn()
        cur = conn.cursor()
        
        cur.execute(f"SELECT userid, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        userid = t[0][0]
        name = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "leave_company_before_delete")}
        
        username = getUserInfo(discordid = discordid)["name"]
        cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()

        await AuditLog(-999, f"Deleted account: `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}