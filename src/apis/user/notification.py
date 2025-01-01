# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import json
import math
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, after_notificationid: Optional[int] = None, \
        content: Optional[str] = '', status: Optional[int] = None, \
        order_by: Optional[str] = "notificationid", order: Optional[str] = "desc"):
    """Returns a list of notification of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /user/notification/list', 60, 120)
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

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 500:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    content = convertQuotation(content).lower()

    if order_by not in ['notificationid', 'content', 'timestamp']:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    limit = ""
    if status == 0:
        limit += "AND status = 0 "
    elif status == 1:
        limit += "AND status = 1 "
    if after_notificationid is not None:
        if order == "asc":
            limit += f"AND notificationid >= {after_notificationid} "
        elif order == "desc":
            limit += f"AND notificationid <= {after_notificationid} "

    await app.db.execute(dhrid, f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{content}%' ORDER BY {order_by} {order}, notificationid DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"notificationid": tt[0], "content": tt[1], "timestamp": tt[2], "read": TF[tt[3]]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{content}%'")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_notification(request: Request, response: Response, notificationid: int, authorization: str = Header(None)):
    """Returns a specific notification of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /user/notification', 60, 120)
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

    await app.db.execute(dhrid, f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE notificationid = {notificationid} AND uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "notification_not_found")}
    tt = t[0]
    return {"notificationid": tt[0], "content": tt[1], "timestamp": tt[2], "read": TF[tt[3]]}

async def delete_notification(request: Request, response: Response, after_notificationid: int, before_notificationid: int, authorization: str = Header(None)):
    """Delete a range of notifications (for authorized users / for all users)"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /user/notification', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    # first delete for current user
    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid} AND notificationid >= {after_notificationid} AND notificationid <= {before_notificationid}")
    await app.db.commit(dhrid)

    if checkPerm(app, au["roles"], ["administrator", "delete_notifications"]):
        # then delete for all users
        await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE notificationid >= {after_notificationid} AND notificationid <= {before_notificationid}")
        await app.db.commit(dhrid)

    return Response(status_code=204)

async def patch_status(request: Request, response: Response, notificationid: str, status: int, authorization: str = Header(None)):
    """Updates status of a specific notification of the authorized user"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/notification/status', 60, 120)
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
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /user/notification/settings', 60, 120)
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

    settings = copy.deepcopy(NOTIFICATION_SETTINGS)

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    return settings

# NOTE: Daily bonus notification is handled separately in member/userop
async def post_settings_enable(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    """Enables a specific type of notification of the authorized user"""
    app = request.app
    if notification_type not in copy.deepcopy(NOTIFICATION_SETTINGS).keys():
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /user/notification/settings/enable', 60, 60)
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

    settings = copy.deepcopy(NOTIFICATION_SETTINGS)
    settingsok = False

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if settings[notification_type] is True:
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

        rl = await ratelimit(request, 'POST /user/notification/discord/enable', 60, 5)
        if rl[0]:
            return rl[1]
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post(app, "https://discord.com/api/v10/users/@me/channels", headers = headers, data = json.dumps({"recipient_id": discordid}), dhrid = dhrid)
        except:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
        if r.status_code == 401:
            DisableDiscordIntegration(app)
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
                r = await arequests.post(app, f"https://discord.com/api/v10/channels/{channelid}/messages", headers = headers, data=json.dumps({"embeds": [{"title": ml.tr(request, "notification", force_lang = await GetUserLanguage(request, uid)),
                "description": ml.tr(request, "discord_notification_enabled", force_lang = await GetUserLanguage(request, uid)), \
                "footer": {"text": app.config.name, "icon_url": app.config.logo_url}, \
                "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}))
            except:
                pass

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
    app = request.app
    if notification_type not in copy.deepcopy(NOTIFICATION_SETTINGS).keys():
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /user/notification/settings/disable', 60, 60)
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

    settings = copy.deepcopy(NOTIFICATION_SETTINGS)
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
