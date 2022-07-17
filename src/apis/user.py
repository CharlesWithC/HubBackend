# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
from typing import Optional
import json, time, requests, math

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.post(f'/{config.vtcprefix}/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/ban', 60, 10)
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
    expire = int(form["expire"])
    if expire == -1:
        expire = 9999999999999999
    reason = form["reason"].replace("'","''")
    try:
        discordid = int(discordid)
    except:
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid")}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    username = "Unknown User"
    if len(t) > 0:
        userid = t[0][0]
        if userid != -1:
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
        return {"error": False, "response": {"discordid": str(discordid)}}
    else:
        return {"error": True, "descriptor": ml.tr(request, "user_already_banned")}

@app.post(f'/{config.vtcprefix}/user/unban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/unban', 60, 10)
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
        
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid")}
    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "user_not_banned")}
    else:
        cur.execute(f"DELETE FROM banned WHERE discordid = {discordid}")
        conn.commit()
        await AuditLog(adminid, f"Unbanned user with Discord ID `{discordid}`")
        return {"error": False, "response": {"discordid": str(discordid)}}

@app.get(f"/{config.vtcprefix}/users")
async def getUsers(page:int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /users', 60, 60)
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
    
    cur.execute(f"SELECT userid, name, discordid FROM user WHERE userid < 0 ORDER BY discordid ASC")
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
        ret.append({"name": tt[1], "discordid": f"{tt[2]}", "banned": banned, "banreason": banreason})
    ret = ret[(page-1)*10:page*10]
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid < 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get(f'/{config.vtcprefix}/user')
async def getUser(request: Request, response: Response, authorization: str = Header(None), qdiscordid: Optional[int] = 0):
    rl = ratelimit(request.client.host, 'GET /user', 30, 10)
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

    cur.execute(f"SELECT userid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    ok = False
    isDS = False
    for i in roles:
        if int(i) in config.perms.admin or int(i) in config.perms.hr or int(i) in config.perms.hrm:
            ok = True
        if int(i) in config.perms.division:
            isDS = True

    if qdiscordid == 0:
        qdiscordid = discordid
    
    if discordid != qdiscordid:
        if not ok and not isDS:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        cur.execute(f"SELECT userid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {qdiscordid}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    else:
        ok = True
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    email = t[0][8]
    if au["application_token"] or not ok and isDS:
        edomain = email[email.rfind("@"):]
        l = email.rfind("@")
        email = "*" * l + edomain
    return {"error": False, "response": {"userid": t[0][0], "name": t[0][1], "email": email, "discordid": f"{discordid}", "avatar": t[0][2], "bio": b64e(t[0][7]), "roles": roles, "join": t[0][4], "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}"}}

@app.post(f'/{config.vtcprefix}/user/bio')
async def updateUserBio(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /user/bio', 60, 10)
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
        return {"error": True, "descriptor": ml.tr(request, "bio_too_long")}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False, "response": {"bio": bio}}
    
@app.patch(f"/{config.vtcprefix}/user/discord")
async def adminUpdateDiscord(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/discord', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    old_discord_id = int(form["old_discord_id"])
    new_discord_id = int(form["new_discord_id"])

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {old_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "user_must_register_first")}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) > 0 and t[0][0] != -1:
        return {"error": True, "descriptor": ml.tr(request, "user_must_not_be_member")}

    cur.execute(f"DELETE FROM user WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM session WHERE discordid = {old_discord_id}")
    cur.execute(f"DELETE FROM session WHERE discordid = {new_discord_id}")
    cur.execute(f"UPDATE user SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    conn.commit()

    await AuditLog(adminid, f"Updated user Discord ID from `{old_discord_id}` to `{new_discord_id}`")

    return {"error": False, "response": {"discordid": str(new_discord_id)}}
    
@app.patch(f"/{config.vtcprefix}/user/unbind")
async def adminUnbindConnections(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /user/unbind', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    discordid = int(form["discordid"])

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    userid = t[0][0]
    if userid != -1:
        return {"error": True, "descriptor": ml.tr(request, "dismiss_before_unbind")}
    
    cur.execute(f"UPDATE user SET steamid = -1, truckersmpid = -1 WHERE discordid = {discordid}")
    conn.commit()

    await AuditLog(adminid, f"Unbound connections for user with Discord ID `{discordid}`")

    return {"error": False}
    
@app.delete(f"/{config.vtcprefix}/user/delete")
async def adminDeleteUser(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/delete', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    discordid = int(form["discordid"])

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    userid = t[0][0]
    if userid != -1:
        return {"error": True, "descriptor": ml.tr(request, "dismiss_before_delete")}
    
    cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
    conn.commit()

    await AuditLog(adminid, f"Deleted user with Discord ID `{discordid}`")

    return {"error": False}