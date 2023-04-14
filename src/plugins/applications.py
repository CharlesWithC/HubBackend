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
from functions import *

# Basic Info
async def get_types(request: Request):
    app = request.app
    
    return app.config.application_types

async def get_positions(request: Request):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return []
    else:
        ret = []
        for tt in t[0][0].split(","):
            tt = b64d(tt).strip(" ")
            if tt != "":
                ret.append(tt)
        return ret

async def patch_positions(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /applications/positions', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin", "hrm", "update_application_positions"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

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

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES (0, 'applicationpositions', '{positions}')")
    else:
        await app.db.execute(dhrid, f"UPDATE settings SET sval = '{positions}' WHERE skey = 'applicationpositions'")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "updated_application_positions", var = {"positions": positions_str}))

    return Response(status_code=204)

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, application_type: Optional[int] = None, \
        all_user: Optional[bool] = False, status: Optional[int] = None, order: Optional[str] = "desc"):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /applications/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
        
    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]
    await ActivityUpdate(request, au["uid"], f"applications")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    t = None
    tot = 0
    if all_user == False:
        limit = ""
        if application_type is not None:
            limit = f" AND application_type = {application_type} "

        if status is not None and status in [0,1,2]:
            limit += f" AND status = {status} "

        await app.db.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application WHERE uid = {uid} {limit} ORDER BY applicationid {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
        t = await app.db.fetchall(dhrid)
        
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM application WHERE uid = {uid} {limit}")
        p = await app.db.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]
    else:
        limit = ""
        if not checkPerm(app, roles, "admin"):
            allowed_application_types = []
            for tt in app.config.application_types:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        allowed_application_types.append(tt["id"])
                        break

            if len(allowed_application_types) == 0:
                response.status_code = 403
                return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}
        
            if application_type is None: # show all type
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

        await app.db.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application {limit} ORDER BY applicationid {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
        t = await app.db.fetchall(dhrid)
        
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM application {limit}")
        p = await app.db.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]

    ret = []
    for tt in t:
        ret.append({"applicationid": tt[0], "creator": await GetUserInfo(request, uid = tt[2]), "application_type": tt[1], "status": tt[4], "submit_timestamp": tt[3], "update_timestamp": tt[5], "last_update_staff": await GetUserInfo(request, userid = tt[6])})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /applications', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}

    application_type = t[0][1]
    
    if not checkPerm(app, roles, "admin") and uid != t[0][2]:
        ok = False
        for tt in app.config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

    return {"applicationid": t[0][0], "creator": await GetUserInfo(request, uid = t[0][2]), "application_type": t[0][1], "application": json.loads(decompress(t[0][3])), "status": t[0][4], "submit_timestamp": t[0][5], "update_timestamp": t[0][7], "last_update_staff": await GetUserInfo(request, userid = t[0][6])}

