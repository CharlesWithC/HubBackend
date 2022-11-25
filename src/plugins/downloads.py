# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
import json, time, requests, random, string

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.abbr}/downloads")
async def getDownloads(request: Request, response: Response, authorization: str = Header(None), \
        downloadsid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /downloads', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffau = auth(authorization, request, allow_application_token = True, required_permission=["admin", "downloads"])
    isstaff = False
    if not staffau["error"]:
        isstaff = True
    activityUpdate(au["discordid"], "downloads")

    if downloadsid <= 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT downloadsid, userid, title, description, link, click_count, orderid FROM downloads WHERE downloadsid = {downloadsid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    tt = t[0]

    secret = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    cur.execute(f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    cur.execute(f"INSERT INTO downloads_templink VALUES ({downloadsid}, '{secret}', {int(time.time()+300)})")
    conn.commit()

    if not isstaff:
        return {"error": False, "response": {"downloads": {"downloadsid": str(tt[0]), "creator": getUserInfo(userid = tt[1]), "title": tt[2], "description": decompress(tt[3]), "secret": secret, "orderid": str(tt[6]), "click_count": str(tt[5])}}}
    else:
        return {"error": False, "response": {"downloads": {"downloadsid": str(tt[0]), "creator": getUserInfo(userid = tt[1]), "title": tt[2], "description": decompress(tt[3]), "link": tt[4], "secret": secret, "orderid": str(tt[6]), "click_count": str(tt[5])}}}

@app.get(f"/{config.abbr}/downloads/list")
async def getDownloadsList(request: Request, response: Response, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "orderid", order: Optional[int] = "asc", \
        title: Optional[str] = "", creator_userid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /downloads/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffau = auth(authorization, request, allow_application_token = True, required_permission=["admin", "downloads"])
    isstaff = False
    if not staffau["error"]:
        isstaff = True
    activityUpdate(au["discordid"], "downloads")
        
    limit = ""
    if title != "":
        title = convert_quotation(title).lower()
        limit += f"AND LOWER(title) LIKE '%{title[:200]}%' "
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

    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT downloadsid, userid, title, description, link, click_count, orderid FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        if not isstaff:
            ret.append({"downloadsid": str(tt[0]), "creator": getUserInfo(userid = tt[1]), "title": tt[2], "description": decompress(tt[3]), "orderid": str(tt[6]), "click_count": str(tt[5])})
        else:
            ret.append({"downloadsid": str(tt[0]), "creator": getUserInfo(userid = tt[1]), "title": tt[2], "description": decompress(tt[3]), "link": tt[4], "orderid": str(tt[6]), "click_count": str(tt[5])})
        
    cur.execute(f"SELECT COUNT(*) FROM downloads WHERE downloadsid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret[:page_size], "total_items": str(tot), \
        "total_pages": str(int(math.ceil(tot / page_size)))}}

# MUST BE AFTER /downloads/list or this will overwrite that
@app.get(f"/{config.abbr}/downloads/{{secret}}")
async def redirectDownloads(request: Request, response: Response, authorization: str = Header(None), \
        secret: Optional[str] = ""):
    rl = ratelimit(request, request.client.host, 'GET /downloads/redirect', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"DELETE FROM downloads_templink WHERE expire <= {int(time.time())}")
    conn.commit()

    secret = convert_quotation(secret)

    cur.execute(f"SELECT downloadsid FROM downloads_templink WHERE secret = '{secret}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    downloadsid = t[0][0]

    cur.execute(f"SELECT link FROM downloads WHERE downloadsid = {downloadsid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    link = t[0][0]

    cur.execute(f"UPDATE downloads SET click_count = click_count + 1 WHERE downloadsid = {downloadsid}")
    conn.commit()

    return RedirectResponse(url=link, status_code=302)

@app.post(f"/{config.abbr}/downloads")
async def postDownloads(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'POST /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        if len(form["title"]) > 200:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = compress(form["description"])
        if len(form["description"]) > 2000:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        link = convert_quotation(form["link"])
        if len(form["link"]) > 200:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
        orderid = int(form["orderid"])
    except:        
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if not isurl(link):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "downloads_invalid_link", force_lang = au["language"])}
    
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtdownloadsid'")
    t = cur.fetchall()
    nxtdownloadsid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {nxtdownloadsid+1} WHERE skey = 'nxtdownloadsid'")
    cur.execute(f"INSERT INTO downloads VALUES ({nxtdownloadsid}, {adminid}, '{title}', '{description}', '{link}', {orderid}, 0)")
    await AuditLog(adminid, f"Created downloadable item `#{nxtdownloadsid}`")
    conn.commit()

    return {"error": False, "response": {"downloadsid": str(nxtdownloadsid)}}

@app.patch(f"/{config.abbr}/downloads")
async def patchDownloads(request: Request, response: Response, authorization: str = Header(None), \
        downloadsid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'PATCH /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    if downloadsid <= 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT userid FROM downloads WHERE downloadsid = {downloadsid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        if len(form["title"]) > 200:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = compress(form["description"])
        if len(form["description"]) > 2000:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        link = convert_quotation(form["link"])
        if len(form["link"]) > 200:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "200"}, force_lang = au["language"])}
        orderid = int(form["orderid"])
    except:        
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if not isurl(link):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "downloads_invalid_link", force_lang = au["language"])}
    
    cur.execute(f"UPDATE downloads SET title = '{title}', description = '{description}', link = '{link}', orderid = {orderid} WHERE downloadsid = {downloadsid}")
    await AuditLog(adminid, f"Updated downloadable item `#{downloadsid}`")
    conn.commit()

    return {"error": False}
    
@app.delete(f"/{config.abbr}/downloads")
async def deleteDownloads(request: Request, response: Response, authorization: str = Header(None), \
        downloadsid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /downloads', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "downloads"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    if int(downloadsid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}

    cur.execute(f"SELECT * FROM downloads WHERE downloadsid = {downloadsid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "downloads_not_found", force_lang = au["language"])}
    
    cur.execute(f"DELETE FROM downloads WHERE downloadsid = {downloadsid}")
    await AuditLog(adminid, f"Deleted downloadable item `#{downloadsid}`")
    conn.commit()

    return {"error": False}