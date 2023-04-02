# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import traceback
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, query: Optional[str] = '', status: Optional[int] = None, \
        order_by: Optional[str] = "notificationid", order: Optional[str] = "desc"):
    """Returns a list of notification of the authorized user"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user/notification/list', 60, 60)
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

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    query = convertQuotation(query).lower()
    
    if not order_by in ["content", "notificationid"]:
        order_by = "notificationid"
        order = "desc"

    if not order in ["asc", "desc"]:
        if order_by == "notificationid":
            order = "desc"
        elif order_by == "content":
            order = "asc"
    order = order.upper()

    limit = ""
    if status == 0:
        limit += f"AND status = 0"
    elif status == 1:
        limit += f"AND status = 1"

    await app.db.execute(dhrid, f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{query}%' ORDER BY {order_by} {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"notificationid": tt[0], "content": tt[1], "timestamp": tt[2], "read": TF[tt[3]]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{query}%'")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
        
    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_notification(request: Request, response: Response, notificationid: int, authorization: str = Header(None)):
    """Returns a specific notification of the authorized user"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user/notification', 60, 30)
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
    
    await app.db.execute(dhrid, f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE notificationid = {notificationid} AND uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "notification_not_found")}
    tt = t[0]
    return {"notificationid": tt[0], "content": tt[1], "timestamp": tt[2], "read": TF[tt[3]]}

async def patch_status(request: Request, response: Response, notificationid: str, status: int, authorization: str = Header(None)):
    """Updates status of a specific notification of the authorized user"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/notification/status', 60, 30)
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
    
    if notificationid == "all":
        await app.db.execute(dhrid, f"UPDATE user_notification SET status = {status} WHERE uid = {uid}")
        await app.db.commit(dhrid)
        return Response(status_code=204)

    try:
        notificationid = int(notificationid)
    except:
        response.status_code = 404
        return {"error": ml.tr(request, "notification_not_found")}

    await app.db.execute(dhrid, f"SELECT status FROM user_notification WHERE notificationid = {notificationid} AND uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "notification_not_found")}
    
    await app.db.execute(dhrid, f"UPDATE user_notification SET status = {status} WHERE notificationid = {notificationid} AND uid = {uid}")
    await app.db.commit(dhrid)
    
    return Response(status_code=204)

async def get_settings(request: Request, response: Response, authorization: str = Header(None)):
    """Returns notification settings of the authorized user"""

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user/notification/settings', 60, 60)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "economy": False, "event": False}

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    return settings

async def post_settings_enable(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    """Enables a specific type of notification of the authorized user"""

    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "economy", "event"]:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /user/notification/settings/enable', 60, 30)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "economy": False, "event": False}
    settingsok = False

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    if settings[notification_type] == True:
        return Response(status_code=204)
    
    if notification_type != "discord":
        settings[notification_type] = True

    if notification_type == "discord":
        if discordid is None:
            response.status_code = 409
            return {"error": ml.tr(request, "connection_not_found", var = {"app": "Discord"}, force_lang = au["language"])}
        
        if app.config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        rl = await ratelimit(dhrid, request, 'PATCH /user/notification/discord/enable', 60, 5)
        if rl[0]:
            return rl[1]
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post("https://discord.com/api/v10/users/@me/channels", headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=5, dhrid = dhrid)
        except:
            traceback.print_exc()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
        if r.status_code == 401:
            DisableDiscordIntegration()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        if r.status_code // 100 != 2:
            response.status_code = 428
            return {"error": ml.tr(request, "unable_to_dm", force_lang = au["language"])}
        d = json.loads(r.text)
        if "id" in d:
            channelid = str(d["id"])

            r = None
            try:
                r = await arequests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", headers=headers, data=json.dumps({"embeds": [{"title": ml.tr(request, "notification", force_lang = await GetUserLanguage(dhrid, uid)), 
                "description": ml.tr(request, "discord_notification_enabled", force_lang = await GetUserLanguage(dhrid, uid)), \
                "footer": {"text": app.config.name, "icon_url": app.config.logo_url}, \
                "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), timeout=5)
            except:
                traceback.print_exc()

            if r is None or r.status_code // 100 != 2:
                response.status_code = 428
                return {"error": ml.tr(request, "unable_to_dm", force_lang = au["language"])}

            await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'discord-notification'")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                await app.db.execute(dhrid, f"INSERT INTO settings VALUES ({uid}, 'discord-notification', '{channelid}')")
            elif t[0][0] != channelid:
                await app.db.execute(dhrid, f"UPDATE settings SET sval = '{channelid}' WHERE uid = {uid} AND skey = 'discord-notification'")
            await app.db.commit(dhrid)

            settings["discord"] = True

        else:
            response.status_code = 428
            return {"error": ml.tr(request, "unable_to_dm", force_lang = au["language"])}

    res = ""
    for tt in settings.keys():
        if settings[tt]:
            res += tt + ","
    res = res[:-1]
    if settingsok:
        await app.db.execute(dhrid, f"UPDATE settings SET sval = ',{res},' WHERE uid = {uid} AND skey = 'notification'")
    else:
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',{res},')")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_settings_disable(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    """Disables a specific type of notification of the authorized user"""

    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "economy", "event"]:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /user/notification/settings/disable', 60, 60)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "economy": False, "event": False}
    settingsok = False

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    settings[notification_type] = False

    if notification_type == "discord":
        await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid} AND skey = 'discord-notification'")

    res = ""
    for tt in settings.keys():
        if settings[tt]:
            res += tt + ","
    res = res[:-1]
    if settingsok:
        await app.db.execute(dhrid, f"UPDATE settings SET sval = '{res}' WHERE uid = {uid} AND skey = 'notification'")
    else:
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', '{res}')")
    await app.db.commit(dhrid)
    
    return Response(status_code=204)