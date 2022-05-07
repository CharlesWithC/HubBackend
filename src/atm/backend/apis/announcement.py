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
async def getAnnouncement(page: int, response: Response, authorization: str = Header(None)):
    conn = newconn()
    cur = conn.cursor()
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
    userid = t[0][0]
    roles = t[0][1].split(",")
    limit = ""
    if userid == -1 or "10000" in roles: # external staff / not registered
        limit = "AND pvt = 0"

    cur.execute(f"SELECT title, content, atype, timestamp, userid, aid FROM announcement WHERE aid >= 0 {limit} ORDER BY timestamp DESC")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        ret.append({"aid": tt[5], "title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "by":name, "timestamp": tt[3]})
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
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
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

    if adminhighest >= 10 and not "40" in adminroles and not "41" in adminroles:
        return {"error": True, "descriptor": "Event staff can only post event announcements."}

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
    pvt = int(bool(form["pvt"]))
    channelid = form["channelid"]
    if not channelid.isdigit():
        channleid = 0

    cur.execute(f"INSERT INTO announcement VALUES ({aid}, {adminid}, '{title}', '{content}', {atype}, {timestamp}, {pvt})")
    await AuditLog(adminid, f"Created announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": "<@&929761730089877634>", "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                            "timestamp": str(datetime.now())}}))
        except:
            pass

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
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
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
    pvt = int(bool(form["pvt"]))
    channelid = form["channelid"]
    if not channelid.isdigit():
        channleid = 0

    cur.execute(f"SELECT userid FROM announcement WHERE aid = {aid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Announcement not found!"}
    creator = t[0][0]
    if creator != adminid and adminhighest >= 10:
        return {"error": True, "descriptor": "Only announcement creator can edit it."}

    if adminhighest >= 10 and not "40" in adminroles and not "41" in adminroles:
        return {"error": True, "descriptor": "Event staff can only post event announcements."}
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', atype = {atype} WHERE aid = {aid}")
    await AuditLog(adminid, f"Updated announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": "<@&929761730089877634>", "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                            "timestamp": str(datetime.now())}}))
        except:
            pass

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
    creator = t[0][0]
    if creator != adminid and adminhighest >= 10: # creator or leadership
        return {"error": True, "descriptor": "Only announcement creator can delete it."}
    
    cur.execute(f"UPDATE announcement SET aid = -aid WHERE aid = {aid}")
    await AuditLog(adminid, f"Deleted announcement #{aid}")
    conn.commit()

    return {"error": False, "response": {"message": "Announcement deleted."}}