# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import random
import string
import time
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_downloadsid: Optional[int] = None, \
        created_after: Optional[int] = None, created_before: Optional[int] = None, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", \
        title: Optional[str] = "", created_by: Optional[int] = None,
        min_click: Optional[int] = None, max_click: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /downloads/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    isstaff = checkPerm(app, au["roles"], ["administrator", "manage_downloads"])
    await ActivityUpdate(request, au["uid"], "downloads")

    limit = ""
    if title != "":
        title = convertQuotation(title).lower()
        limit += f"AND LOWER(title) LIKE '%{title}%' "
    if created_by is not None:
        limit += f"AND userid = {created_by} "
    if created_after is not None:
        limit += f"AND timestamp >= {created_after} "
    if created_before is not None:
        limit += f"AND timestamp <= {created_before} "
    if min_click is not None:
        limit += f"AND click_count >= {min_click} "
    if max_click is not None:
        limit += f"AND click_count <= {max_click} "

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if order_by not in ["orderid", "downloadsid", "title", "timestamp", "click_count"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT downloadsid FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, downloadsid DESC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_downloadsid is not None:
        for tt in t:
            if tt[0] == after_downloadsid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT downloadsid, userid, title, description, link, click_count, orderid, is_pinned, timestamp FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, downloadsid DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        if not isstaff:
            ret.append({"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(request, userid = tt[1]), "orderid": tt[6], "is_pinned": TF[tt[7]], "timestamp": tt[8], "click_count": tt[5]})
        else:
            ret.append({"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(request, userid = tt[1]), "link": tt[4], "orderid": tt[6], "is_pinned": TF[tt[7]], "timestamp": tt[8], "click_count": tt[5]})

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /downloads', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    isstaff = checkPerm(app, au["roles"], ["administrator", "manage_downloads"])
    await ActivityUpdate(request, au["uid"], "downloads")

    await app.db.execute(dhrid, f"SELECT downloadsid, userid, title, description, link, click_count, orderid, is_pinned, timestamp FROM downloads WHERE downloadsid = {downloadsid} AND downloadsid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    tt = t[0]

    secret = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    await app.db.execute(dhrid, f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    await app.db.execute(dhrid, f"INSERT INTO downloads_templink VALUES ({downloadsid}, '{secret}', {int(time.time()+300)})")
    await app.db.commit(dhrid)

    if not isstaff:
        return {"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(request, userid = tt[1]), "secret": secret, "orderid": tt[6], "is_pinned": TF[tt[7]], "timestamp": tt[8], "click_count": tt[5]}
    else:
        return {"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(request, userid = tt[1]), "link": tt[4], "secret": secret, "orderid": tt[6], "is_pinned": TF[tt[7]], "timestamp": tt[8], "click_count": tt[5]}

async def get_redirect(request: Request, response: Response, secret: str):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /downloads/redirect', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    await app.db.execute(dhrid, f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    await app.db.commit(dhrid)

    secret = convertQuotation(secret)

    await app.db.execute(dhrid, f"SELECT downloadsid FROM downloads_templink WHERE secret = '{secret}'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found")}
    downloadsid = t[0][0]

    await app.db.execute(dhrid, f"SELECT link FROM downloads WHERE downloadsid = {downloadsid} AND downloadsid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found")}
    link = t[0][0]

    await app.db.execute(dhrid, f"UPDATE downloads SET click_count = click_count + 1 WHERE downloadsid = {downloadsid}")
    await app.db.commit(dhrid)

    return RedirectResponse(url=link, status_code=302)

async def post_downloads(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = data["title"]
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = data["description"]
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        link = data["link"]
        if len(data["link"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
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

    if not isurl(link):
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_link", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO downloads(userid, title, description, link, orderid, is_pinned, timestamp, click_count) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(description))}', '{link}', {orderid}, {is_pinned}, {int(time.time())}, 0)")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    downloadsid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], "downloads", ml.ctr(request, "created_downloads", var = {"id": downloadsid}))
    await app.db.commit(dhrid)

    await notification_to_everyone(request, "new_downloads", ml.spl("new_downloadable_item_with_title", var = {"title": title}), discord_embed = {"title": title, "description": description, "fields": [{"name": "‎ ", "value": ml.spl("download_link", var = {"link": link}), "inline": True}], "footer": {"text": ml.spl("new_downloadable_item"), "icon_url": app.config.logo_url}}, only_to_members=True)

    def setvar(msg):
        return msg.replace("{mention}", f"<@{au['discordid']}>").replace("{name}", au['name']).replace("{userid}", str(au['userid'])).replace("{uid}", str(au['uid'])).replace("{avatar}", validateUrl(au['avatar'])).replace("{id}", str(downloadsid)).replace("{title}", title).replace("{description}", description).replace("{link}", validateUrl(link))

    for meta in app.config.downloads_forwarding:
        meta = Dict2Obj(meta)
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

    return {"downloadsid": downloadsid}

async def patch_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, link, orderid, is_pinned FROM downloads WHERE downloadsid = {downloadsid} AND downloadsid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    (title, description, link, orderid, is_pinned) = t[0]
    description = decompress(description)

    data = await request.json()
    try:
        if "title" in data.keys():
            title = data["title"]
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "description" in data.keys():
            description = data["description"]
            if len(data["description"]) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        if "link" in data.keys():
            link = data["link"]
            if len(data["link"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
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

    if not isurl(link):
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_link", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE downloads SET title = '{convertQuotation(title)}', description = '{convertQuotation(compress(description))}', link = '{convertQuotation(link)}', orderid = {orderid}, is_pinned = {is_pinned} WHERE downloadsid = {downloadsid}")
    await AuditLog(request, au["uid"], "downloads", ml.ctr(request, "updated_downloads", var = {"id": downloadsid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT * FROM downloads WHERE downloadsid = {downloadsid} AND downloadsid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE downloads SET downloadsid = -downloadsid WHERE downloadsid = {downloadsid}")
    await AuditLog(request, au["uid"], "downloads", ml.ctr(request, "deleted_downloads", var = {"id": downloadsid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)
