# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from datetime import datetime
import json, time, requests, math

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.abbr}/announcement")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int]= -1, page_size: Optional[int] = 10, order: Optional[str] = "desc", order_by: Optional[str] = "announcementid", \
        announcementid: Optional[int] = -1, title: Optional[str] = ""):
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
        limit = "AND is_private = 0 "
    if title != "":
        title = convert_quotation(title)
        limit += f"AND title LIKE '%{title}%' "

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100
    
    if not order_by in ["announcementid", "title"]:
        order_by = "announcementidid"
    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    if announcementid != -1:
        if int(announcementid) < 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
            
        cur.execute(f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid = {announcementid} {limit}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
        tt = t[0]
        return {"error": False, "response": {"announcementid": str(tt[5]), "title": tt[0], "content": decompress(tt[1]), \
            "author": getUserInfo(userid = tt[4]), "announcement_type": str(tt[2]), "is_private": TF[tt[6]], \
                "timestamp": str(tt[3])}}

    if page <= 0:
        page = 1

    cur.execute(f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"announcementid": str(tt[5]), "title": tt[0], "content": decompress(tt[1]), \
            "author": getUserInfo(userid = tt[4]), "announcement_type": str(tt[2]), "is_private": TF[tt[6]], \
                "timestamp": str(tt[3])})
        
    cur.execute(f"SELECT COUNT(*) FROM announcement WHERE announcementid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.post(f"/{config.abbr}/announcement")
async def postAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /announcement', 180, 5)
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
    try:
        title = convert_quotation(form["title"])
        content = compress(form["content"])
        discord_message_content = str(form["discord_message_content"])
        announcement_type = int(form["announcement_type"])
        channelid = int(form["channelid"])
        is_private = 0
        if form["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    if not isAdmin and announcement_type != 1:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "event_staff_announcement_limit")}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtannid'")
    t = cur.fetchall()
    announcementid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {announcementid+1} WHERE skey = 'nxtannid'")
    conn.commit()
    timestamp = int(time.time())

    cur.execute(f"INSERT INTO announcement VALUES ({announcementid}, {adminid}, '{title}', '{content}', {announcement_type}, {timestamp}, {is_private})")
    await AuditLog(adminid, f"Created announcement `#{announcementid}`")
    conn.commit()

    if channelid != 0:
        try:
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": discord_message_content, "embed": {"title": title, "description": decompress(content), 
                    "footer": {"text": f"{adminname}", "icon_url": getAvatarSrc(adminid)}, "thumbnail": {"url": config.logo_url},\
                            "timestamp": str(datetime.now()), "color": config.intcolor, "color": config.intcolor}}))
        except:
            pass

    return {"error": False, "response": {"announcementid": str(announcementid)}}

@app.patch(f"/{config.abbr}/announcement")
async def patchAnnouncement(request: Request, response: Response, authorization: str = Header(None), announcementid: Optional[int] = -1):
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
    try:
        title = convert_quotation(form["title"])
        content = compress(form["content"])
        discord_message_content = str(form["discord_message_content"])
        announcement_type = int(form["announcement_type"])
        channelid = int(form["channelid"])
        is_private = 0
        if form["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    if int(announcementid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    cur.execute(f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_edit")}
    
    cur.execute(f"UPDATE announcement SET title = '{title}', content = '{content}', announcement_type = {announcement_type} WHERE announcementid = {announcementid}")
    await AuditLog(adminid, f"Updated announcement `#{announcementid}`")
    conn.commit()

    if channelid != 0:
        try:
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"content": discord_message_content, "embed": {"title": title, "description": decompress(content), 
                    "footer": {"text": f"{adminname}", "icon_url": getAvatarSrc(adminid)}, "thumbnail": {"url": config.logo_url},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}))
        except:
            pass

    return {"error": False}

@app.delete(f"/{config.abbr}/announcement")
async def deleteAnnouncement(request: Request, response: Response, authorization: str = Header(None), announcementid: Optional[int] = -1):
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

    if int(announcementid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    cur.execute(f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found")}
    creator = t[0][0]
    if creator != adminid and not isAdmin: # creator or leadership
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_delete")}
    
    cur.execute(f"DELETE FROM announcement WHERE announcementid = {announcementid}")
    await AuditLog(adminid, f"Deleted announcement `#{announcementid}`")
    conn.commit()

    return {"error": False}