# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import json
import math
import time
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response, Query

import multilang as ml
from functions import *


# Basic Info
async def get_types(request: Request):
    app = request.app
    ret = copy.deepcopy(app.config.application_types)
    to_remove = ["webhook_url", "channel_id", "discord_role_change", "message"]
    for i in range(len(ret)):
        for k in to_remove:
            if k in ret[i].keys():
                del ret[i][k]
    return ret

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_applicationid: Optional[int] = None, \
        submitted_after: Optional[int] = None, submitted_before: Optional[int] = None,
        responded_after: Optional[int] = None, responded_before: Optional[int] = None, \
        order: Optional[str] = "desc", order_by: Optional[str] = "applicationid", \
        submitted_by: Optional[int] = None, responded_by: Optional[int] = None, \
        application_type: Optional[int] = Query(None, alias='type'), \
        all_user: Optional[bool] = False, status: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /applications/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}
    if order_by not in ["applicationid", "submit_timestamp", "respond_timestamp", "applicant_uid", "respond_staff_userid"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    cvt = {"respond_timestamp": "update_staff_timestamp", "applicant_uid": "uid", "respond_staff_userid": "update_staff_userid"}
    if order_by in cvt.keys():
        order_by = cvt[order_by]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]
    await ActivityUpdate(request, au["uid"], "applications")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if submitted_by is not None:
        all_user = True

    t = None
    tot = 0
    if all_user is False:
        limit = ""
        if application_type is not None:
            limit += f" AND application_type = {application_type} "

        if status is not None and status in [0,1,2]:
            limit += f" AND status = {status} "

        if submitted_after is not None:
            limit += f" AND submit_timestamp >= {submitted_after} "
        if submitted_before is not None:
            limit += f" AND submit_timestamp <= {submitted_before} "

        if responded_after is not None:
            limit += f" AND update_staff_timestamp >= {responded_after} "
        if responded_before is not None:
            limit += f" AND update_staff_timestamp <= {responded_before} "

        if responded_by is not None:
            limit += f" AND update_staff_userid = {responded_by} "

        if after_applicationid is not None:
            if order == "asc":
                limit += f" AND applicationid >= {after_applicationid} "
            elif order == "desc":
                limit += f" AND applicationid <= {after_applicationid} "

        limit += " AND applicationid >= 0 "

        await app.db.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application WHERE uid = {uid} {limit} ORDER BY {order_by} {order}, applicationid DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
        t = await app.db.fetchall(dhrid)

        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM application WHERE uid = {uid} {limit}")
        p = await app.db.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]
    else:
        limit = ""
        if not checkPerm(app, roles, "administrator"):
            allowed_application_types = []
            for tt in app.config.application_types:
                allowed_roles = tt["staff_role_ids"]
                for role in allowed_roles:
                    if role in roles:
                        allowed_application_types.append(tt["id"])
                        break

            if len(allowed_application_types) == 0:
                response.status_code = 403
                return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

            allowed_application_types = ",".join(map(str, allowed_application_types))
            limit += f" AND application_type IN ({allowed_application_types}) "
            if application_type is not None:
                limit += f" AND application_type = {application_type} "

        if status is not None and status in [0,1,2]:
            limit += f" AND status = {status} "

        if submitted_after is not None:
            limit += f" AND submit_timestamp >= {submitted_after} "
        if submitted_before is not None:
            limit += f" AND submit_timestamp <= {submitted_before} "

        if responded_after is not None:
            limit += f" AND update_staff_timestamp >= {responded_after} "
        if responded_before is not None:
            limit += f" AND update_staff_timestamp <= {responded_before} "

        if responded_by is not None:
            limit += f" AND update_staff_userid = {responded_by} "

        if after_applicationid is not None:
            if order == "asc":
                limit += f" AND applicationid >= {after_applicationid} "
            elif order == "desc":
                limit += f" AND applicationid <= {after_applicationid} "

        if submitted_by is not None:
            limit += f" AND uid = {submitted_by} "

        limit += " AND applicationid >= 0 "

        limit = limit.strip()
        if limit.startswith("AND"):
            limit = "WHERE " + limit[3:]

        await app.db.execute(dhrid, f"SELECT applicationid, application_type, uid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application {limit} ORDER BY {order_by} {order}, applicationid DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
        t = await app.db.fetchall(dhrid)

        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM application {limit}")
        p = await app.db.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]

    ret = []
    for tt in t:
        ret.append({"applicationid": tt[0], "type": tt[1], "status": tt[4], "submit_timestamp": tt[3], "respond_timestamp": tt[5], "creator": await GetUserInfo(request, uid = tt[2]), "last_respond_staff": await GetUserInfo(request, userid = tt[6])})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /applications', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    roles = au["roles"]

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid} AND applicationid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}

    application_type = t[0][1]

    if not checkPerm(app, roles, "administrator") and uid != t[0][2]:
        ok = False
        for tt in app.config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_ids"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

    return {"applicationid": t[0][0], "type": t[0][1], "status": t[0][4], "submit_timestamp": t[0][5], "respond_timestamp": t[0][7], "creator": await GetUserInfo(request, uid = t[0][2]), "last_respond_staff": await GetUserInfo(request, userid = t[0][6]), "application": json.loads(decompress(t[0][3]))}

