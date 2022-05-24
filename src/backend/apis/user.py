# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
from typing import Optional
import json, time, requests, math, validators

from app import app, config
from db import newconn
from functions import *

@app.post('/atm/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
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
        return {"error": True, "descriptor": "Invalid discordid."}

    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    username = "Unknown User"
    if len(t) > 0:
        roles = t[0][1]
        userroles = roles.split(",")
        while "" in userroles:
            userroles.remove("")
        userhighest = 99999
        for i in userroles:
            if int(i) < userhighest:
                userhighest = int(i)
        if userhighest <= adminhighest:
            # # response.status_code = 401
            return {"error": True, "descriptor": "User has higher / equal role."}
        userid = t[0][0]
        username = t[0][2]

        if userid != -1:
            return {"error": True, "descriptor": "Dismiss member before banning."}

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
        return {"error": False, "response": {"message": "User banned.", "discordid": discordid}}
    else:
        return {"error": True, "descriptor": "User already banned."}

@app.post('/atm/user/unban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = int(form["discordid"])
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Invalid discordid."}
    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "User not banned."}
    else:
        cur.execute(f"DELETE FROM banned WHERE discordid = {discordid}")
        conn.commit()
        await AuditLog(adminid, f"Unbanned user with Discord ID `{discordid}`")
        return {"error": False, "response": {"message": "User unbanned.", "discordid": discordid}}

@app.get("/atm/user/list")
async def userList(page:int, request: Request, response: Response, authorization: str = Header(None)):
    if page <= 0:
        page = 1
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    roles = t[0][1].split(",")
    while "" in roles:
        roles.remove("")
    adminhighest = 99999
    for i in roles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    
    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
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

@app.get('/atm/user/info')
async def userInfo(request: Request, response: Response, authorization: str = Header(None), qdiscordid: Optional[int] = 0):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT userid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    adminhighest = 99999
    for i in roles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    
    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    email = t[0][8]
    if isapptoken:
        email = None
    return {"error": False, "response": {"userid": t[0][0], "name": t[0][1], "email": email, "discordid": f"{discordid}", "avatar": t[0][2], "bio": b64e(t[0][7]), "roles": roles, "join": t[0][4], "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}"}}

@app.post('/atm/user/bio')
async def updateUserBio(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    bio = form["bio"]
    if len(bio) > 500:
        # response.status_code = 400
        return {"error": True, "descriptor": "Bio too long."}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False, "response": {"message": "Bio updated.", "bio": bio}}

@app.get("/atm/auditlog")
async def getAuditLog(page: int, request: Request, response: Response, authorization: str = Header(None)):
    if page <= 0:
        page = 1
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    if adminhighest >= 100: # any staff
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT * FROM auditlog ORDER BY timestamp DESC LIMIT {(page - 1) * 30}, 30")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        name = "Unknown"
        if len(p) > 0:
            name = p[0][0]
        ret.append({"timestamp": tt[2], "user": name, "operation": tt[1]})

    cur.execute(f"SELECT COUNT(*) FROM auditlog")
    t = cur.fetchall()
    tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}