# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math
import requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.vtcprefix}/downloads")
async def getDownloads(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /downloads', 60, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
        
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT data FROM downloads")
    t = cur.fetchall()
    data = ""
    if len(t) > 0:
        data = b64d(t[0][0])
        
    return {"error": False, "response": data}

@app.patch(f"/{config.vtcprefix}/downloads")
async def patchDownloads(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /downloads', 60, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    data = b64e(form["data"])
    
    cur.execute(f"DELETE FROM downloads")
    cur.execute(f"INSERT INTO downloads VALUES ('{data}')")
    conn.commit()

    await AuditLog(adminid, "Updated downloads")

    return {"error": False}
