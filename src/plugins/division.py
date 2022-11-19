# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from discord import Webhook, Embed
from datetime import datetime
from aiohttp import ClientSession
import json, time, requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

divisions = config.divisions
divisionsGET = divisions
for i in range(len(divisions)):
    try:
        divisions[i]["id"] = int(divisions[i]["id"])
        divisionsGET[i]["id"] = str(divisions[i]["id"])
    except:
        pass
    
divisionroles = []
divisiontxt = {}
for division in divisions:
    try:
        divisionroles.append(int(division["role_id"]))
        divisiontxt[int(division["id"])] = division["name"]
    except:
        pass

DIVISIONPNT = {}
for division in divisions:
    try:
        DIVISIONPNT[int(division["id"])] = int(division["point"])
    except:
        pass

# Basic info
@app.get(f"/{config.abbr}/division/list")
async def getDivisions(request: Request, response: Response):
    return {"error": False, "response": divisionsGET}

# Get division info
@app.get(f"/{config.abbr}/division")
async def getDivision(request: Request, response: Response, authorization: str = Header(None), logid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /division', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]
        
    conn = newconn()
    cur = conn.cursor()

    if logid != -1:
        cur.execute(f"SELECT divisionid, userid, request_timestamp, status, update_timestamp, update_staff_userid, message FROM division WHERE logid = {logid} AND logid >= 0")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
            t = cur.fetchall()
            if len(t) == 0:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}
            duserid = t[0][0]
            if duserid != userid:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}
            else:
                return {"error": False, "response": {"divisionid": "-1", "status": "-1"}}
        tt = t[0]
        divisionid = tt[0]
        duserid = tt[1]
        request_timestamp = tt[2]
        status = tt[3]
        update_timestamp = tt[4]
        update_staff_userid = tt[5]
        message = decompress(tt[6])

        ok = False
        for i in roles:
            if int(i) in config.perms.admin or int(i) in config.perms.division:
                ok = True

        if not ok:
            if userid != duserid and status != 1:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}

        if userid == duserid or ok: # delivery driver check division / division staff check delivery
            return {"error": False, "response": {"divisionid": str(divisionid), "status": str(status), \
                "request_timestamp": str(request_timestamp), "update_timestamp": str(update_timestamp), \
                    "update_staff": getUserInfo(userid = update_staff_userid), "update_message": message}}
        else:
            return {"error": False, "response": {"divisionid": str(divisionid), "status": str(status)}}

    activityUpdate(au["discordid"], f"Viewing Divisions")
    
    stats = []
    for division in divisions:
        tstats = []
        cur.execute(f"SELECT userid FROM user WHERE roles LIKE '%,{division['role_id']},%'")
        t = cur.fetchall()
        userpnt = {}
        for tt in t:
            divisionpnt = 0
            cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {tt[0]} AND status = 1 AND logid >= 0 GROUP BY divisionid, userid")
            o = cur.fetchall()
            for oo in o:
                if o[0][0] in DIVISIONPNT.keys():
                    divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
            userpnt[tt[0]] = divisionpnt
        userpnt = dict(sorted(userpnt.items(), key=lambda item: item[1]))
        totalpnt = 0
        for uid in userpnt.keys():
            totalpnt += userpnt[uid]
            # tstats.append({"user": getUserInfo(userid = uid), "points": str(userpnt[uid])})
        stats.append({"divisionid": str(division['id']), "name": division['name'], "total_drivers": len(userpnt), "total_points": totalpnt})
    
    return {"error": False, "response": stats}   

# Self-operation
@app.post(f"/{config.abbr}/division")
async def postDivision(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'POST /division', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        logid = int(form["logid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form")}

    cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "delivery_log_not_found")}
    luserid = t[0][0]
    if userid != luserid:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    cur.execute(f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        status = t[0][0]
        if status == 0:
            return {"error": True, "descriptor": ml.tr(request, "division_already_requested")}
        elif status == 1:
            return {"error": True, "descriptor": ml.tr(request, "division_already_validated")}
        elif status == 2:
            return {"error": True, "descriptor": ml.tr(request, "division_already_denied")}
    
    cur.execute(f"SELECT roles FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    while "" in roles:
        roles.remove("")
    udivisions = []
    for role in roles:
        if int(role) in divisionroles:
            for division in divisions:
                try:
                    if int(division["role_id"]) == int(role):
                        udivisions.append(int(division["id"]))
                except:
                    pass
    if not divisionid in udivisions:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "not_division_driver")}
    
    cur.execute(f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    conn.commit()
    
    notification(f"Division Validation Request for Delivery `#{logid}` submitted.")

    dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
    cur.execute(f"SELECT userid, name, avatar FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    tt = t[0]
    msg = f"**User ID**: {tt[0]}\n**Name**: {tt[1]}\n**Discord**: <@{discordid}> (`{discordid}`)\n\n"
    msg += f"**Delivery ID**: [{logid}]({dlglink})\n**Division**: {divisiontxt[divisionid]}"
    avatar = tt[2]

    if config.webhook_division != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_division, session=session)

                embed = Embed(title = f"New Division Validation Request for Delivery #{logid}", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif")
                else:
                    embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png")
                embed.set_footer(text = f"Delivery ID: {logid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = config.webhook_division_message, embed = embed)
        except:
            import traceback
            traceback.print_exc()
        
    return {"error": False}

@app.get(f"/{config.abbr}/division/list/pending")
async def getDivisionsPending(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1,\
        page: Optional[int] = 1, page_size: Optional[int] = 10):
    rl = ratelimit(request, request.client.host, 'GET /division/list/pending', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = 401
        return au
        
    if page <= 0:
        page = 1
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
        
    conn = newconn()
    cur = conn.cursor()

    limit = ""
    if divisionid != -1:
        limit = f"AND divisionid = {divisionid}"
    cur.execute(f"SELECT logid, userid, divisionid FROM division WHERE status = 0 {limit} AND logid >= 0 \
        LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"logid": str(tt[0]), "divisionid": str(tt[2]), "user": getUserInfo(userid = tt[1])})
    
    cur.execute(f"SELECT COUNT(*) FROM division WHERE status = 0 {limit} AND logid >= 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.patch(f"/{config.abbr}/division")
async def patchDivision(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'PATCH /division', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        logid = int(form["logid"])
        message = str(form["message"])
        status = int(form["status"])
        if len(form["message"]) > 200:
            response.status_code = 413
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "200"})}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form")}
    
    cur.execute(f"SELECT divisionid, status, userid FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "division_validation_not_found")}
    if not divisionid in divisiontxt.keys():
        divisionid = t[0][0]
    userid = t[0][2]
        
    cur.execute(f"UPDATE division SET divisionid = {divisionid}, status = {status}, update_staff_userid = {adminid}, update_timestamp = {int(time.time())}, message = '{compress(message)}' WHERE logid = {logid}")
    conn.commit()

    STATUS = {0: "pending", 1: "validated", 2: "denied"}
    await AuditLog(adminid, f"Updated division validation status of delivery `#{logid}` to `{STATUS[status]}`")

    discordid = getUserInfo(userid = userid)["discordid"]
    adiscordid = getUserInfo(userid = adminid)["discordid"]

    STATUS = {0: "pending", 1: "accepted", 2: "rejected"}
    notification(discordid, f"Division Validation Request for Delivery `#{logid}` status updated to `{STATUS[status]}`")

    return {"error": False}