# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *

DIVISION_POINTS = {}
DIVISION_NAME = {}
for division in config.divisions:
    DIVISION_POINTS[division["id"]] = division["points"]
    DIVISION_NAME[division["id"]] = division["name"]

# Basic info
@app.get(f"/division/list")
async def get_division_list():
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    return config.divisions

# Get division info
@app.get(f"/division")
async def get_division(request: Request, response: Response, authorization: str = Header(None)):
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /division', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await ActivityUpdate(dhrid, au["uid"], f"divisions")
    
    stats = []
    for division in config.divisions:
        division_id = division["id"]
        division_role_id = division["role_id"]
        division_point = division["points"]
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE roles LIKE '%,{division_role_id},%'")
        usertot = await aiosql.fetchone(dhrid)
        usertot = usertot[0]
        usertot = 0 if usertot is None else int(usertot)
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM division WHERE status = 1 AND logid >= 0 AND divisionid = {division_id}")
        pointtot = await aiosql.fetchone(dhrid)
        pointtot = pointtot[0]
        pointtot = 0 if pointtot is None else int(pointtot)
        pointtot *= division_point
        stats.append({"divisionid": division_id, "name": division['name'], "total_drivers": usertot, "total_points": pointtot})
    
    return stats

# Get division info
@app.get(f"/dlog/{{logid}}/division")
async def get_dlog_division(request: Request, response: Response, logid: int, authorization: str = Header(None)):
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /dlog/division', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    roles = au["roles"]
        
    await aiosql.execute(dhrid, f"SELECT divisionid, userid, request_timestamp, status, update_timestamp, update_staff_userid, message FROM division WHERE logid = {logid} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "division_not_validated", force_lang = au["language"])}
        duserid = t[0][0]
        if duserid != userid:
            response.status_code = 404
            return {"error": ml.tr(request, "division_not_validated", force_lang = au["language"])}
        else:
            return {"divisionid": None, "status": None}
    tt = t[0]
    divisionid = tt[0]
    duserid = tt[1]
    request_timestamp = tt[2]
    status = tt[3]
    update_timestamp = tt[4]
    update_staff_userid = tt[5]
    message = decompress(tt[6])

    isStaff = checkPerm(roles, ["admin", "division"])

    if not isStaff:
        if userid != duserid and status != 1:
            response.status_code = 404
            return {"error": ml.tr(request, "division_not_validated", force_lang = au["language"])}

    if userid == duserid or isStaff: # delivery driver check division / division staff check delivery
        return {"divisionid": divisionid, "status": status, "request_timestamp": request_timestamp, "update_timestamp": update_timestamp, "update_message": message, "update_staff": await GetUserInfo(dhrid, request, userid = update_staff_userid)}
    else:
        return {"divisionid": divisionid, "status": status}

# Self-operation
@app.post(f"/dlog/{{logid}}/division/{{divisionid}}")
async def post_dlog_division(request: Request, response: Response, logid: int, divisionid: int, authorization: str = Header(None)):
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /dlog/division', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]
        
    await aiosql.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    luserid = t[0][0]
    if userid != luserid:
        response.status_code = 403
        return {"error": ml.tr(request, "only_delivery_submitter_can_request_division_validation", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        status = t[0][0]
        if status == 0:
            return {"error": ml.tr(request, "division_already_requested", force_lang = au["language"])}
        elif status == 1:
            return {"error": ml.tr(request, "division_already_validated", force_lang = au["language"])}
        elif status == 2:
            return {"error": ml.tr(request, "division_already_denied", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT roles FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    roles = str2list(t[0][0])
    joined_divisions = []
    for role in roles:
        if role in DIVISION_ROLES:
            for division in config.divisions:
                try:
                    if division["role_id"] == role:
                        joined_divisions.append(division["id"])
                except:
                    pass
    if not checkPerm(roles, "admin") and not divisionid in joined_divisions:
        response.status_code = 403
        return {"error": ml.tr(request, "not_division_driver", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    await aiosql.commit(dhrid)
    
    language = await GetUserLanguage(dhrid, uid)
    await notification(dhrid, "division", uid, ml.tr(request, "division_validation_request_submitted", var = {"logid": logid}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_submitted_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": DIVISION_NAME[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
    await aiosql.execute(dhrid, f"SELECT userid, name, avatar FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    tt = t[0]
    msg = f"**UID**: {uid}\n**User ID**: {tt[0]}\n**Name**: {tt[1]}\n**Discord**: <@{discordid}> (`{discordid}`)\n\n"
    msg += f"**Delivery ID**: [{logid}]({dlglink})\n**Division**: {DIVISION_NAME[divisionid]}"
    avatar = tt[2]

    if config.webhook_division != "":
        try:
            if avatar.startswith("a_"):
                author = {"name": tt[1], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif"}
            else:
                author = {"name": tt[1], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png"}
                
            r = await arequests.post(config.webhook_division, data=json.dumps({"content": config.webhook_division_message,"embeds": [{"title": f"New Division Validation Request for Delivery #{logid}", "description": msg, "author": author, "footer": {"text": f"Delivery ID: {logid} "}, "timestamp": str(datetime.now()), "color": config.int_color}]}), headers = {"Content-Type": "application/json"})
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()
        
    return Response(status_code=204)

@app.patch(f"/dlog/{{logid}}/division/{{divisionid}}")
async def patch_dlog_division(request: Request, response: Response, logid: int, divisionid: int, authorization: str = Header(None)):
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /dlog/division', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    data = await request.json()
    try:
        message = str(data["message"])
        status = int(data["status"])
        if len(data["message"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "200"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT divisionid, status, userid FROM division WHERE logid = {logid} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "division_validation_not_found", force_lang = au["language"])}
    if not divisionid in DIVISION_NAME.keys():
        divisionid = t[0][0]
    userid = t[0][2]
        
    await aiosql.execute(dhrid, f"UPDATE division SET divisionid = {divisionid}, status = {status}, update_staff_userid = {au['userid']}, update_timestamp = {int(time.time())}, message = '{compress(message)}' WHERE logid = {logid}")
    await aiosql.commit(dhrid)

    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    await AuditLog(dhrid, au["uid"], ml.ctr("updated_division_validation", var = {"logid": logid, "status": STATUS[status]}))

    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]

    language = await GetUserLanguage(dhrid, uid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[status]

    await notification(dhrid, "division", uid, ml.tr(request, "division_validation_request_status_updated", var = {"logid": logid, "status": statustxtTR.lower()}, force_lang = await GetUserLanguage(dhrid, uid)), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_status_updated_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": DIVISION_NAME[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})

    return Response(status_code=204)

@app.get(f"/division/list/pending")
async def get_division_list_pending(request: Request, response: Response, authorization: str = Header(None), \
        divisionid: Optional[int] = None, page: Optional[int] = 1, page_size: Optional[int] = 10):
    if "division" not in config.enabled_plugins:
        return Response({"error": "Not Found"}, 404)

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /division/list/pending', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
        
    limit = ""
    if divisionid is not None:
        limit = f"AND divisionid = {divisionid}"
    await aiosql.execute(dhrid, f"SELECT logid, userid, divisionid FROM division WHERE status = 0 {limit} AND logid >= 0 \
        LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"logid": tt[0], "divisionid": tt[2], "user": await GetUserInfo(dhrid, request, userid = tt[1])})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM division WHERE status = 0 {limit} AND logid >= 0")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}