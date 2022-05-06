# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
import json, time, math
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *

@app.get("/atm/announcement")
async def getAnnouncement(page: int, response: Response):
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT title, content, atype, timestamp FROM announcement WHERE aid >= 0 ORDER BY timestamp DESC")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "timestamp": tt[3]})
    totpage = math.ceil(len(ret) / 10)
    ret = ret[(page - 1) * 10 : page * 10]

    return {"error": False, "response": {"list": ret, "page": page, "tot": totpage}}

@app.post("/atm/announcement")
async def postAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
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

    ok = False
    if adminhighest <= 10 or "40" in adminroles or "41" in adminroles: # Leadership + Event Staff
        ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT COUNT(*) FROM announcement")
    t = cur.fetchall()
    aid = 0
    if len(t) > 0:
        aid = t[0][0]

    form = await request.form()
    title = b64e(form["title"])
    content = b64e(form["content"])
    atype = int(form["atype"])
    timestamp = int(time.time())

    cur.execute(f"INSERT INTO announcement VALUES ({aid}, {adminid}, '{title}', '{content}', {atype}, {timestamp})")
    await AuditLog(adminid, f"Created announcement #{aid}")
    conn.commit()

    return {"error": False, "response": {"message": "Announcement created.", "aid": aid}}

@app.patch("/atm/announcement")
async def deleteAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
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

    ok = False
    if adminhighest <= 10 or "40" in adminroles or "41" in adminroles: # Leadership + Event Staff
        ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    aid = int(form["aid"])
    title = b64e(form["title"])
    content = b64e(form["content"])
    atype = int(form["atype"])

    cur.execute(f"SELECT * FROM announcement WHERE aid = {aid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Announcement not found!"}
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', atype = {atype} WHERE aid = {aid}")
    await AuditLog(adminid, f"Updated announcement #{aid}")
    conn.commit()

    return {"error": False, "response": {"message": "Announcement updated.", "aid": aid}}

@app.delete("/atm/announcement")
async def deleteAnnouncement(aid: int, request: Request, response: Response, authorization: str = Header(None)):
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

    ok = False
    if adminhighest <= 10 or "40" in adminroles or "41" in adminroles: # Leadership + Event Staff
        ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT * FROM announcement WHERE aid = {aid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Announcement not found!"}
    
    cur.execute(f"UPDATE announcement SET aid = -aid WHERE aid = {aid}")
    await AuditLog(adminid, f"Deleted announcement #{aid}")
    conn.commit()

    return {"error": False, "response": {"message": "Announcement deleted."}}