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
from app import app
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int]= -1, page_size: Optional[int] = 10, order: Optional[str] = "desc", \
        order_by: Optional[str] = "announcementid", query: Optional[str] = ""):
    if "announcement" not in app.config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /announcements/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization is not None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            await ActivityUpdate(dhrid, au["uid"], "announcements")
    
    limit = ""
    if userid == -1:
        limit = "AND is_private = 0 "
    if query != "":
        query = convertQuotation(query)
        limit += f"AND title LIKE '%{query[:200]}%' "

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

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(dhrid, request, userid = tt[4]), "announcement_type": tt[2], "is_private": TF[tt[6]], "timestamp": tt[3]})
        
    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM announcement WHERE announcementid >= 0 {limit}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    if "announcement" not in app.config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /announcements', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if authorization is not None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            aulanguage = au["language"]
            await ActivityUpdate(dhrid, au["uid"], "announcements")

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = aulanguage)}
    tt = t[0]

    return {"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(dhrid, request, userid = tt[4]), "announcement_type": tt[2], "is_private": TF[tt[6]], "timestamp": tt[3]}

async def post_announcement(request: Request, response: Response, authorization: str = Header(None)):
    if "announcement" not in app.config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        content = compress(data["content"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["content"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        announcement_type = int(data["announcement_type"])
        is_private = int(data["is_private"])
        try:
            discord_channel_id = None
            discord_channel_id = int(data["discord_channel_id"])
            discord_message_content = str(data["discord_message_content"])
        except:
            pass
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    timestamp = int(time.time())

    await app.db.execute(dhrid, f"INSERT INTO announcement(userid, title, content, announcement_type, timestamp, is_private) VALUES ({au['userid']}, '{title}', '{content}', {announcement_type}, {timestamp}, {is_private})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    announcementid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(dhrid, au["uid"], ml.ctr("created_announcement", var = {"id": announcementid}))

    if discord_channel_id is not None and app.config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post(f"https://discord.com/api/v10/channels/{discord_channel_id}/messages", headers=headers, data=json.dumps({"content": discord_message_content, "embeds": [{"title": title, "description": decompress(content), "footer": {"text": f"{au['name']}", "icon_url": (await GetUserInfo(dhrid, request, userid = au['userid']))["avatar"]}, "thumbnail": {"url": app.config.logo_url},"timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}))
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return {"announcementid": announcementid}

async def patch_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    if "announcement" not in app.config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffroles = au["roles"]

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        content = compress(data["content"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["content"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        announcement_type = int(data["announcement_type"])
        is_private = int(data["is_private"])
        try:
            discord_channel_id = None
            discord_channel_id = int(data["discord_channel_id"])
            discord_message_content = str(data["discord_message_content"])
        except:
            pass
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    authorid = t[0][0]
    if authorid != au["userid"] and not checkPerm(staffroles, "admin"):
        response.status_code = 403
        return {"error": ml.tr(request, "announcement_only_creator_can_edit", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"UPDATE announcement SET title = '{title}', content = '{content}', announcement_type = {announcement_type}, is_private = {is_private} WHERE announcementid = {announcementid}")
    await AuditLog(dhrid, au["uid"], ml.ctr("updated_announcement", var = {"id": announcementid}))
    await app.db.commit(dhrid)

    if discord_channel_id is not None and app.config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post(f"https://discord.com/api/v10/channels/{discord_channel_id}/messages", headers=headers, data=json.dumps({"content": discord_message_content, "embeds": [{"title": title, "description": decompress(content), "footer": {"text": f"{au['name']}", "icon_url": (await GetUserInfo(dhrid, request, userid = au["userid"]))["avatar"]}, "thumbnail": {"url": app.config.logo_url}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}))
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return Response(status_code=204)

async def delete_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    if "announcement" not in app.config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)
    
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffroles = au["roles"]

    await app.db.execute(dhrid, f"SELECT userid FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    authorid = t[0][0]
    if authorid != au["userid"] and not checkPerm(staffroles, "admin"): # creator or leadership
        response.status_code = 403
        return {"error": ml.tr(request, "announcement_only_creator_can_delete", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"DELETE FROM announcement WHERE announcementid = {announcementid}")
    await AuditLog(dhrid, au["uid"], ml.ctr("deleted_announcement", var = {"id": announcementid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)