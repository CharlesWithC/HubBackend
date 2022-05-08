# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
from typing import Optional
import json, time, requests, math

from app import app, config
from db import newconn
from functions import *

@app.post('/atm/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = form["discordid"]
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Invalid discordid."}

    cur.execute(f"SELECT roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        roles = t[0][0]
        userroles = t[0][0].split(",")
        while "" in userroles:
            userroles.remove("")
        userhighest = 99999
        for i in userroles:
            if int(i) < userhighest:
                userhighest = int(i)
        if userhighest <= adminhighest:
            # response.status_code = 401
            return {"error": True, "descriptor": "User has higher / equal role."}

    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO banned VALUES ({discordid})")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()
        await AuditLog(adminid, f"Banned user with Discord ID `{discordid}`")
        return {"error": False, "response": {"response_message": "User banned.", "discordid": discordid}}
    else:
        return {"error": True, "descriptor": "User already banned."}

@app.post('/atm/user/unban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = form["discordid"]
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
        return {"error": False, "response": {"response_message": "User unbanned.", "discordid": discordid}}

@app.get("/atm/user/list")
async def userList(page:int, request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    cur.execute(f"SELECT userid, name, discordid FROM user WHERE userid < 0")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"name": tt[1], "discordid": f"{tt[2]}"})
    totpage = math.ceil(len(ret)/30)
    ret = ret[(page-1)*30:page*30]
    return {"error": False, "response": {"list": ret, "page": page, "tot": totpage}}

@app.get('/atm/user/info')
async def userInfo(response: Response, authorization: str = Header(None), qdiscordid: Optional[int] = 0):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    adminhighest = 99999
    for i in roles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if discordid != qdiscordid and qdiscordid != 0:
        print("Checking non-me")
        if adminhighest >= 30:
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    if discordid == qdiscordid:    
        cur.execute(f"SELECT userid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()

    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    return {"error": False, "response": {"userid": t[0][0], "name": t[0][1], "email": t[0][8], "discordid": f"{discordid}", "avatar": t[0][2], "bio": b64e(t[0][7]), "roles": roles, "join": t[0][4], "truckesmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}"}}

@app.post('/atm/user/bio')
async def updateUserBio(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]

    form = await request.form()
    bio = form["bio"]
    if len(bio) > 500:
        # response.status_code = 400
        return {"error": True, "descriptor": "Bio too long."}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False, "response": {"message": "Bio updated.", "bio": bio}}