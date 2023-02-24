# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *


@app.get(f"/{config.abbr}/announcement")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), announcementid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /announcement', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization != None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await activityUpdate(dhrid, au["discordid"], "announcements")

    if int(announcementid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = aulanguage)}
        
    await aiosql.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid = {announcementid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = aulanguage)}
    tt = t[0]
    return {"error": False, "response": {"announcement": {"announcementid": str(tt[5]), \
        "title": tt[0], "content": decompress(tt[1]), "author": await getUserInfo(dhrid, userid = tt[4]), \
            "announcement_type": str(tt[2]), "is_private": TF[tt[6]], "timestamp": str(tt[3])}}}

@app.get(f"/{config.abbr}/announcement/list")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int]= -1, page_size: Optional[int] = 10, order: Optional[str] = "desc", order_by: Optional[str] = "announcementid", \
        title: Optional[str] = ""):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /announcement/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization != None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await activityUpdate(dhrid, au["discordid"], "announcements")
    
    limit = ""
    if userid == -1:
        limit = "AND is_private = 0 "
    if title != "":
        title = convert_quotation(title)
        limit += f"AND title LIKE '%{title[:200]}%' "

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100
    
    if not order_by in ["announcementid", "title"]:
        order_by = "announcementidid"
        order = "asc"
    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    if page <= 0:
        page = 1

    await aiosql.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"announcementid": str(tt[5]), "title": tt[0], "content": decompress(tt[1]), \
            "author": await getUserInfo(dhrid, userid = tt[4]), "announcement_type": str(tt[2]), "is_private": TF[tt[6]], \
                "timestamp": str(tt[3])})
        
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM announcement WHERE announcementid >= 0 {limit}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.post(f"/{config.abbr}/announcement")
async def postAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /announcement', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    adminname = au["name"]
    
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        content = compress(form["content"])
        if len(form["title"]) > 200:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(form["content"]) > 2000:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        discord_message_content = str(form["discord_message_content"])
        announcement_type = int(form["announcement_type"])
        channelid = int(form["channelid"])
        is_private = 0
        if form["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if not isAdmin and announcement_type != 1:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "event_staff_announcement_limit", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtannid' FOR UPDATE")
    t = await aiosql.fetchall(dhrid)
    announcementid = int(t[0][0])
    await aiosql.execute(dhrid, f"UPDATE settings SET sval = {announcementid+1} WHERE skey = 'nxtannid'")
    await aiosql.commit(dhrid)
    timestamp = int(time.time())

    await aiosql.execute(dhrid, f"INSERT INTO announcement VALUES ({announcementid}, {adminid}, '{title}', '{content}', {announcement_type}, {timestamp}, {is_private})")
    await AuditLog(dhrid, adminid, f"Created announcement `#{announcementid}`")
    await aiosql.commit(dhrid)

    if channelid != 0 and config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", headers=headers, data=json.dumps({"content": discord_message_content, "embeds": [{"title": title, "description": decompress(content), 
                "footer": {"text": f"{adminname}", "icon_url": await getAvatarSrc(dhrid, adminid)}, "thumbnail": {"url": config.logo_url},\
                        "timestamp": str(datetime.now()), "color": config.intcolor, "color": config.intcolor}]}))
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return {"error": False, "response": {"announcementid": str(announcementid)}}

@app.patch(f"/{config.abbr}/announcement")
async def patchAnnouncement(request: Request, response: Response, authorization: str = Header(None), announcementid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /announcement', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    adminname = au["name"]
    
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        content = compress(form["content"])
        if len(form["title"]) > 200:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(form["content"]) > 2000:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        discord_message_content = str(form["discord_message_content"])
        announcement_type = int(form["announcement_type"])
        channelid = int(form["channelid"])
        is_private = 0
        if form["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if int(announcementid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    await aiosql.execute(dhrid, f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    creator = t[0][0]
    if creator != adminid and not isAdmin:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_edit", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE announcement SET title = '{title}', content = '{content}', announcement_type = {announcement_type}, is_private = {is_private} WHERE announcementid = {announcementid}")
    await AuditLog(dhrid, adminid, f"Updated announcement `#{announcementid}`")
    await aiosql.commit(dhrid)

    if channelid != 0 and config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            await arequests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", headers=headers, data=json.dumps({"content": discord_message_content, "embeds": [{"title": title, "description": decompress(content), 
                "footer": {"text": f"{adminname}", "icon_url": await getAvatarSrc(dhrid, adminid)}, "thumbnail": {"url": config.logo_url},\
                        "timestamp": str(datetime.now()), "color": config.intcolor}]}))
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return {"error": False}

@app.delete(f"/{config.abbr}/announcement")
async def deleteAnnouncement(request: Request, response: Response, authorization: str = Header(None), announcementid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /announcement', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event", "announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]
    
    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.announcement:
            isAdmin = True

    if int(announcementid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    await aiosql.execute(dhrid, f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    creator = t[0][0]
    if creator != adminid and not isAdmin: # creator or leadership
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "announcement_only_creator_can_delete", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM announcement WHERE announcementid = {announcementid}")
    await AuditLog(dhrid, adminid, f"Deleted announcement `#{announcementid}`")
    await aiosql.commit(dhrid)

    return {"error": False}