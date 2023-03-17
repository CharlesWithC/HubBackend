# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import os
import time
import traceback
import uuid
from typing import Optional

import bcrypt
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *


# User Info Section
@app.get(f'/{config.abbr}/user')
async def getUser(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, uid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /user', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    request_uid = -1
    aulanguage = ""
    if userid == -1 and uid == -1 and discordid == -1 and steamid == -1 and truckersmpid == -1:
        au = await auth(dhrid, authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            uid = au["uid"] # self-query
            request_uid = au["uid"]
            aulanguage = au["language"]
    else:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            if config.privacy:
                response.status_code = au["code"]
                del au["code"]
                return au
        else:
            request_uid = au["uid"]
            aulanguage = au["language"]

    qu = ""
    if userid != -1:
        qu = f"userid = {userid}"
    elif uid != -1:
        qu = f"uid = {uid}"
    elif discordid != -1:
        qu = f"discordid = {discordid}"
    elif steamid != -1:
        qu = f"steamid = {steamid}"
    elif truckersmpid != -1:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}

    await aiosql.execute(dhrid, f"SELECT userid, uid FROM user WHERE {qu}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    userid = t[0][0]
    uid = t[0][1]
    
    if userid >= 0:
        await ActivityUpdate(dhrid, request_uid, f"member_{userid}")

    return (await GetUserInfo(dhrid, request, uid = uid))

@app.get(f"/{config.abbr}/user/notification/list")
async def getUserNotificationList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, content: Optional[str] = '', status: Optional[int] = -1, \
        order_by: Optional[str] = "notificationid", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /user/notification/list', 60, 60)
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

    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    content = convert_quotation(content).lower()
    
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

    await aiosql.execute(dhrid, f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{content}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"notificationid": str(tt[0]), "content": tt[1], "timestamp": str(tt[2]), "read": TF[tt[3]]})
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM user_notification WHERE uid = {uid} {limit} AND LOWER(content) LIKE '%{content}%'")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.patch(f"/{config.abbr}/user/notification/status")
async def patchUserNotificationStatus(request: Request, response: Response, authorization: str = Header(None), \
        notificationids: Optional[str] = ""):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/notification/status', 60, 30)
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
    
    data = await request.json()
    try:
        read = 0
        if data["read"] == "true":
            read = 1
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if notificationids == "all":
        await aiosql.execute(dhrid, f"UPDATE user_notification SET status = {read} WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        return Response(status_code=204)

    notificationids = notificationids.split(",")
    
    for notificationid in notificationids:
        try:
            notificationid = int(notificationid)
            await aiosql.execute(dhrid, f"UPDATE user_notification SET status = {read} WHERE notificationid = {notificationid} AND uid = {uid}")
        except:
            pass
    await aiosql.commit(dhrid)
    
    return Response(status_code=204)

@app.get(f"/{config.abbr}/user/notification/settings")
async def getNotificationSettings(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /user/notification/settings', 60, 60)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    return settings

@app.post(f"/{config.abbr}/user/notification/{{notification_type}}/enable")
async def enableNotification(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "event"]:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /user/notification/notification_type/enable', 60, 30)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}
    settingsok = False

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
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
            return {"error": ml.tr(request, "discord_not_connected", force_lang = au["language"])}
        
        if config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/notification/discord/enable', 60, 5)
        if rl[0]:
            return rl[1]
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]

        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = await arequests.post("https://discord.com/api/v10/users/@me/channels", headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3, dhrid = dhrid)
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
                r = await arequests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", headers=headers, data=json.dumps({"embeds": [{"title": ml.tr(request, "notification", force_lang = await GetUserLanguage(dhrid, discordid)), 
                "description": ml.tr(request, "discord_notification_enabled", force_lang = await GetUserLanguage(dhrid, discordid)), \
                "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]}), timeout=3)
            except:
                traceback.print_exc()

            if r is None or r.status_code // 100 != 2:
                response.status_code = 428
                return {"error": ml.tr(request, "unable_to_dm", force_lang = au["language"])}

            await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'discord-notification'")
            t = await aiosql.fetchall(dhrid)
            if len(t) == 0:
                await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ({uid}, 'discord-notification', '{channelid}')")
            elif t[0][0] != channelid:
                await aiosql.execute(dhrid, f"UPDATE settings SET sval = '{channelid}' WHERE uid = {uid} AND skey = 'discord-notification'")
            await aiosql.commit(dhrid)

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
        await aiosql.execute(dhrid, f"UPDATE settings SET sval = ',{res},' WHERE uid = '{uid}' AND skey = 'notification'")
    else:
        await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', ',{res},')")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.post(f"/{config.abbr}/user/notification/{{notification_type}}/disable")
async def disableNotification(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "event"]:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /user/notification/notification_type/disable', 60, 60)
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

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}
    settingsok = False

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    settings[notification_type] = False

    if notification_type == "discord":
        await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = '{uid}' AND skey = 'discord-notification'")

    res = ""
    for tt in settings.keys():
        if settings[tt]:
            res += tt + ","
    res = res[:-1]
    if settingsok:
        await aiosql.execute(dhrid, f"UPDATE settings SET sval = '{res}' WHERE uid = '{uid}' AND skey = 'notification'")
    else:
        await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', '{res}')")
    await aiosql.commit(dhrid)
    
    return Response(status_code=204)

@app.get(f"/{config.abbr}/user/language")
async def getUserLanguage(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /user/language', 60, 60)
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

    return {"language": await GetUserLanguage(dhrid, uid)}

@app.patch(f"/{config.abbr}/user/language")
async def patchUserLanguage(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/language', 60, 30)
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

    data = await request.json()
    try:
        language = convert_quotation(data["language"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if not os.path.exists(config.language_dir + "/" + language + ".json"):
        response.status_code = 400
        return {"error": ml.tr(request, "language_not_supported", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = '{uid}' AND skey = 'language'")
    await aiosql.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'language', '{language}')")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.get(f"/{config.abbr}/user/list")
async def getUserList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, name: Optional[str] = '', \
        order_by: Optional[str] = "uid", order: Optional[str] = "asc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /user/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "get_pending_user_list"])
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
    
    name = convert_quotation(name).lower()
    
    if not order_by in ["name", "uid", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
        order = "asc"
    cvt = {"name": "user.name", "uid": "user.uid", "discord_id": "user.discordid", "join_timestamp": "user.join_timestamp"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    await aiosql.execute(dhrid, f"SELECT user.uid, banned.reason, banned.expire_timestamp FROM user LEFT JOIN banned ON banned.uid = user.uid WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{name}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        user = await GetUserInfo(dhrid, request, uid = tt[0])
        if tt[1] != None:
            user["ban"] = {"reason": tt[1], "expire": tt[2]}
        else:
            user["ban"] = None
        if "roles" in user.keys():
            del user["roles"]
        ret.append(user)
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE userid < 0 AND LOWER(name) LIKE '%{name}%'")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

# Self-Operation Section
@app.patch(f"/{config.abbr}/user/profile")
async def patchUserProfile(request: Request, response: Response, authorization: str = Header(None), \
        uid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/profile', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staffmode = False

    discordid = -1
    if uid == -1 or uid == au["uid"]:
        uid = au["uid"]
        discordid = au["discordid"]
    else:
        au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "hr", "patch_username"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await aiosql.execute(dhrid, f"SELECT discordid FROM user WHERE uid = '{uid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}
        staffmode = True
        discordid = t[0][0]

    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "discord_not_connected", force_lang = au["language"])}
    
    if config.discord_bot_token == "":
        response.status_code = 503
        return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

    try:
        r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
    except:
        traceback.print_exc()
        if not staffmode:
            return {"error": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    if r.status_code == 404:
        if not staffmode:
            return {"error": ml.tr(request, "must_join_discord", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_not_in_discord", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        if not staffmode:
            return {"error": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    d = json.loads(r.text)
    username = convert_quotation(d["user"]["username"])
    avatar = ""
    if config.use_server_nickname and d["nick"] != None:
        username = convert_quotation(d["nick"])
    if d["user"]["avatar"] != None:
        avatar = convert_quotation(d["user"]["avatar"])
        
    await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}', avatar = '{avatar}' WHERE uid = '{uid}'")
    await aiosql.commit(dhrid)

    return Response(status_code=204)
    
@app.patch(f'/{config.abbr}/user/bio')
async def patchUserBio(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/bio', 60, 30)
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

    data = await request.json()
    try:
        bio = str(data["bio"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        
    if len(bio) > 1000:
        response.status_code = 400
        return {"error": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET bio = '{b64e(bio)}' WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.patch(f'/{config.abbr}/user/password')
async def patchPassword(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/password', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    email = t[0][0]

    data = await request.json()
    try:
        password = str(data["password"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if not "@" in email: # make sure it's not empty
        response.status_code = 403
        return {"error": ml.tr(request, "invalid_email", force_lang = au["language"])}
        
    await aiosql.execute(dhrid, f"SELECT userid FROM user WHERE email = '{email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 1:
        response.status_code = 409
        return {"error": ml.tr(request, "too_many_user_with_same_email", force_lang = au["language"])}
        
    if len(password) >= 8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}
    else:
        return {"error": ml.tr(request, "weak_password", force_lang = au["language"])}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await aiosql.execute(dhrid, f"INSERT INTO user_password VALUES ({uid}, '{email}', '{b64e(pwdhash)}')")
    await aiosql.commit(dhrid)

    return Response(status_code=204)
    
@app.delete(f'/{config.abbr}/user/password')
async def deletePassword(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /user/password', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    email = t[0][0]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE email = '{email}'")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.post(f"/{config.abbr}/user/mfa")
async def postMFA(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /user/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    secret = t[0][0]
    if secret != "":
        response.status_code = 409
        return {"error": ml.tr(request, "mfa_already_enabled", force_lang = au["language"])}
    
    data = await request.json()
    try:
        secret = data["secret"]
        otp = int(data["otp"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if len(secret) != 16 or not secret.isalnum():
        response.status_code = 400
        return {"error": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}
    
    try:
        base64.b32decode(secret)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}

    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE user SET mfa_secret = '{secret}' WHERE uid = {uid}")
    await aiosql.commit(dhrid)
        
    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    await AuditLog(dhrid, -999, f"Enabled MFA for `{username}` (UID: `{uid}`)")

    return Response(status_code=204)

@app.delete(f"/{config.abbr}/user/mfa")
async def deleteMFA(request: Request, response: Response, authorization: str = Header(None), uid: Optional[str] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /user/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if uid == -1:
        # self-disable mfa
        au = await auth(dhrid, authorization, request, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        uid = au["uid"]
        
        await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": ml.tr(request, "mfa_not_enabled", force_lang = au["language"])}
    
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        if not valid_totp(otp, secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        await aiosql.execute(dhrid, f"UPDATE user SET mfa_secret = '' WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        
        username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
        await AuditLog(dhrid, -999, f"Disabled MFA for `{username}` (UID: `{uid}`)")

        return Response(status_code=204)
    
    else:
        # admin / hrm disable user mfa
        au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "disable_user_mfa"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": ml.tr(request, "mfa_not_enabled")}
        
        await aiosql.execute(dhrid, f"UPDATE user SET mfa_secret = '' WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        
        username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
        await AuditLog(dhrid, adminid, f"Disabled MFA for `{username}` (UID: `{uid}`)")

        return Response(status_code=204)
        
@app.patch(f"/{config.abbr}/user/steam")
async def patchSteam(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/steam', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    data = await request.json()
    try:
        openid = str(data["callback"]).replace("openid.mode=id_res", "openid.mode=check_authentication")
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    r = None
    try:
        r = await arequests.get("https://steamcommunity.com/openid/login?" + openid, dhrid = dhrid)
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_steam_auth", force_lang = au["language"])}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    await aiosql.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND steamid = {steamid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "steam_bound_to_other_account", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT roles, steamid, userid FROM user WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    roles = t[0][0].split(",")
    roles = [int(x) for x in roles if isint(x)]
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid is not None and userid >= 0:
        if not (await auth(dhrid, authorization, request, required_permission = ["driver"]))["error"]:
            try:
                if config.tracker.lower() == "tracksim":
                    await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(orgsteamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
                    await arequests.post("https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
                elif config.tracker.lower() == "navio":
                    await arequests.delete(f"https://api.navio.app/v1/drivers/{orgsteamid}", headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
                    await arequests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
            except:
                traceback.print_exc()
            await AuditLog(dhrid, userid, f"Updated Steam ID to `{steamid}`")

    await aiosql.execute(dhrid, f"UPDATE user SET steamid = {steamid} WHERE uid = '{uid}'")
    await aiosql.commit(dhrid)

    try:
        r = await arequests.get(f"https://api.truckersmp.com/v2/player/{steamid}", dhrid = dhrid)
        if r.status_code == 200:
            d = json.loads(r.text)
            if not d["error"]:
                truckersmpid = d["response"]["id"]
                await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = '{uid}'")
                await aiosql.commit(dhrid)
                return Response(status_code=204)
    except:
        traceback.print_exc()

    # in case user changed steam
    await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = NULL WHERE uid = '{uid}'")
    await aiosql.commit(dhrid)
    
    return Response(status_code=204)

@app.patch(f"/{config.abbr}/user/truckersmp")
async def patchTruckersMP(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/truckersmp', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    data = await request.json()
    try:
        truckersmpid = data["truckersmpid"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    try:
        truckersmpid = int(truckersmpid)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    r = await arequests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid), dhrid = dhrid)
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, "truckersmp_api_error", force_lang = au["language"])}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT steamid FROM user WHERE uid = '{uid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "steam_not_bound_before_truckersmp", force_lang = au["language"])}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    truckersmp_name = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": ml.tr(request, "truckersmp_steam_mismatch", var = {"truckersmp_name": truckersmp_name, "truckersmpid": str(truckersmpid)}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = '{uid}'")
    await aiosql.commit(dhrid)
    return Response(status_code=204)

# Manage User Section
@app.put(f'/{config.abbr}/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PUT /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    data = await request.json()
    try:
        uid = int(data["uid"])
        expire = int(data["expire"])
        reason = convert_quotation(data["reason"])
        if len(reason) > 256:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "reason", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if expire == -1:
        expire = 253402272000

    await aiosql.execute(dhrid, f"SELECT userid, name, email, discordid, steamid, truckersmpid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    username = "Unknown User"
    email = ""
    discordid = "NULL"
    steamid = "NULL"
    truckersmpid = "NULL"
    if len(t) > 0:
        userid = t[0][0]
        username = t[0][1]
        email = t[0][2]
        discordid = t[0][3]
        steamid = t[0][4]
        truckersmpid = t[0][5]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_ban", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO banned VALUES ({uid}, '{email}', {discordid}, {steamid}, {truckersmpid}, {expire}, '{reason}')")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        duration = "forever"
        if expire != 253402272000:
            duration = f'until `{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))}` UTC'
        await AuditLog(dhrid, adminid, f"Banned `{username}` (UID: `{uid}`) {duration}.")
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "user_already_banned", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/user/ban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    data = await request.json()
    try:
        uid = int(data["uid"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    await aiosql.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 409
        return {"error": ml.tr(request, "user_not_banned", force_lang = au["language"])}
    else:
        await aiosql.execute(dhrid, f"DELETE FROM banned WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        
        username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
        await AuditLog(dhrid, adminid, f"Unbanned `{username}` (UID: `{uid}`)")
        return Response(status_code=204)

# Higher Management Section
@app.patch(f"/{config.abbr}/user/discord")
async def patchUserDiscord(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /user/discord', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "update_user_discord"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    data = await request.json()
    try:
        old_discord_id = int(data["old_discord_id"])
        new_discord_id = int(data["new_discord_id"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        
    if old_discord_id == new_discord_id:
        return Response(status_code=204)

    await aiosql.execute(dhrid, f"SELECT uid, name FROM user WHERE discordid = {old_discord_id}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    old_uid = t[0][0]
    name = t[0][1]

    await aiosql.execute(dhrid, f"SELECT uid, userid FROM user WHERE discordid = {new_discord_id}")
    t = await aiosql.fetchall(dhrid)
    if len(t) >= 0:
        # delete account of new discord, and both sessions
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {old_uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {old_uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {old_uid}")

        # an account exists with the new discordid
        if len(t) > 0:
            if t[0][1] != -1:
                response.status_code = 409
                return {"error": ml.tr(request, "user_must_not_be_member", force_lang = au["language"])}
            new_uid = t[0][0]

            await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {new_uid}")

    # update discord binding
    await aiosql.execute(dhrid, f"UPDATE user SET discordid = {new_discord_id} WHERE uid = {old_uid}")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Updated Discord ID of `{name}` (UID: `{old_uid}`) from `{old_discord_id}` to `{new_discord_id}`")

    return Response(status_code=204)
    
@app.delete(f"/{config.abbr}/user/connections")
async def deleteUserConnection(request: Request, response: Response, uid: Optional[int] = -1, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /user/connections', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "delete_account_connections"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": ml.tr(request, "dismiss_before_unbind", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE user SET steamid = -1, truckersmpid = -1 WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    await AuditLog(dhrid, adminid, f"Deleted connections of `{username}` (UID: `{uid}`)")

    return Response(status_code=204)
    
@app.delete(f"/{config.abbr}/user")
async def deleteUser(request: Request, response: Response, authorization: str = Header(None), uid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /user', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    auth_uid = au["uid"]
    if uid == auth_uid:
        uid = -1

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if uid != -1:
        au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "delete_user"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        userid = t[0][0]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_delete", force_lang = au["language"])}
        username = t[0][1]
        
        await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await aiosql.commit(dhrid)

        await AuditLog(dhrid, adminid, f"Deleted account: `{username}` (UID: `{uid}`)")

        return Response(status_code=204)
    
    else:
        uid = auth_uid
        
        await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        userid = t[0][0]
        username = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "leave_company_before_delete", force_lang = au["language"])}
        
        await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await aiosql.commit(dhrid)

        await AuditLog(dhrid, -999, f"Deleted account: `{username}` (UID: `{uid}`)")

        return Response(status_code=204)