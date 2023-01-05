# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from discord import Webhook, Embed
from datetime import datetime
from aiohttp import ClientSession
import json, time, requests
import traceback

from app import app, config
from db import aiosql
from functions import *
import multilang as ml

divisions = config.divisions
divisionsGET = divisions
to_delete = []
for i in range(len(divisions)):
    try:
        divisions[i]["id"] = int(divisions[i]["id"])
        divisionsGET[i]["id"] = str(divisions[i]["id"])
    except:
        to_delete.append(i)
for i in to_delete[::-1]:
    divisions.remove(i)
    divisionsGET.remove(i)
    
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
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /division', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]
        
    if logid != -1:
        await aiosql.execute(dhrid, f"SELECT divisionid, userid, request_timestamp, status, update_timestamp, update_staff_userid, message FROM division WHERE logid = {logid} AND logid >= 0")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            await aiosql.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
            t = await aiosql.fetchall(dhrid)
            if len(t) == 0:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated", force_lang = au["language"])}
            duserid = t[0][0]
            if duserid != userid:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated", force_lang = au["language"])}
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
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated", force_lang = au["language"])}

        if userid == duserid or ok: # delivery driver check division / division staff check delivery
            return {"error": False, "response": {"divisionid": str(divisionid), "status": str(status), \
                "request_timestamp": str(request_timestamp), "update_timestamp": str(update_timestamp), \
                    "update_staff": await getUserInfo(dhrid, userid = update_staff_userid), "update_message": message}}
        else:
            return {"error": False, "response": {"divisionid": str(divisionid), "status": str(status)}}

    await activityUpdate(dhrid, au["discordid"], f"divisions")
    
    stats = []
    for division in divisions:
        division_id = division["id"]
        division_role_id = division["role_id"]
        division_point = int(division["point"])
        tstats = []
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE roles LIKE '%,{division_role_id},%'")
        usertot = await aiosql.fetchone(dhrid)
        usertot = usertot[0]
        usertot = 0 if usertot is None else int(usertot)
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM division WHERE status = 1 AND logid >= 0 AND divisionid = {division_id}")
        pointtot = await aiosql.fetchone(dhrid)
        pointtot = pointtot[0]
        pointtot = 0 if pointtot is None else int(pointtot)
        pointtot *= division_point
        stats.append({"divisionid": str(division['id']), "name": division['name'], "total_drivers": str(usertot), "total_points": str(pointtot)})
    
    return {"error": False, "response": stats}   

# Self-operation
@app.post(f"/{config.abbr}/division")
async def postDivision(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1):
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /division', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
        
    form = await request.form()
    try:
        logid = int(form["logid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    luserid = t[0][0]
    if userid != luserid:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "Forbidden", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        status = t[0][0]
        if status == 0:
            return {"error": True, "descriptor": ml.tr(request, "division_already_requested", force_lang = au["language"])}
        elif status == 1:
            return {"error": True, "descriptor": ml.tr(request, "division_already_validated", force_lang = au["language"])}
        elif status == 2:
            return {"error": True, "descriptor": ml.tr(request, "division_already_denied", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT roles FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
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
        return {"error": True, "descriptor": ml.tr(request, "not_division_driver", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    await aiosql.commit(dhrid)
    
    language = await GetUserLanguage(dhrid, discordid)
    await notification(dhrid, "division", discordid, ml.tr(request, "division_validation_request_submitted", var = {"logid": logid}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_submitted_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": divisiontxt[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
    await aiosql.execute(dhrid, f"SELECT userid, name, avatar FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
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
            traceback.print_exc()
        
    return {"error": False}

@app.get(f"/{config.abbr}/division/list/pending")
async def getDivisionsPending(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1,\
        page: Optional[int] = 1, page_size: Optional[int] = 10):
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /division/list/pending', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    if page <= 0:
        page = 1
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
        
    limit = ""
    if divisionid != -1:
        limit = f"AND divisionid = {divisionid}"
    await aiosql.execute(dhrid, f"SELECT logid, userid, divisionid FROM division WHERE status = 0 {limit} AND logid >= 0 \
        LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"logid": str(tt[0]), "divisionid": str(tt[2]), "user": await getUserInfo(dhrid, userid = tt[1])})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM division WHERE status = 0 {limit} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.patch(f"/{config.abbr}/division")
async def patchDivision(request: Request, response: Response, authorization: str = Header(None), divisionid: Optional[int] = -1):
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /division', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    form = await request.form()
    try:
        logid = int(form["logid"])
        message = str(form["message"])
        status = int(form["status"])
        if len(form["message"]) > 200:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "200"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT divisionid, status, userid FROM division WHERE logid = {logid} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "division_validation_not_found", force_lang = au["language"])}
    if not divisionid in divisiontxt.keys():
        divisionid = t[0][0]
    userid = t[0][2]
        
    await aiosql.execute(dhrid, f"UPDATE division SET divisionid = {divisionid}, status = {status}, update_staff_userid = {adminid}, update_timestamp = {int(time.time())}, message = '{compress(message)}' WHERE logid = {logid}")
    await aiosql.commit(dhrid)

    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    await AuditLog(dhrid, adminid, f"Updated division validation status of delivery `#{logid}` to `{STATUS[status]}`")

    discordid = (await getUserInfo(dhrid, userid = userid))["discordid"]
    adiscordid = (await getUserInfo(dhrid, userid = adminid))["discordid"]

    language = await GetUserLanguage(dhrid, discordid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[int(status)]

    await notification(dhrid, "division", discordid, ml.tr(request, "division_validation_request_status_updated", var = {"logid": logid, "status": statustxtTR.lower()}, force_lang = await GetUserLanguage(dhrid, discordid, "en")), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_status_updated_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": divisiontxt[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})

    return {"error": False}