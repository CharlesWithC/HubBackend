# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import random
import string
import time
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *


@app.get(f"/{config.abbr}/downloads/list")
async def get_downloads_list(request: Request, response: Response, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "orderid", order: Optional[int] = "asc", \
        query: Optional[str] = "", creator_userid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /downloads/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffau = await auth(dhrid, authorization, request, allow_application_token = True, required_permission=["admin", "downloads"])
    isstaff = False
    if not staffau["error"]:
        isstaff = True
    await ActivityUpdate(dhrid, au["uid"], "downloads")
        
    limit = ""
    if query != "":
        query = convertQuotation(query).lower()
        limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "
    if creator_userid != -1:
        limit += f"AND userid = {creator_userid} "

    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if not order_by in ["orderid", "downloadsid", "title", "click_count"]:
        order_by = "orderid"
        order = "asc"
    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()    

    await aiosql.execute(dhrid, f"SELECT downloadsid, userid, title, description, link, click_count, orderid FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        if not isstaff:
            ret.append({"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(dhrid, request, userid = tt[1]), "orderid": tt[6], "click_count": tt[5]})
        else:
            ret.append({"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(dhrid, request, userid = tt[1]), "link": tt[4], "orderid": tt[6], "click_count": tt[5]})
        
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.get(f"/{config.abbr}/downloads/{{downloadsid}}")
async def get_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /downloads', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffau = await auth(dhrid, authorization, request, allow_application_token = True, required_permission=["admin", "downloads"])
    isstaff = False
    if not staffau["error"]:
        isstaff = True
    await ActivityUpdate(dhrid, au["uid"], "downloads")

    if downloadsid <= 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT downloadsid, userid, title, description, link, click_count, orderid FROM downloads WHERE downloadsid = {downloadsid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    tt = t[0]

    secret = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    await aiosql.execute(dhrid, f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO downloads_templink VALUES ({downloadsid}, '{secret}', {int(time.time()+300)})")
    await aiosql.commit(dhrid)

    if not isstaff:
        return {"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(dhrid, request, userid = tt[1]), "secret": secret, "orderid": tt[6], "click_count": tt[5]}
    else:
        return {"downloadsid": tt[0], "title": tt[2], "description": decompress(tt[3]), "creator": await GetUserInfo(dhrid, request, userid = tt[1]), "link": tt[4], "secret": secret, "orderid": tt[6], "click_count": tt[5]}

@app.get(f"/{config.abbr}/downloads/redirect/{{secret}}")
async def get_downloads_redirect(request: Request, response: Response, secret: str):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /downloads/redirect', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    await aiosql.execute(dhrid, f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    await aiosql.commit(dhrid)

    secret = convertQuotation(secret)

    await aiosql.execute(dhrid, f"SELECT downloadsid FROM downloads_templink WHERE secret = '{secret}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found")}
    downloadsid = t[0][0]

    await aiosql.execute(dhrid, f"SELECT link FROM downloads WHERE downloadsid = {downloadsid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found")}
    link = t[0][0]

    await aiosql.execute(dhrid, f"UPDATE downloads SET click_count = click_count + 1 WHERE downloadsid = {downloadsid}")
    await aiosql.commit(dhrid)

    return RedirectResponse(url=link, status_code=302)

@app.post(f"/{config.abbr}/downloads")
async def post_downloads(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = compress(data["description"])
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        link = convertQuotation(data["link"])
        if len(data["link"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
        orderid = int(data["orderid"])
        if orderid > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:        
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if not isurl(link):
        response.status_code = 400
        return {"error": ml.tr(request, "downloads_invalid_link", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"INSERT INTO downloads(userid, title, description, link, orderid, click_count) VALUES ({adminid}, '{title}', '{description}', '{link}', {orderid}, 0)")
    await aiosql.commit(dhrid)
    await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    downloadsid = (await aiosql.fetchone(dhrid))[0]
    await AuditLog(dhrid, adminid, f"Created downloadable item `#{downloadsid}`")

    return {"downloadsid": downloadsid}

@app.patch(f"/{config.abbr}/downloads/{{downloadsid}}")
async def patch_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    if downloadsid <= 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid FROM downloads WHERE downloadsid = {downloadsid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = compress(data["description"])
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        link = convertQuotation(data["link"])
        if len(data["link"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
        orderid = int(data["orderid"])
        if orderid > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:        
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if not isurl(link):
        response.status_code = 400
        return {"error": ml.tr(request, "downloads_invalid_link", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE downloads SET title = '{title}', description = '{description}', link = '{link}', orderid = {orderid} WHERE downloadsid = {downloadsid}")
    await AuditLog(dhrid, adminid, f"Updated downloadable item `#{downloadsid}`")
    await aiosql.commit(dhrid)

    return Response(status_code=204)
    
@app.delete(f"/{config.abbr}/downloads/{{downloadsid}}")
async def delete_downloads(request: Request, response: Response, downloadsid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    if int(downloadsid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM downloads WHERE downloadsid = {downloadsid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM downloads WHERE downloadsid = {downloadsid}")
    await AuditLog(dhrid, adminid, f"Deleted downloadable item `#{downloadsid}`")
    await aiosql.commit(dhrid)

    return Response(status_code=204)