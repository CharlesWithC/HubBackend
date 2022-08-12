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
    discordid = int(form["discordid"])
    expire = int(form["expire"])
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
        return {"error": False, "response": {"discordid": str(discordid)}}
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
        return {"error": False, "response": {"discordid": str(discordid)}}

@app.get(f"/{config.vtc_abbr}/users")
async def getUsers(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, order_by: Optional[str] = "discord_id", order: Optional[str] = "asc", pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /users', 180, 90)
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

    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 250:
        pagelimit = 250
    
    if not order_by in ["name", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
    cvt = {"name": "name", "discord_id": "discordid", "join_timestamp": "joints"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    cur.execute(f"SELECT userid, name, discordid, joints FROM user WHERE userid < 0 ORDER BY {order_by} {order} LIMIT {(page - 1) * pagelimit}, {pagelimit}")
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
        ret.append({"name": tt[1], "discordid": f"{tt[2]}", "banned": TF[banned], "banreason": banreason, "join_timestamp": tt[3]})
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid < 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot)}}

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

    return {"error": False, "response": {"bio": bio}}
    
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
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    old_discord_id = int(form["old_discord_id"])
    new_discord_id = int(form["new_discord_id"])

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

    return {"error": False, "response": {"discordid": str(new_discord_id)}}
    
@app.delete(f"/{config.vtc_abbr}/user/connection")
async def deleteUserConnection(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/connection', 180, 10)
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
    
@app.delete(f"/{config.vtc_abbr}/user/delete")
async def deleteUser(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /user/delete', 180, 10)
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