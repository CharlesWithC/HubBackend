# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int]= -1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", \
        after_announcementid: Optional[int] = None, query: Optional[str] = "", announcement_type: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /announcements/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization is not None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            await ActivityUpdate(request, au["uid"], "announcements")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    if order_by not in ["orderid", "announcementid", "title", "timestamp"]:
        order_by = "orderid"
        order = "asc"
    if order not in ["asc", "desc"]:
        order = "asc"

    limit = ""
    if userid == -1:
        limit = "AND is_private = 0 "
    if query != "":
        query = convertQuotation(query)
        limit += f"AND title LIKE '%{query[:200]}%' "
    if announcement_type is not None:
        limit += f"AND announcement_type = {announcement_type} "

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT announcementid FROM announcement WHERE announcementid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, timestamp DESC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_announcementid is not None:
        for tt in t:
            if tt[0] == after_announcementid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private, orderid, is_pinned FROM announcement WHERE announcementid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, timestamp DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(request, userid = tt[4]), "announcement_type": tt[2], "is_private": TF[tt[6]], "orderid": tt[7], "is_pinned": TF[tt[8]], "timestamp": tt[3]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM announcement WHERE announcementid >= 0 {limit}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /announcements', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if authorization is not None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            aulanguage = au["language"]
            await ActivityUpdate(request, au["uid"], "announcements")

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private, orderid, is_pinned FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = aulanguage)}
    tt = t[0]

    return {"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(request, userid = tt[4]), "announcement_type": tt[2], "is_private": TF[tt[6]], "orderid": tt[7], "is_pinned": TF[tt[8]], "timestamp": tt[3]}

async def post_announcement(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
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
        is_private = int(bool(data["is_private"]))
        orderid = int(data["orderid"])
        if orderid < -2147483647 or orderid > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    timestamp = int(time.time())

    await app.db.execute(dhrid, f"INSERT INTO announcement(userid, title, content, announcement_type, timestamp, is_private, orderid INT, is_pinned INT) VALUES ({au['userid']}, '{title}', '{content}', {announcement_type}, {timestamp}, {is_private}, {orderid}, {is_pinned})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    announcementid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], ml.ctr(request, "created_announcement", var = {"id": announcementid}))

    return {"announcementid": announcementid}

async def patch_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffroles = au["roles"]

    await app.db.execute(dhrid, f"SELECT userid, title, content, announcement_type, is_private, orderid, is_pinned FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    (authorid, title, content, announcement_type, is_private, orderid, is_pinned) = t[0]

    data = await request.json()
    try:
        if "title" in data.keys():
            title = convertQuotation(data["title"])
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "content" in data.keys():
            content = compress(data["content"])
            if len(data["content"]) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        if "announcement_type" in data.keys():
            announcement_type = int(data["announcement_type"])
        if "is_private" in data.keys():
            is_private = int(bool(data["is_private"]))
        if "orderid" in data.keys():
            orderid = int(data["orderid"])
            if orderid < -2147483647 or orderid > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_pinned" in data.keys():
            is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    if authorid != au["userid"] and not checkPerm(app, staffroles, "admin"):
        response.status_code = 403
        return {"error": ml.tr(request, "announcement_only_creator_can_edit", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE announcement SET title = '{title}', content = '{content}', announcement_type = {announcement_type}, is_private = {is_private}, orderid = {orderid}, is_pinned = {is_pinned} WHERE announcementid = {announcementid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "updated_announcement", var = {"id": announcementid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_announcement(request: Request, response: Response, announcementid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin","announcement"])
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
    if authorid != au["userid"] and not checkPerm(app, staffroles, "admin"): # creator or leadership
        response.status_code = 403
        return {"error": ml.tr(request, "announcement_only_creator_can_delete", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM announcement WHERE announcementid = {announcementid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_announcement", var = {"id": announcementid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)
