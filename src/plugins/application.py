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
from app import app, config
from db import aiosql
from functions import *

# Basic Info
@app.get(f"/{config.abbr}/application/types")
async def get_application_types():
    return config.application_types

@app.get(f"/{config.abbr}/application/positions")
async def get_application_positions(request: Request):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return []
    else:
        ret = []
        for tt in t[0][0].split(","):
            tt = b64d(tt).strip(" ")
            if tt != "":
                ret.append(tt)
        return ret

@app.patch(f"/{config.abbr}/application/positions")
async def post_application_positions(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /application/positions', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "update_application_positions"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffid = au["userid"]

    data = await request.json()
    try:
        if type(data["positions"]) != list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    positions = []
    for position in data["positions"]:
        position = position.strip()
        if position != "":
            positions.append(position)
    positions_str = ", ".join(positions)
    positions = [b64e(x) for x in positions]
    positions = ",".join([b64e(x) for x in data["positions"]])

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO settings VALUES (0, 'applicationpositions', '{positions}')")
    else:
        await aiosql.execute(dhrid, f"UPDATE settings SET sval = '{positions}' WHERE skey = 'applicationpositions'")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, staffid, ml.ctr("updated_application_positions", var = {"positions": positions_str}))

    return Response(status_code=204)

# Get Application
@app.get(f"/{config.abbr}/application/list")
async def get_application_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, application_type: Optional[int] = 0, \
        all_user: Optional[bool] = False, status: Optional[int] = None, order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /application/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
        
    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]
    await ActivityUpdate(dhrid, au["uid"], f"applications")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    t = None
    tot = 0
    if all_user == False:
        limit = ""
        if application_type != 0:
            limit = f" AND application_type = {application_type} "

        if status is not None and status in [0,1,2]:
            limit += f" AND status = {status} "

        await aiosql.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application WHERE uid = {uid} {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = await aiosql.fetchall(dhrid)
        
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application WHERE uid = {uid} {limit}")
        p = await aiosql.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]
    else:
        limit = ""
        if not checkPerm(roles, "admin"):
            allowed_application_types = []
            for tt in config.application_types:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        allowed_application_types.append(tt["id"])
                        break

            if len(allowed_application_types) == 0:
                response.status_code = 403
                return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}
        
            if application_type == 0: # show all type
                limit = " WHERE ("
                for tt in allowed_application_types:
                    limit += f"application_type = {tt} OR "
                limit = limit[:-3]
                limit += ")"
            else:
                limit = f" WHERE application_type = {application_type} "
        
        if status is not None and status in [0,1,2]:
            if not "WHERE" in limit:
                limit = f" WHERE status = {status} "
            else:
                limit += f" AND status = {status} "

        await aiosql.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = await aiosql.fetchall(dhrid)
        
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application {limit}")
        p = await aiosql.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]

    ret = []
    for tt in t:
        ret.append({"applicationid": tt[0], "creator": await GetUserInfo(dhrid, request, uid = tt[2]), "application_type": tt[1], "status": tt[4], "submit_timestamp": tt[3], "update_timestamp": tt[5], "last_update_staff": await GetUserInfo(dhrid, request, userid = tt[6])})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.get(f"/{config.abbr}/application/{{applicationid}}")
async def get_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /application', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}

    application_type = t[0][1]
    
    if not checkPerm(roles, "admin") and uid != t[0][2]:
        ok = False
        for tt in config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

    return {"applicationid": t[0][0], "creator": await GetUserInfo(dhrid, request, uid = t[0][2]), "application_type": t[0][1], "application": json.loads(decompress(t[0][3])), "status": t[0][4], "submit_timestamp": t[0][5], "update_timestamp": t[0][7], "last_update_staff": await GetUserInfo(dhrid, request, userid = t[0][6])}

