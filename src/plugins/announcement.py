# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from datetime import datetime
import json, time, requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.vtc_abbr}/announcements")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int]= -1, aid: Optional[int] = -1, order: Optional[str] = "desc", pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /announcement', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = "guest"
    if authorization != None:
        stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            userid = -1
        else:
            userid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    limit = ""
    if userid == -1:
        limit = "AND pvt = 0"

    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 100:
        pagelimit = 100

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    if aid != -1:
        cur.execute(f"SELECT title, content, atype, timestamp, userid, aid, pvt FROM announcement WHERE aid = {aid} {limit}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
        tt = t[0]
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        return {"error": False, "response": {"aid": str(tt[5]), "title": b64d(tt[0]), "content": b64d(tt[1]), \
            "atype": str(tt[2]), "by": name, "timestamp": str(tt[3]), "private": TF[tt[6]]}}

    if page <= 0:
        page = 1

    cur.execute(f"SELECT title, content, atype, timestamp, userid, aid, pvt FROM announcement WHERE aid >= 0 {limit} ORDER BY aid {order} LIMIT {(page-1) * pagelimit}, {pagelimit}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        ret.append({"aid": str(tt[5]), "title": b64d(tt[0]), "content": b64d(tt[1]), \
            "atype": str(tt[2]), "by": name, "byuserid": str(tt[4]), "timestamp": str(tt[3]), "private": TF[tt[6]]})
        
    cur.execute(f"SELECT COUNT(*) FROM announcement WHERE aid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot)}}

@app.post(f"/{config.vtc_abbr}/announcement")
async def postAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /announcement', 180, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    adminname = au["name"]
    
    conn = newconn()
    cur = conn.cursor()
    
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    form = await request.form()
    title = b64e(form["title"])
    content = b64e(form["content"])
    discord_message_content = form["discord_message_content"]
    atype = int(form["atype"])

    if not isAdmin and atype != 1:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "event_staff_announcement_limit")}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtannid'")
    t = cur.fetchall()
    aid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {aid+1} WHERE skey = 'nxtannid'")
    conn.commit()
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
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": discord_message_content, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                            "timestamp": str(datetime.now()), "color": config.intcolor, "color": config.intcolor}}))
        except:
            pass

    return {"error": False, "response": {"aid": str(aid)}}

@app.patch(f"/{config.vtc_abbr}/announcement")
async def patchAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /announcement', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    adminname = au["name"]
    
    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    form = await request.form()
    aid = int(form["aid"])
    title = b64e(form["title"])
    content = b64e(form["content"])
    discord_message_content = form["discord_message_content"]
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
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_edit")}
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', atype = {atype} WHERE aid = {aid}")
    await AuditLog(adminid, f"Updated announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": discord_message_content, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}))
        except:
            pass

    return {"error": False, "response": {"aid": str(aid)}}

@app.delete(f"/{config.vtc_abbr}/announcement")
async def deleteAnnouncement(aid: int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /announcement', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    
    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    cur.execute(f"SELECT userid FROM announcement WHERE aid = {aid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin: # creator or leadership
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_delete")}
    
    cur.execute(f"UPDATE announcement SET aid = -aid WHERE aid = {aid}")
    await AuditLog(adminid, f"Deleted announcement #{aid}")
    conn.commit()

    return {"error": False}