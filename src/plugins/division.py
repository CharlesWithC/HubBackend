# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *

async def get_all_divisions(request: Request):
    app = request.app

    return app.config.divisions

async def get_division(request: Request, response: Response, authorization: str = Header(None), \
        after: Optional[int] = None, before: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /divisions', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if after is None:
        after = 0
    if before is None:
        before = max(int(time.time()), 32503651200)

    await ActivityUpdate(request, au["uid"], "divisions")

    stats = []
    for division in app.config.divisions:
        division_id = division["id"]
        division_role_id = division["role_id"]
        division_point = division["points"]

        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE roles LIKE '%,{division_role_id},%'")
        usertot = nint(await app.db.fetchone(dhrid))

        await app.db.execute(dhrid, f"SELECT division.divisionid, COUNT(dlog.distance), SUM(dlog.distance) \
            FROM dlog \
            INNER JOIN division ON dlog.logid = division.logid AND division.status = 1 AND division.divisionid = {division_id} \
            WHERE dlog.logid >= 0 AND dlog.userid >= 0 \
            GROUP BY division.divisionid")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            jobstot = 0
            pointtot = 0
        else:
            jobstot = nint(t[0][1])
            distance = nint(t[0][2])
            if division_point["mode"] == "static":
                pointtot = jobstot * division_point["value"]
            elif division_point["mode"] == "ratio":
                pointtot = distance * division_point["value"]

        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance), SUM(dlog.fuel) FROM division \
                             LEFT JOIN dlog ON division.logid = dlog.logid \
                             WHERE division.status = 1 AND division.divisionid = {division_id} AND division.logid >= 0 \
                             AND division.request_timestamp >= {after} AND division.request_timestamp <= {before}")
        t = await app.db.fetchone(dhrid)
        distancetot = nint(t[0])
        fueltot = nint(t[1])

        await app.db.execute(dhrid, f"SELECT SUM(dlog.profit) FROM division \
                             LEFT JOIN dlog ON division.logid = dlog.logid AND dlog.unit = 1 \
                             WHERE division.status = 1 AND division.divisionid = {division_id} AND division.logid >= 0 \
                             AND division.request_timestamp >= {after} AND division.request_timestamp <= {before}")
        europrofit = nint(await app.db.fetchone(dhrid))

        await app.db.execute(dhrid, f"SELECT SUM(dlog.profit) FROM division \
                             LEFT JOIN dlog ON division.logid = dlog.logid AND dlog.unit = 2 \
                             WHERE division.status = 1 AND division.divisionid = {division_id} AND division.logid >= 0 \
                             AND division.request_timestamp >= {after} AND division.request_timestamp <= {before}")
        dollarprofit = nint(await app.db.fetchone(dhrid))

        profit = {"euro": europrofit, "dollar": dollarprofit}

        stats.append({"divisionid": division_id, "name": division['name'], "drivers": usertot, "points": pointtot, "jobs": jobstot, "distance": distancetot, "fuel": fueltot, "profit": profit})

    return stats