# Self-operation
@app.post(f"/{config.abbr}/application")
async def post_application(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /application', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    data = await request.json()
    try:
        application_type = int(data["application_type"])
        application = data["application"]
        if type(data["application"]) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    application_type_text = ""
    applicantrole = 0
    discord_message_content = ""
    webhookurl = ""
    note = ""
    for o in config.application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            applicantrole = o["discord_role_id"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
            note = o["note"]
    if application_type_text == "":
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if note == "driver":
        for r in config.perms.driver:
            if r in roles:
                response.status_code = 409
                return {"error": ml.tr(request, "drivers_not_allowed_to_create_driver_application", force_lang = au["language"])}
        await aiosql.execute(dhrid, f"SELECT * FROM application WHERE application_type = 1 AND uid = {uid} AND status = 0")
        p = await aiosql.fetchall(dhrid)
        if len(p) > 0:
            response.status_code = 409
            return {"error": ml.tr(request, "already_driver_application", force_lang = au["language"])}

    if note == "division" and not checkPerm(roles, "admin"):
        ok = False
        for r in config.perms.driver:
            if r in roles:
                ok = True
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "must_be_driver_to_submit_division_application", force_lang = au["language"])}        

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE uid = {uid} AND submit_timestamp >= {int(time.time()) - 7200}")
    p = await aiosql.fetchall(dhrid)
    if len(p) > 0:
        response.status_code = 429
        return {"error": ml.tr(request, "no_multiple_application_2h", force_lang = au["language"])}

    if userid == -1 and application_type == 3:
        response.status_code = 403
        return {"error": ml.tr(request, "must_be_member_to_submit_loa_application", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid, discordid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if t[0][2] is None and "email" in config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "email"}, force_lang = au["language"])}
    if t[0][6] is None and ("discord" in config.required_connections or config.must_join_guild):
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Discord"}, force_lang = au["language"])}
    if t[0][4] is None and "steam" in config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Steam"}, force_lang = au["language"])}
    if t[0][3] is None and "truckersmp" in config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "TruckersMP"}, force_lang = au["language"])}
    userid = t[0][5]

    if discordid is not None and config.must_join_guild and config.discord_bot_token != "":
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
        except:
            traceback.print_exc()
            response.status_code = 428
            return {"error": ml.tr(request, "user_in_guild_check_failed")}
        if r.status_code == 404:
            response.status_code = 428
            return {"error": ml.tr(request, "current_user_didnt_join_discord")}
        if r.status_code // 100 != 2:
            response.status_code = 428
            return {"error": ml.tr(request, "user_in_guild_check_failed")}

    await aiosql.execute(dhrid, f"INSERT INTO application(application_type, uid, data, status, submit_timestamp, update_staff_userid, update_staff_timestamp) VALUES ({application_type}, {uid}, '{compress(json.dumps(application,separators=(',', ':')))}', 0, {int(time.time())}, -1, 0)")
    await aiosql.commit(dhrid)
    await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    applicationid = (await aiosql.fetchone(dhrid))[0]

    if discordid is not None and applicantrole != 0 and config.discord_bot_token != "":
        try:
            r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{applicantrole}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when user submits application."}, dhrid = dhrid)
            if r.status_code == 401:
                DisableDiscordIntegration()
            if r.status_code // 100 != 2:
                err = json.loads(r.text)
                await AuditLog(dhrid, -998, ml.ctr("error_adding_discord_role", var = {"code": err["code"], "discord_role": applicantrole, "user_discordid": discordid, "message": err["message"]}))
        except:
            traceback.print_exc()

    language = await GetUserLanguage(dhrid, uid)
    await notification(dhrid, "application", uid, ml.tr(request, "application_submitted", 
            var = {"application_type": application_type_text, "applicationid": applicationid}, force_lang = language), 
        discord_embed = {"title": ml.tr(request, "application_submitted_title", force_lang = language), "description": "", 
            "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True},
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n"
    for d in application.keys():
        msg += f"**{d}**:\n{application[d]}\n\n"

    if webhookurl != "":
        try:
            if t[0][1].startswith("a_"):
                author = {"name": t[0][0], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif"}
            else:
                author = {"name": t[0][0], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png"}
            
            if len(msg) > 4000:
                msg = "*Message too long, please view application in Drivers Hub.*"
                
            r = await arequests.post(webhookurl, data=json.dumps({"content": discord_message_content, "embeds": [{"title": f"New {application_type_text} Application", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": config.int_color}]}), headers = {"Content-Type": "application/json"})
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return {"applicationid": applicationid}

@app.patch(f"/{config.abbr}/application/{{applicationid}}")
async def patch_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /application', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    name = au["name"]

    data = await request.json()
    try:
        message = str(data["message"])
        if len(data["message"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT uid, data, status, application_type FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if uid != t[0][0]:
        response.status_code = 403
        return {"error": ml.tr(request, "not_applicant", force_lang = au["language"])}
    if t[0][2] != 0:
        response.status_code = 409
        if t[0][2] == 1:
            return {"error": ml.tr(request, "application_already_accepted", force_lang = au["language"])}
        elif t[0][2] == 2:
            return {"error": ml.tr(request, "application_already_declined", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "application_already_processed", force_lang = au["language"])}

    data = json.loads(decompress(t[0][1]))
    application_type = t[0][3]
    i = 1
    while 1:
        if not f"[Message] {name} ({userid}) #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {name} ({userid}) #{i}"] = message

    await aiosql.execute(dhrid, f"UPDATE application SET data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n"
    msg += f"**New message**: \n{message}\n\n"

    application_type_text = ""
    discord_message_content = ""
    webhookurl = ""
    for o in config.application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
    if application_type < 1 and application_type > 4 and application_type_text == "":
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if webhookurl != "":
        try:
            if t[0][1].startswith("a_"):
                author = {"name": t[0][0], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif"}
            else:
                author = {"name": t[0][0], "icon_url": f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png"}
            
            if len(msg) > 4000:
                msg = "*Message too long, please view application in Drivers Hub.*"
                
            r = await arequests.post(webhookurl, data=json.dumps({"content": discord_message_content, "embeds": [{"title": f"Application #{applicationid} - New Message", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": config.int_color}]}), headers = {"Content-Type": "application/json"})
            if r.status_code == 401:
                DisableDiscordIntegration()
        except:
            traceback.print_exc()

    return Response(status_code=204)

# Management
@app.patch(f"/{config.abbr}/application/{{applicationid}}/status")
async def update_application_status(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /application/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "application"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffid = au["userid"]
    adminname = au["name"]
    roles = au["roles"]

    data = await request.json()
    try:
        status = int(data["status"])
        message = str(data["message"])
        if len(data["message"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    statustxt = f"N/A"
    if status in STATUS.keys():
        statustxt = STATUS[int(status)]

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}
    
    application_type = t[0][1]
    applicant_uid = t[0][2]

    language = await GetUserLanguage(dhrid, applicant_uid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[status]

    if not checkPerm(roles, "admin"):
        ok = False
        for tt in config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

    data = json.loads(decompress(t[0][3]))
    i = 1
    while 1:
        if not f"[Message] {adminname} ({staffid}) #{i}" in data.keys():
            break
        i += 1
    if message != "":
        data[f"[Message] {adminname} ({staffid}) #{i}"] = message

    update_timestamp = 0
    if status != 0:
        update_timestamp = int(time.time())

    await aiosql.execute(dhrid, f"UPDATE application SET status = {status}, update_staff_userid = {staffid}, update_staff_timestamp = {update_timestamp}, data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await AuditLog(dhrid, staffid, ml.tr(request, "updated_application_status", var = {"id": applicationid, "status": statustxt}))
    await notification(dhrid, "application", applicant_uid, ml.tr(request, "application_status_updated", var = {"applicationid": applicationid, "status": statustxtTR.lower()}, force_lang = language), 
    discord_embed = {"title": ml.tr(request, "application_status_updated_title", force_lang = language), "description": "", "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True}, {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})
    await aiosql.commit(dhrid)

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    return Response(status_code=204)

@app.delete(f"/{config.abbr}/application/{{applicationid}}")
async def delete_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /application', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "delete_application"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffid = au["userid"]
    roles = au["roles"]
    
    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}
    
    application_type = t[0][1]

    if not checkPerm(roles, "admin"):
        ok = False
        for tt in config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}
        
    await aiosql.execute(dhrid, f"DELETE FROM application WHERE applicationid = {applicationid}")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, staffid, ml.ctr("deleted_application", var = {"id": applicationid}))

    return Response(status_code=204)