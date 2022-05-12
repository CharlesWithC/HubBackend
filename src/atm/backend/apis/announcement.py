# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math, validators
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *

@app.get("/atm/announcement")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), page: Optional[int]= -1, aid: Optional[int] = -1):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    userid = -1
    if stoken != "guest":
        isapptoken = False
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
            t = cur.fetchall()
            if len(t) == 0:
                response.status_code = 401
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
                    response.status_code = 401
                    return {"error": True, "descriptor": "401: Unauthroized"}
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

    if aid != -1:
        cur.execute(f"SELECT title, content, atype, timestamp, userid, aid FROM announcement WHERE aid = {aid} {limit}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Announcement not found"}
        tt = t[0]
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        return {"error": False, "response": {"aid": tt[5], "title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "by":name, "timestamp": tt[3]}}

    if page <= 0:
        page = 1

    cur.execute(f"SELECT title, content, atype, timestamp, userid, aid FROM announcement WHERE aid >= 0 {limit} ORDER BY timestamp DESC LIMIT {(page-1) * 10}, 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        ret.append({"aid": tt[5], "title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "by":name, "timestamp": tt[3]})
        
    cur.execute(f"SELECT COUNT(*) FROM announcement WHERE aid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

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
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtannid'")
    t = cur.fetchall()
    aid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {aid+1} WHERE skey = 'nxtannid'")
    conn.commit()

    form = await request.form()
    title = b64e(form["title"])
    content = b64e(form["content"])
    atype = int(form["atype"])
    timestamp = int(time.time())
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1
    channelid = form["channelid"]
    if not channelid.isdigit():
        channleid = 0

    cur.execute(f"INSERT INTO announcement VALUES ({aid}, {adminid}, '{title}', '{content}', {atype}, {timestamp}, {pvt})")
    await AuditLog(adminid, f"Created announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            role = "<@&929761730089877634>"
            if pvt == 1:
                role = "<@&941548239776272454>"
            headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": role, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                            "timestamp": str(datetime.now()), "color": 11730944, "color": 11730944}}))
        except:
            pass

    return {"error": False, "response": {"message": "Announcement created.", "aid": aid}}

@app.patch("/atm/announcement")
async def patchAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
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

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1
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
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', atype = {atype} WHERE aid = {aid}")
    await AuditLog(adminid, f"Updated announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            role = "<@&929761730089877634>"
            if pvt == 1:
                role = "<@&941548239776272454>"
            headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": role, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                            "timestamp": str(datetime.now()), "color": 11730944}}))
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

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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