async def get_dlog_division(request: Request, response: Response, logid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /dlog/division', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    roles = au["roles"]

    await app.db.execute(dhrid, f"SELECT divisionid, userid, request_timestamp, status, update_timestamp, update_staff_userid, message FROM division WHERE logid = {logid} AND logid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
        t = await app.db.fetchall(dhrid)
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

    isStaff = checkPerm(app, roles, ["administrator", "manage_divisions"])

    if not isStaff:
        if userid != duserid and status != 1:
            response.status_code = 404
            return {"error": ml.tr(request, "division_not_validated", force_lang = au["language"])}

    if userid == duserid or isStaff: # delivery driver check division / division staff check delivery
        return {"divisionid": divisionid, "status": status, "request_timestamp": request_timestamp, "update_timestamp": update_timestamp, "update_message": message, "update_staff": await GetUserInfo(request, userid = update_staff_userid)}
    else:
        return {"divisionid": divisionid, "status": status}

async def post_dlog_division(request: Request, response: Response, logid: int, divisionid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /dlog/division', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    await app.db.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    luserid = t[0][0]
    if userid != luserid:
        response.status_code = 403
        return {"error": ml.tr(request, "only_delivery_submitter_can_request_division_validation", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        status = t[0][0]
        if status == 0:
            return {"error": ml.tr(request, "division_already_requested", force_lang = au["language"])}
        elif status == 1:
            return {"error": ml.tr(request, "division_already_validated", force_lang = au["language"])}
        elif status == 2:
            return {"error": ml.tr(request, "division_already_denied", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT roles FROM user WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    roles = str2list(t[0][0])
    joined_divisions = []
    for role in roles:
        if role in app.division_roles:
            for division in app.config.divisions:
                try:
                    if division["role_id"] == role:
                        joined_divisions.append(division["id"])
                except:
                    pass
    if not checkPerm(app, roles, "administrator") and divisionid not in joined_divisions:
        response.status_code = 403
        return {"error": ml.tr(request, "not_division_driver", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    await app.db.commit(dhrid)

    language = await GetUserLanguage(request, uid)
    await notification(request, "division", uid, ml.tr(request, "division_validation_request_submitted", var = {"logid": logid}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_submitted_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": app.division_name[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    dlglink = app.config.frontend_urls.delivery.replace("{logid}", str(logid))
    await app.db.execute(dhrid, f"SELECT userid, name, avatar FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    tt = t[0]
    msg = f"**UID**: {uid}\n**User ID**: {tt[0]}\n**Name**: {tt[1]}\n**Discord**: <@{discordid}> (`{discordid}`)\n\n"
    msg += f"**Delivery ID**: [{logid}]({dlglink})\n**Division**: {app.division_name[divisionid]}"
    avatar = tt[2]

    hook_message = ""
    hook_url = ""
    hook_key = ""
    for o in app.config.divisions:
        if divisionid == o["id"]:
            hook_message = o["message"]
            if o["channel_id"] != "":
                hook_url = f"https://discord.com/api/v10/channels/{o['channel_id']}/messages"
                hook_key = o["channel_id"]
            elif o["webhook_url"] != "":
                hook_url = o["webhook_url"]
                hook_key = o["webhook_url"]
    if hook_url != "":
        try:
            author = {"name": tt[1], "icon_url": avatar}

            headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}

            opqueue.queue(app, "post", hook_key, hook_url, json.dumps({"content": hook_message, "embeds": [{"title": f"New Division Validation Request for Delivery #{logid}", "description": msg, "author": author, "footer": {"text": f"Delivery ID: {logid} "}, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers, "disable")
        except:
            pass

    return Response(status_code=204)

async def patch_dlog_division(request: Request, response: Response, logid: int, divisionid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /dlog/division', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_divisions"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        message = ""
        if "message" in data.keys():
            message = str(data["message"])
            if len(data["message"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "200"}, force_lang = au["language"])}
        status = int(data["status"])
        if abs(status) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "status", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT divisionid, status, userid FROM division WHERE logid = {logid} AND logid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "division_validation_not_found", force_lang = au["language"])}
    if divisionid not in app.division_name.keys():
        divisionid = t[0][0]
    userid = t[0][2]

    staff_role_ids = []
    for division in app.config.divisions:
        if division["id"] == divisionid:
            staff_role_ids = division["staff_role_ids"]
    ok = False
    for role in au["roles"]:
        if role in staff_role_ids:
            ok = True
    if not ok and not checkPerm(app, au["roles"], "administrator"):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE division SET divisionid = {divisionid}, status = {status}, update_staff_userid = {au['userid']}, update_timestamp = {int(time.time())}, message = '{compress(message)}' WHERE logid = {logid}")
    await app.db.commit(dhrid)

    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    await AuditLog(request, au["uid"], ml.ctr(request, "updated_division_validation", var = {"logid": logid, "status": STATUS[status]}))

    uid = (await GetUserInfo(request, userid = userid))["uid"]

    language = await GetUserLanguage(request, uid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[status]

    await notification(request, "division", uid, ml.tr(request, "division_validation_request_status_updated", var = {"logid": logid, "status": statustxtTR.lower()}, force_lang = await GetUserLanguage(request, uid)), \
        discord_embed = {"title": ml.tr(request, "division_validation_request_status_updated_title", force_lang = language), "description": message, \
            "fields": [{"name": ml.tr(request, "division", force_lang = language), "value": app.division_name[divisionid], "inline": True},
                       {"name": ml.tr(request, "log_id", force_lang = language), "value": f"{logid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})

    return Response(status_code=204)

async def get_list_pending(request: Request, response: Response, authorization: str = Header(None), \
        divisionid: Optional[int] = None, \
        page: Optional[int] = 1, page_size: Optional[int] = 10, requested_by: Optional[int] = None, after_logid: Optional[int] = None,
        order_by: Optional[str] = "request_timestamp", order: Optional[str] = "asc"):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /divisions/list/pending', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_divisions"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if divisionid is not None:
        staff_role_ids = []
        for division in app.config.divisions:
            if division["id"] == divisionid:
                staff_role_ids = division["staff_role_ids"]
        ok = False
        for role in au["roles"]:
            if role in staff_role_ids:
                ok = True
        if not ok and not checkPerm(app, au["roles"], "administrator"):
            response.status_code = 403
            return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    allowed_divisions = []
    if not checkPerm(app, au["roles"], "administrator"):
        for division in app.config.divisions:
            for role in division["staff_role_ids"]:
                if role in au["roles"]:
                    allowed_divisions.append(division["id"])
                    breakpoint
    else:
        for division in app.config.divisions:
            allowed_divisions.append(division["id"])
    if len(allowed_divisions) == 0:
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}
    allowed_divisions = ",".join(map(str, allowed_divisions))

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order_by not in ["logid", "userid", "request_timestamp"]:
        order_by = "request_timestamp"
        order = "asc"

    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    limit = ""
    if divisionid is not None:
        limit = f"AND divisionid = {divisionid} "
    if requested_by is not None:
        limit += f"AND userid = {requested_by} "

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT logid FROM division WHERE status = 0 {limit} AND logid >= 0 \
    ORDER BY {order_by} {order}, logid DESC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_logid is not None:
        for tt in t:
            if tt[0] == after_logid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT logid, userid, divisionid FROM division WHERE status = 0 {limit} AND logid >= 0 AND divisionid IN ({allowed_divisions}) ORDER BY {order_by} {order}, logid DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"logid": tt[0], "divisionid": tt[2], "user": await GetUserInfo(request, userid = tt[1])})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}
