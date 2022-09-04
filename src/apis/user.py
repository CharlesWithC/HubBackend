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
@app.get(f'/{config.vtc_abbr}/user')
async def getUser(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /user', 180, 60)
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
    
    cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]

    email = ""
    if isAdmin or isHR or udiscordid == t[0][0]:
        email = t[0][8]

    return {"error": False, "response": {"userid": str(userid), "name": t[0][1], \
        "email": email, "avatar": t[0][2], "join": str(t[0][4]), "roles": roles, \
        "discordid": f"{t[0][0]}", "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", "bio": b64d(t[0][7])}}

@app.get(f"/{config.vtc_abbr}/user/list")
async def getUserList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, order_by: Optional[str] = "discord_id", order: Optional[str] = "asc", page_size: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /user/list', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
    
    if not order_by in ["name", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
    cvt = {"name": "name", "discord_id": "discordid", "join_timestamp": "joints"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    cur.execute(f"SELECT userid, name, discordid, joints FROM user WHERE userid < 0 ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT reason FROM banned WHERE discordid = {tt[2]}")
        p = cur.fetchall()
        banned = False
        banreason = ""
        if len(p) > 0:
            banned = True
            banreason = p[0][0]
        ret.append({"name": tt[1], "discordid": f"{tt[2]}", "is_banned": TF[banned], "ban_reason": banreason, "join_timestamp": tt[3]})
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid < 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

# Self-Operation Section
@app.patch(f'/{config.vtc_abbr}/user/bio')
async def patchUserBio(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/bio', 180, 10)
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
    bio = form["bio"]
    if len(bio) > 500:
        response.status_code = 413
        return {"error": True, "descriptor": ml.tr(request, "bio_too_long")}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False}

@app.patch(f'/{config.vtc_abbr}/user/password')
async def patchPassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/password', 180, 5)
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
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_required")}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    form = await request.form()
    password = form["password"]

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
    
@app.delete(f'/{config.vtc_abbr}/user/password')
async def deletePassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/password', 180, 5)
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
    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_required")}
    
    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    conn.commit()

    return {"error": False}
    
@app.patch(f"/{config.vtc_abbr}/user/steam")
async def patchSteam(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/steam', 180, 3)
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
    openid = form["openid"].replace("openid.mode=id_res", "openid.mode=check_authentication")
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
        cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%Steam ID updated from%' AND userid = {userid} AND timestamp >= {int(time.time() - 86400 * 7)}")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 429
            return {"error": True, "descriptor": ml.tr(request, "steam_updated_within_7d")}

        for role in roles:
            if role == "100":
                requests.delete(f"https://api.navio.app/v1/drivers/{orgsteamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
                requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
                await AuditLog(userid, f"Steam ID updated from `{orgsteamid}` to `{steamid}`")

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

@app.patch(f"/{config.vtc_abbr}/user/truckersmp")
async def patchTruckersMP(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/truckersmp', 180, 3)
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
    truckersmpid = form["truckersmpid"]
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
    tmpname = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_steam_mismatch", var = {"tmpname": tmpname, "truckersmpid": str(truckersmpid)})}

    cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
    conn.commit()
    return {"error": False}

# Manage User Section
@app.post(f'/{config.vtc_abbr}/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/ban', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm"])
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
    except:
        response.status_code = 400
        return {"error": True}
    if expire == -1:
        expire = 9999999999999999
    reason = form["reason"].replace("'","''")
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid")}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    username = "Unknown User"
    if len(t) > 0:
        userid = t[0][0]
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
            duration = f'until {time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))} UTC'
        await AuditLog(adminid, f"Banned **{username}** (Discord ID `{discordid}`) for `{reason}` **{duration}**.")
        return {"error": False}
    else:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_already_banned")}

@app.post(f'/{config.vtc_abbr}/user/unban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/unban', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    discordid = int(form["discordid"])
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid")}
    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_not_banned")}
    else:
        cur.execute(f"DELETE FROM banned WHERE discordid = {discordid}")
        conn.commit()
        await AuditLog(adminid, f"Unbanned user with Discord ID `{discordid}`")
        return {"error": False}

# Higher Management Section
@app.patch(f"/{config.vtc_abbr}/user/discord")
async def patchUserDiscord(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/discord', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_required")}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        old_discord_id = int(form["old_discord_id"])
        new_discord_id = int(form["new_discord_id"])
    except:
        response.status_code = 400
        return {"error": True}

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

    await AuditLog(adminid, f"Updated user Discord ID from `{old_discord_id}` to `{new_discord_id}`")

    return {"error": False}
    
@app.delete(f"/{config.vtc_abbr}/user/connections")
async def deleteUserConnection(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/connections', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_required")}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True}

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

    await AuditLog(adminid, f"Unbound connections for user with Discord ID `{discordid}`")

    return {"error": False}
    
@app.delete(f"/{config.vtc_abbr}/user")
async def deleteUser(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "login_with_discord_required")}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "dismiss_before_delete")}
    
    cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
    conn.commit()

    await AuditLog(adminid, f"Deleted user with Discord ID `{discordid}`")

    return {"error": False}