async def post_application(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /applications', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
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
    for o in app.config.application_types:
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
        for r in app.config.perms.driver:
            if r in roles:
                response.status_code = 409
                return {"error": ml.tr(request, "drivers_not_allowed_to_create_driver_application", force_lang = au["language"])}
        await app.db.execute(dhrid, f"SELECT * FROM application WHERE application_type = 1 AND uid = {uid} AND status = 0")
        p = await app.db.fetchall(dhrid)
        if len(p) > 0:
            response.status_code = 409
            return {"error": ml.tr(request, "already_driver_application", force_lang = au["language"])}

    if note == "division" and not checkPerm(app, roles, "admin"):
        ok = False
        for r in app.config.perms.driver:
            if r in roles:
                ok = True
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "must_be_driver_to_submit_division_application", force_lang = au["language"])}        

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE uid = {uid} AND submit_timestamp >= {int(time.time()) - 7200}")
    p = await app.db.fetchall(dhrid)
    if len(p) > 0:
        response.status_code = 429
        return {"error": ml.tr(request, "no_multiple_application_2h", force_lang = au["language"])}

    if userid == -1 and application_type == 3:
        response.status_code = 403
        return {"error": ml.tr(request, "must_be_member_to_submit_loa_application", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid, discordid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if t[0][2] is None and "email" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "email"}, force_lang = au["language"])}
    if t[0][6] is None and ("discord" in app.config.required_connections or app.config.must_join_guild):
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Discord"}, force_lang = au["language"])}
    if t[0][4] is None and "steam" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Steam"}, force_lang = au["language"])}
    if t[0][3] is None and "truckersmp" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "TruckersMP"}, force_lang = au["language"])}
    userid = t[0][5]

    if discordid is not None and app.config.must_join_guild and app.config.discord_bot_token != "":
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {app.config.discord_bot_token}"}, dhrid = dhrid)
        except:
            response.status_code = 428
            return {"error": ml.tr(request, "user_in_guild_check_failed")}
        if r.status_code == 404:
            response.status_code = 428
            return {"error": ml.tr(request, "current_user_didnt_join_discord")}
        if r.status_code // 100 != 2:
            response.status_code = 428
            return {"error": ml.tr(request, "user_in_guild_check_failed")}

    await app.db.execute(dhrid, f"INSERT INTO application(application_type, uid, data, status, submit_timestamp, update_staff_userid, update_staff_timestamp) VALUES ({application_type}, {uid}, '{compress(json.dumps(application,separators=(',', ':')))}', 0, {int(time.time())}, -1, 0)")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    applicationid = (await app.db.fetchone(dhrid))[0]

    if discordid is not None and applicantrole != 0 and app.config.discord_bot_token != "":
        try:
            r = await arequests.put(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{applicantrole}', headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when user submits application."}, dhrid = dhrid)
            if r.status_code == 401:
                DisableDiscordIntegration(app)
            if r.status_code // 100 != 2:
                err = json.loads(r.text)
                await AuditLog(request, -998, ml.ctr(request, "error_adding_discord_role", var = {"code": err["code"], "discord_role": applicantrole, "user_discordid": discordid, "message": err["message"]}))
        except:
            pass

    language = await GetUserLanguage(request, uid)
    await notification(request, "application", uid, ml.tr(request, "application_submitted", 
            var = {"application_type": application_type_text, "applicationid": applicationid}, force_lang = language), 
        discord_embed = {"title": ml.tr(request, "application_submitted_title", force_lang = language), "description": "", 
            "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True},
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    await app.db.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n"
    for d in application.keys():
        msg += f"**{d}**:\n{application[d]}\n\n"

    if webhookurl != "":
        try:
            author = {"name": t[0][0], "icon_url": t[0][1]}
            
            if len(msg) > 4000:
                msg = "*Message too long, please view application in Drivers Hub.*"
                
            r = await arequests.post(app, webhookurl, data=json.dumps({"content": discord_message_content, "embeds": [{"title": f"New {application_type_text} Application", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers = {"Content-Type": "application/json"})
            if r.status_code == 401:
                DisableDiscordIntegration(app)
        except:
            pass

    return {"applicationid": applicationid}

async def patch_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /applications', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
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

    await app.db.execute(dhrid, f"SELECT uid, data, status, application_type FROM application WHERE applicationid = {applicationid}")
    t = await app.db.fetchall(dhrid)
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

    await app.db.execute(dhrid, f"UPDATE application SET data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await app.db.commit(dhrid)

    await app.db.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n"
    msg += f"**New message**: \n{message}\n\n"

    application_type_text = ""
    discord_message_content = ""
    webhookurl = ""
    for o in app.config.application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
    if application_type < 1 and application_type > 4 and application_type_text == "":
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if webhookurl != "":
        try:
            author = {"name": t[0][0], "icon_url": t[0][1]}
            
            if len(msg) > 4000:
                msg = "*Message too long, please view application in Drivers Hub.*"
                
            r = await arequests.post(app, webhookurl, data=json.dumps({"content": discord_message_content, "embeds": [{"title": f"Application #{applicationid} - New Message", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers = {"Content-Type": "application/json"})
            if r.status_code == 401:
                DisableDiscordIntegration(app)
        except:
            pass

    return Response(status_code=204)

async def patch_status(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /applications/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "application"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
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

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}
    
    application_type = t[0][1]
    applicant_uid = t[0][2]

    language = await GetUserLanguage(request, applicant_uid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[status]

    if not checkPerm(app, roles, "admin"):
        ok = False
        for tt in app.config.application_types:
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
        if not f"[Message] {au['name']} ({au['userid']}) #{i}" in data.keys():
            break
        i += 1
    if message != "":
        data[f"[Message] {au['name']} ({au['userid']}) #{i}"] = message

    update_timestamp = 0
    if status != 0:
        update_timestamp = int(time.time())

    await app.db.execute(dhrid, f"UPDATE application SET status = {status}, update_staff_userid = {au['userid']}, update_staff_timestamp = {update_timestamp}, data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await AuditLog(request, au["uid"], ml.tr(request, "updated_application_status", var = {"id": applicationid, "status": statustxt}))
    await notification(request, "application", applicant_uid, ml.tr(request, "application_status_updated", var = {"applicationid": applicationid, "status": statustxtTR.lower()}, force_lang = language), 
    discord_embed = {"title": ml.tr(request, "application_status_updated_title", force_lang = language), "description": "", "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True}, {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})
    await app.db.commit(dhrid)

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    return Response(status_code=204)

async def delete_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /applications', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "delete_application"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    roles = au["roles"]
    
    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}
    
    application_type = t[0][1]

    if not checkPerm(app, roles, "admin"):
        ok = False
        for tt in app.config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}
        
    await app.db.execute(dhrid, f"DELETE FROM application WHERE applicationid = {applicationid}")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_application", var = {"id": applicationid}))

    return Response(status_code=204)