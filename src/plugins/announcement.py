# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Query, Response

import multilang as ml
from functions import *

async def get_types(request: Request):
    app = request.app

    return app.config.announcement_types

def get_type(request, type_id: int, force_lang: Optional[str] = ""):
    app = request.app
    ret = {"id": type_id, "name": ml.tr(request, "unknown", force_lang = force_lang)}
    for announcement_type in app.config.announcement_types:
        if announcement_type["id"] == type_id:
            ret["name"] = announcement_type["name"]
            break
    return ret

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int]= -1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", is_private: Optional[bool] = None, \
        created_by: Optional[int] = None, created_after: Optional[int] = None, created_before: Optional[int] = None, \
        after_announcementid: Optional[int] = None, title: Optional[str] = "", announcement_type: Optional[int] = Query(None, alias='type')):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /announcements/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    aulanguage = ""
    if authorization is not None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await ActivityUpdate(request, au["uid"], "announcements")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if order_by not in ["orderid", "announcementid", "title", "timestamp"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    limit = ""
    if userid in [-1, None]:
        limit = "AND is_private = 0 "
    if title != "":
        title = convertQuotation(title)
        limit += f"AND title LIKE '%{title}%' "
    if announcement_type is not None:
        limit += f"AND announcement_type = {announcement_type} "
    if created_after is not None:
        limit += f"AND timestamp >= {created_after} "
    if created_before is not None:
        limit += f"AND timestamp <= {created_before} "
    if created_by is not None:
        limit += f"AND userid = {created_by} "
    if is_private is not None:
        if is_private:
            limit += "AND is_private = 1 "
        else:
            limit += "AND is_private = 0 "

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT announcementid FROM announcement WHERE announcementid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, announcementid DESC")
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

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, timestamp, userid, announcementid, is_private, orderid, is_pinned FROM announcement WHERE announcementid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, announcementid DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(request, userid = tt[4]), "type": get_type(request, tt[2], aulanguage), "is_private": TF[tt[6]], "orderid": tt[7], "is_pinned": TF[tt[8]], "timestamp": tt[3]})

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

    aulanguage = ""
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

    return {"announcementid": tt[5], "title": tt[0], "content": decompress(tt[1]), "author": await GetUserInfo(request, userid = tt[4]), "type": get_type(request, tt[2], aulanguage), "is_private": TF[tt[6]], "orderid": tt[7], "is_pinned": TF[tt[8]], "timestamp": tt[3]}

async def post_announcement(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /announcements', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator","manage_announcements"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = data["title"]
        content = data["content"]
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["content"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        announcement_type = int(data["type"])
        if abs(announcement_type) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "type", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_private" not in data.keys():
            data["is_private"] = False
        is_private = int(bool(data["is_private"]))
        if "orderid" not in data.keys():
            data["orderid"] = 0
        if "is_pinned" not in data.keys():
            data["is_pinned"] = False
        orderid = int(data["orderid"])
        if abs(orderid) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    tatype = None
    for atype in app.config.announcement_types:
        if atype["id"] == announcement_type:
            tatype = atype
            break
    if tatype is None:
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_announcement_type", force_lang = au["language"])}
    ok = False
    for role in au["roles"]:
        if role in tatype["staff_role_ids"]:
            ok = True
    if not ok and not checkPerm(app, au["roles"], "administrator"):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    timestamp = int(time.time())

    await app.db.execute(dhrid, f"INSERT INTO announcement(userid, title, content, announcement_type, timestamp, is_private, orderid, is_pinned) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(content))}', {announcement_type}, {timestamp}, {is_private}, {orderid}, {is_pinned})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    announcementid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], ml.ctr(request, "created_announcement", var = {"id": announcementid}))

    author = await GetUserInfo(request, userid = au["userid"])
    await notification_to_everyone(request, "new_announcement", ml.spl("new_announcement_with_title", var = {"title": title}),     discord_embed = {"title": title, "description": content, "footer": {"text": author["name"], "icon_url": author["avatar"]}}, only_to_members=is_private)

    def setvar(msg):
        return msg.replace("{mention}", f"<@{au['discordid']}>").replace("{name}", au['name']).replace("{userid}", str(au['userid'])).replace("{uid}", str(au['uid'])).replace("{avatar}", validateUrl(au['avatar'])).replace("{id}", str(announcementid)).replace("{title}", title).replace("{content}", content).replace("{type}", tatype["name"])

    for meta in app.config.announcement_forwarding:
        meta = Dict2Obj(meta)
        if meta.is_private is not None and int(meta.is_private) != is_private:
            continue
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

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

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator","manage_announcements"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    au["roles"]

    await app.db.execute(dhrid, f"SELECT title, content, announcement_type, is_private, orderid, is_pinned FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    (title, content, announcement_type, is_private, orderid, is_pinned) = t[0]
    content = decompress(content)

    # check if announcement original type can be modified by current staff
    tatype = None
    for atype in app.config.announcement_types:
        if atype["id"] == announcement_type:
            tatype = atype
            break
    if tatype is not None:
        ok = False
        for role in au["roles"]:
            if role in tatype["staff_role_ids"]:
                ok = True
        if not ok and not checkPerm(app, au["roles"], "administrator"):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    data = await request.json()
    try:
        if "title" in data.keys():
            title = data["title"]
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "content" in data.keys():
            content = data["content"]
            if len(data["content"]) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "content", "limit": "2,000"}, force_lang = au["language"])}
        if "type" in data.keys():
            announcement_type = int(data["type"])
            if abs(announcement_type) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "type", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_private" in data.keys():
            is_private = int(bool(data["is_private"]))
        if "orderid" in data.keys():
            orderid = int(data["orderid"])
            if abs(orderid) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_pinned" in data.keys():
            is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    # check if announcement new type can be modified by current staff
    tatype = None
    for atype in app.config.announcement_types:
        if atype["id"] == announcement_type:
            tatype = atype
            break
    if tatype is None:
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_announcement_type", force_lang = au["language"])}
    ok = False
    for role in au["roles"]:
        if role in tatype["staff_role_ids"]:
            ok = True
    if not ok and not checkPerm(app, au["roles"], "administrator"):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE announcement SET title = '{convertQuotation(title)}', content = '{convertQuotation(compress(content))}', announcement_type = {announcement_type}, is_private = {is_private}, orderid = {orderid}, is_pinned = {is_pinned} WHERE announcementid = {announcementid}")
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
    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_announcements"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT announcement_type FROM announcement WHERE announcementid = {announcementid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "announcement_not_found", force_lang = au["language"])}
    announcement_type = t[0][0]

    # check if announcement type can be deleted by current staff
    tatype = None
    for atype in app.config.announcement_types:
        if atype["id"] == announcement_type:
            tatype = atype
            break
    if tatype is not None:
        ok = False
        for role in au["roles"]:
            if role in tatype["staff_role_ids"]:
                ok = True
        if not ok and not checkPerm(app, au["roles"], "administrator"):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM announcement WHERE announcementid = {announcementid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_announcement", var = {"id": announcementid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)