async def post_application(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /applications', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    au["roles"]

    data = await request.json()
    try:
        application_type = int(data["type"])
        if abs(application_type) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "type", "limit": "2,147,483,647"}, force_lang = au["language"])}
        application = data["application"]
        if type(data["application"]) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    application_type_text = ""
    discord_role_change = []
    discord_message_content = ""
    hook_url = ""
    hook_key = ""
    meta = ""
    for o in app.config.application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_role_change = o["discord_role_change"]
            discord_message_content = o["message"]
            if o["channel_id"] != "":
                hook_url = f"https://discord.com/api/v10/channels/{o['channel_id']}/messages"
                hook_key = o["channel_id"]
            elif o["webhook_url"] != "":
                hook_url = o["webhook_url"]
                hook_key = o["webhook_url"]
            meta = o
    if application_type_text == "":
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    ok = True
    if meta["required_member_state"] == 0 and au["userid"] >= 0:
        ok = False
    if meta["required_member_state"] == 1 and au["userid"] < 0:
        ok = False

    role_not_ok = (len(meta["required_either_user_role_ids"]) != 0)
    for role_id in meta["required_either_user_role_ids"]:
        if role_id in au["roles"]:
            role_not_ok = False
    ok = ok and not role_not_ok

    role_not_ok = False
    for role_id in meta["required_all_user_role_ids"]:
        if role_id not in au["roles"]:
            role_not_ok = True
    ok = ok and not role_not_ok

    role_not_ok = False
    for role_id in meta["prohibited_either_user_role_ids"]:
        if role_id in au["roles"]:
            role_not_ok = True
    ok = ok and not role_not_ok

    role_not_ok = (len(meta["prohibited_all_user_role_ids"]) != 0)
    for role_id in meta["prohibited_all_user_role_ids"]:
        if role_id not in au["roles"]:
            role_not_ok = False
    ok = ok and not role_not_ok

    if not ok:
        response.status_code = 403
        return {"error": ml.tr(request, "applicant_not_eligible", force_lang = au["language"])}

    if meta["cooldown_hours"] > 0:
        await app.db.execute(dhrid, f"SELECT * FROM application WHERE uid = {uid} AND application_type = {application_type} AND submit_timestamp >= {int(time.time()) - int(nint(meta['cooldown_hours']) * 3600)} AND applicationid >= 0")
        p = await app.db.fetchall(dhrid)
        if len(p) > 0:
            response.status_code = 429
            return {"error": ml.tr(request, "no_multiple_application", var = {"count": str(meta['cooldown_hours'])}, force_lang = au["language"])}

    if not meta["allow_multiple_pending"]:
        await app.db.execute(dhrid, f"SELECT * FROM application WHERE uid = {uid} AND application_type = {application_type} AND status = 0 AND applicationid >= 0")
        p = await app.db.fetchall(dhrid)
        if len(p) > 0:
            response.status_code = 429
            return {"error": ml.tr(request, "same_type_application_exists", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid, discordid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if (t[0][2] is None or "@" not in t[0][2]) and "email" in meta["required_connections"]:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Email"}, force_lang = au["language"])}
    if t[0][6] is None and ("discord" in meta["required_connections"] or app.config.must_join_guild):
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Discord"}, force_lang = au["language"])}
    if t[0][4] is None and "steam" in meta["required_connections"]:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "Steam"}, force_lang = au["language"])}
    if t[0][3] is None and "truckersmp" in meta["required_connections"]:
        response.status_code = 428
        return {"error": ml.tr(request, "must_have_connection", var = {"app": "TruckersMP"}, force_lang = au["language"])}
    userid = t[0][5]

    if discordid is not None and app.config.must_join_guild and app.config.discord_bot_token != "":
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers={"Authorization": f"Bot {app.config.discord_bot_token}"}, dhrid = dhrid)
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
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    applicationid = (await app.db.fetchone(dhrid))[0]

    if discordid is not None and len(discord_role_change) != 0 and app.config.discord_bot_token != "":
        for role in discord_role_change:
            try:
                if int(role) < 0:
                    opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when user submits application."}, f"remove_role,{-int(role)},{discordid}")
                elif int(role) > 0:
                    opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when user submits application."}, f"add_role,{int(role)},{discordid}")
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
        msg += f"**{d}**\n{application[d]}\n\n"

    if hook_url != "":
        try:
            author = {"name": t[0][0], "icon_url": t[0][1]}

            if len(msg) > 4000:
                msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n*{ml.ctr(request, 'application_message_too_long')}*"

            headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}

            opqueue.queue(app, "post", hook_key, hook_url, json.dumps({"content": discord_message_content, "embeds": [{"title": f"New {application_type_text} Application", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers, "disable")
        except:
            pass

    return {"applicationid": applicationid}

async def post_message(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /applications/message', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

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

    await app.db.execute(dhrid, f"SELECT uid, data, status, application_type FROM application WHERE applicationid = {applicationid} AND applicationid >= 0")
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
        if f"[Message] {name} ({userid}) #{i}" not in data.keys():
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
    hook_url = ""
    hook_key = ""
    for o in app.config.application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_message_content = o["message"]
            if o["channel_id"] != "":
                hook_url = f"https://discord.com/api/v10/channels/{o['channel_id']}/messages"
                hook_key = o["channel_id"]
            elif o["webhook_url"] != "":
                hook_url = o["webhook_url"]
                hook_key = o["webhook_url"]
    if application_type < 1 and application_type > 4 and application_type_text == "":
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if hook_url != "":
        try:
            author = {"name": t[0][0], "icon_url": t[0][1]}

            if len(msg) > 4000:
                msg = f"**UID**: {uid}\n**User ID**: {userid}\n**Email**: {t[0][2]}\n**Discord**: <@{discordid}> (`{discordid}`)\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n\n*{ml.ctr(request, 'application_message_too_long')}*"

            headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}

            opqueue.queue(app, "post", hook_key, hook_url, json.dumps({"content": discord_message_content, "embeds": [{"title": f"Application #{applicationid} - New Message", "description": msg, "author": author, "footer": {"text": f"Application ID: {applicationid} "}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers, "disable")
        except:
            pass

    return Response(status_code=204)

async def patch_status(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /applications/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_applications"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    roles = au["roles"]

    data = await request.json()
    try:
        status = int(data["status"])
        if abs(status) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "status", "limit": "2,147,483,647"}, force_lang = au["language"])}
        message = str(data["message"])
        if len(data["message"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    statustxt = "N/A"
    if status in STATUS.keys():
        statustxt = STATUS[int(status)]

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid} AND applicationid >= 0")
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

    if not checkPerm(app, roles, "administrator"):
        ok = False
        for tt in app.config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_ids"]
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
        if f"[Message] {au['name']} ({au['userid']}) #{i}" not in data.keys():
            break
        i += 1

    if message.strip() == "":
        message = f"{ml.tr(request, 'no_message')}"
    data[f"[Message] {au['name']} ({au['userid']}) #{i}"] = message

    await app.db.execute(dhrid, f"UPDATE application SET status = {status}, update_staff_userid = {au['userid']}, update_staff_timestamp = {int(time.time())}, data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await AuditLog(request, au["uid"], "application", ml.ctr(request, "updated_application_status", var = {"id": applicationid, "status": statustxt}))
    await notification(request, "application", applicant_uid, ml.tr(request, "application_status_updated", var = {"applicationid": applicationid, "status": statustxtTR.lower()}, force_lang = language),
    discord_embed = {"title": ml.tr(request, "application_status_updated_title", force_lang = language), "description": "", "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True}, {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_application(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /applications', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "delete_applications"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    roles = au["roles"]

    await app.db.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid} AND applicationid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "application_not_found", force_lang = au["language"])}

    application_type = t[0][1]

    if not checkPerm(app, roles, "administrator"):
        ok = False
        for tt in app.config.application_types:
            if tt["id"] == application_type:
                allowed_roles = tt["staff_role_ids"]
                for role in allowed_roles:
                    if role in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": ml.tr(request, "no_permission_to_application_type", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE application SET applicationid = -applicationid WHERE applicationid = {applicationid}")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], "application", ml.ctr(request, "deleted_application", var = {"id": applicationid}))

    return Response(status_code=204)
