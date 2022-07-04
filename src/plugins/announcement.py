# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.vtcprefix}/announcement")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), page: Optional[int]= -1, aid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /announcement', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    userid = -1
    roles = []
    if stoken != "guest":
        isapptoken = False
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
            t = cur.fetchall()
            if len(t) == 0:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
            isapptoken = True
        discordid = t[0][0]
        if not isapptoken:
            ip = t[0][1]
            orgiptype = 4
            if iptype(ip) == "ipv6":
                orgiptype = 6
            curiptype = 4
            if iptype(request.client.host) == "ipv6":
                curiptype = 6
            if orgiptype != curiptype:
                cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                conn.commit()
            else:
                if ip != request.client.host:
                    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                    conn.commit()
                    response.status_code = 401
                    return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        userid = t[0][0]
        roles = t[0][1].split(",")
        while "" in roles:
            roles.remove("")

    limit = ""
    ok = False
    for i in roles:
        if int(i) in config.perms.driver or int(i) in config.perms.admin:
            ok = True
    if userid == -1 or not ok:
        limit = "AND pvt = 0"

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
        return {"error": False, "response": {"aid": tt[5], "title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "by":name, "timestamp": tt[3], "private": tt[6]}}

    if page <= 0:
        page = 1

    cur.execute(f"SELECT title, content, atype, timestamp, userid, aid, pvt FROM announcement WHERE aid >= 0 {limit} ORDER BY timestamp DESC LIMIT {(page-1) * 10}, 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[4]}")
        n = cur.fetchall()
        name = "Unknown User"
        if len(n) > 0:
            name = n[0][0]
        ret.append({"aid": tt[5], "title": b64d(tt[0]), "content": b64d(tt[1]), "atype": tt[2], "by":name, "byuserid": tt[4], "timestamp": tt[3], "private": tt[6]})
        
    cur.execute(f"SELECT COUNT(*) FROM announcement WHERE aid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.post(f"/{config.vtcprefix}/announcement")
async def postAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /announcement', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")
    
    ok = False
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    if not isAdmin and atype == 1:
        return {"error": True, "descriptor": ml.tr(request, "event_staff_announcement_limit")}

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
            role = config.public_news_role
            if pvt == 1:
                role = config.private_news_role
            headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": role, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.vtclogo}, "thumbnail": {"url": config.vtclogo},\
                            "timestamp": str(datetime.now()), "color": config.intcolor, "color": config.intcolor}}))
        except:
            pass

    return {"error": False, "response": {"aid": aid}}

@app.patch(f"/{config.vtcprefix}/announcement")
async def patchAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /announcement', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")

    ok = False
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

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
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin:
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_edit")}
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', atype = {atype} WHERE aid = {aid}")
    await AuditLog(adminid, f"Updated announcement #{aid}")
    conn.commit()

    if channelid != 0:
        try:
            role = config.public_news_role
            if pvt == 1:
                role = config.private_news_role
            headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": role, "embed": {"title": b64d(title), "description": b64d(content), 
                    "footer": {"text": f"By {adminname}", "icon_url": config.vtclogo}, "thumbnail": {"url": config.vtclogo},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}))
        except:
            pass

    return {"error": False, "response": {"aid": aid}}

@app.delete(f"/{config.vtcprefix}/announcement")
async def deleteAnnouncement(aid: int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /announcement', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")

    ok = False
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    cur.execute(f"SELECT * FROM announcement WHERE aid = {aid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin: # creator or leadership
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_delete")}
    
    cur.execute(f"UPDATE announcement SET aid = -aid WHERE aid = {aid}")
    await AuditLog(adminid, f"Deleted announcement #{aid}")
    conn.commit()

    return {"error": False}