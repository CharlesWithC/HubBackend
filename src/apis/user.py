# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import os, json, time, requests, uuid, math, bcrypt
import traceback

from app import app, config
from db import newconn
from functions import *
import multilang as ml

# User Info Section
@app.get(f'/{config.abbr}/user')
async def getUser(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /user', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    roles = []
    udiscordid = -1
    aulanguage = ""
    if userid == -1 and discordid == -1 and steamid == -1 and truckersmpid == -1:
        au = auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            discordid = au["discordid"]
            roles = au["roles"]
            udiscordid = discordid
            selfq = True
            aulanguage = au["language"]
    else:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            if config.privacy:
                response.status_code = au["code"]
                del au["code"]
                return au
        else:
            udiscordid = au["discordid"]
            roles = au["roles"]
            aulanguage = au["language"]
    
    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True

    qu = ""
    if userid != -1:
        qu = f"userid = {userid}"
    elif discordid != -1:
        qu = f"discordid = {discordid}"
    elif steamid != -1:
        qu = f"steamid = {steamid}"
    elif truckersmpid != -1:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = aulanguage)}

    cur.execute(f"SELECT userid, discordid FROM user WHERE {qu}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    userid = t[0][0]
    discordid = t[0][1]
    
    cur.execute(f"SELECT discordid, name, avatar, roles, join_timestamp, truckersmpid, steamid, bio, email, mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    roles = t[0][3].split(",")
    while "" in roles:
        roles.remove("")
    roles = [str(i) for i in roles]

    mfa_secret = t[0][9]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True

    if userid >= 0:
        activityUpdate(udiscordid, f"member_{userid}")

    activity_last_seen = 0
    activity_name = "offline"
    cur.execute(f"SELECT activity, timestamp FROM user_activity WHERE discordid = {t[0][0]}")
    ac = cur.fetchall()
    if len(ac) != 0:
        activity_name = ac[0][0]
        activity_last_seen = ac[0][1]
        if int(time.time()) - activity_last_seen >= 300:
            activity_name = "offline"
        elif int(time.time()) - activity_last_seen >= 120:
            activity_name = "online"

    if isAdmin or isHR or udiscordid == t[0][0]:
        return {"error": False, "response": {"user": {"name": t[0][1], "userid": str(userid), \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "activity": {"name": activity_name, "last_seen": str(activity_last_seen)}, \
                "email": t[0][8], "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
             "roles": roles, "bio": b64d(t[0][7]), "mfa": mfa_enabled, "join_timestamp": str(t[0][4])}}}
    else:
        return {"error": False, "response": {"user": {"name": t[0][1], "userid": str(userid), \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "activity": {"name": activity_name, "last_seen": str(activity_last_seen)}, \
                "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
                "roles": roles, "bio": b64d(t[0][7]), "join_timestamp": str(t[0][4])}}}

@app.get(f"/{config.abbr}/user/notification/list")
async def getUserNotificationList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, content: Optional[str] = '', status: Optional[int] = -1, \
        order_by: Optional[str] = "notificationid", order: Optional[str] = "desc"):
    rl = ratelimit(request, request.client.host, 'GET /user/notification/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    
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

    cur.execute(f"SELECT notificationid, content, timestamp, status FROM user_notification WHERE discordid = {discordid} {limit} AND LOWER(content) LIKE '%{content}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"notificationid": str(tt[0]), "content": tt[1], "timestamp": str(tt[2]), "read": TF[tt[3]]})
    cur.execute(f"SELECT COUNT(*) FROM user_notification WHERE discordid = {discordid} {limit} AND LOWER(content) LIKE '%{content}%'")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.patch(f"/{config.abbr}/user/notification/status")
async def patchUserNotificationStatus(request: Request, response: Response, authorization: str = Header(None), \
        notificationids: Optional[str] = ""):
    rl = ratelimit(request, request.client.host, 'PATCH /user/notification/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
        
    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        read = 0
        if form["read"] == "true":
            read = 1
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if notificationids == "all":
        cur.execute(f"UPDATE user_notification SET status = {read} WHERE discordid = {discordid}")
        conn.commit()
        return {"error": False}

    notificationids = notificationids.split(",")
    
    for notificationid in notificationids:
        try:
            notificationid = int(notificationid)
            cur.execute(f"UPDATE user_notification SET status = {read} WHERE notificationid = {notificationid} AND discordid = {discordid}")
        except:
            pass
    conn.commit()
    
    return {"error": False}

@app.get(f"/{config.abbr}/user/notification/settings")
async def getNotificationSettings(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'GET /user/notification/settings', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = cur.fetchall()
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    return {"error": False, "response": settings}

@app.post(f"/{config.abbr}/user/notification/{{notification_type}}/enable")
async def enableNotification(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "event"]:
        response.status_code = 404
        return {"error": True, "descriptor": "Not Found"}

    rl = ratelimit(request, request.client.host, 'POST /user/notification/notification_type/enable', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}
    settingsok = False

    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = cur.fetchall()
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    if settings[notification_type] == True:
        return {"error": False}
    
    if notification_type != "discord":
        settings[notification_type] = True

    if notification_type == "discord":
        if config.discord_bot_token == "":
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        rl = ratelimit(request, request.client.host, 'PATCH /user/notification/discord/enable', 60, 5)
        if rl[0]:
            return rl[1]
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]

        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        try:
            r = requests.post("https://discord.com/api/v10/users/@me/channels", headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        except:
            traceback.print_exc()
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
        if r.status_code == 401:
            DisableDiscordIntegration()
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        if r.status_code // 100 != 2:
            return {"error": True, "descriptor": ml.tr(request, "unable_to_dm", force_lang = au["language"])}
        d = json.loads(r.text)
        if "id" in d:
            channelid = str(d["id"])

            r = None
            try:
                r = requests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", headers=headers, data=json.dumps({"embeds": [{"title": ml.tr(request, "notification", force_lang = GetUserLanguage(discordid)), 
                "description": ml.tr(request, "discord_notification_enabled", force_lang = GetUserLanguage(discordid)), \
                "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]}), timeout=3)
            except:
                traceback.print_exc()

            if r is None or r.status_code // 100 != 2:
                return {"error": True, "descriptor": ml.tr(request, "unable_to_dm", force_lang = au["language"])}

            cur.execute(f"SELECT sval FROM settings WHERE discordid = {discordid} AND skey = 'discord-notification'")
            t = cur.fetchall()
            if len(t) == 0:
                cur.execute(f"INSERT INTO settings VALUES ({discordid}, 'discord-notification', '{channelid}')")
            elif t[0][0] != channelid:
                cur.execute(f"UPDATE settings SET sval = '{channelid}' WHERE discordid = {discordid} AND skey = 'discord-notification'")
            conn.commit()

            settings["discord"] = True

        else:
            return {"error": True, "descriptor": ml.tr(request, "unable_to_dm", force_lang = au["language"])}

    res = ""
    for tt in settings.keys():
        if settings[tt]:
            res += tt + ","
    res = res[:-1]
    if settingsok:
        cur.execute(f"UPDATE settings SET sval = ',{res},' WHERE discordid = '{discordid}' AND skey = 'notification'")
    else:
        cur.execute(f"INSERT INTO settings VALUES ('{discordid}', 'notification', ',{res},')")
    conn.commit()

    return {"error": False}

@app.post(f"/{config.abbr}/user/notification/{{notification_type}}/disable")
async def disableNotification(request: Request, response: Response, notification_type: str, authorization: str = Header(None)):
    if notification_type not in ["drivershub", "discord", "login", "dlog", "member", "application", "challenge", "division", "event"]:
        response.status_code = 404
        return {"error": True, "descriptor": "Not Found"}

    rl = ratelimit(request, request.client.host, 'POST /user/notification/notification_type/disable', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()

    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}
    settingsok = False

    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = cur.fetchall()
    if len(t) != 0:
        settingsok = True
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    settings[notification_type] = False

    if notification_type == "discord":
        cur.execute(f"DELETE FROM settings WHERE discordid = '{discordid}' AND skey = 'discord-notification'")

    res = ""
    for tt in settings.keys():
        if settings[tt]:
            res += tt + ","
    res = res[:-1]
    if settingsok:
        cur.execute(f"UPDATE settings SET sval = '{res}' WHERE discordid = '{discordid}' AND skey = 'notification'")
    else:
        cur.execute(f"INSERT INTO settings VALUES ('{discordid}', 'notification', '{res}')")
    conn.commit()
    
    return {"error": False}

@app.get(f"/{config.abbr}/user/language")
async def getUserLanguage(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'GET /user/language', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": False, "response": {"language": "en"}}
    return {"error": False, "response": {"language": t[0][0]}}

@app.patch(f"/{config.abbr}/user/language")
async def patchUserLanguage(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/language', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    form = await request.form()
    try:
        language = convert_quotation(form["language"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if not os.path.exists(config.language_dir + "/" + language + ".json"):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "language_not_supported", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
    cur.execute(f"INSERT INTO settings VALUES ('{discordid}', 'language', '{language}')")
    conn.commit()

    return {"error": False}

@app.get(f"/{config.abbr}/user/list")
async def getUserList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, name: Optional[str] = '', \
        order_by: Optional[str] = "discord_id", order: Optional[str] = "asc"):
    rl = ratelimit(request, request.client.host, 'GET /user/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "get_pending_user_list"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
    
    name = convert_quotation(name).lower()
    
    if not order_by in ["name", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
        order = "asc"
    cvt = {"name": "user.name", "discord_id": "user.discordid", "join_timestamp": "user.join_timestamp"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    cur.execute(f"SELECT user.userid, user.name, user.discordid, user.join_timestamp, user.avatar, banned.reason FROM user LEFT JOIN banned ON banned.discordid = user.discordid WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{name}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        banreason = ""
        banned = False
        if tt[5] != None:
            banned = True
            banreason = tt[5]
        ret.append({"name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[4], "ban": {"is_banned": TF[banned], "reason": banreason}, "join_timestamp": tt[3]})
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid < 0 AND LOWER(name) LIKE '%{name}%'")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

# Self-Operation Section
@app.patch(f"/{config.abbr}/user/profile")
async def patchUserProfile(request: Request, response: Response, authorization: str = Header(None), \
        discordid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'PATCH /user/profile', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    conn = newconn()
    cur = conn.cursor()

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staffmode = False

    if discordid == -1 or discordid == au["discordid"]:
        discordid = au["discordid"]
    else:
        au = auth(authorization, request, required_permission = ["admin", "hrm", "hr", "patch_username"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        cur.execute(f"SELECT discordid FROM user WHERE discordid = '{discordid}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
        staffmode = True

    if config.discord_bot_token == "":
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

    try:
        r = requests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"})
    except:
        traceback.print_exc()
        if not staffmode:
            return {"error": True, "descriptor": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": True, "descriptor": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    if r.status_code == 404:
        if not staffmode:
            return {"error": True, "descriptor": ml.tr(request, "must_join_discord", force_lang = au["language"])}
        else:
            return {"error": True, "descriptor": ml.tr(request, "user_not_in_discord", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        if not staffmode:
            return {"error": True, "descriptor": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": True, "descriptor": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    d = json.loads(r.text)
    username = convert_quotation(d["user"]["username"])
    avatar = ""
    if config.use_server_nickname and d["nick"] != None:
        username = convert_quotation(d["nick"])
    if d["user"]["avatar"] != None:
        avatar = convert_quotation(d["user"]["avatar"])
        
    cur.execute(f"UPDATE user SET name = '{username}', avatar = '{avatar}' WHERE discordid = '{discordid}'")
    conn.commit()

    return {"error": False}
    
@app.patch(f'/{config.abbr}/user/bio')
async def patchUserBio(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/bio', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        bio = str(form["bio"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
        
    if len(bio) > 1000:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}

    cur.execute(f"UPDATE user SET bio = '{b64e(bio)}' WHERE discordid = {discordid}")
    conn.commit()

    return {"error": False}

@app.patch(f'/{config.abbr}/user/password')
async def patchPassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/password', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    form = await request.form()
    try:
        password = str(form["password"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if not "@" in email: # make sure it's not empty
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "invalid_email", force_lang = au["language"])}
        
    cur.execute(f"SELECT userid FROM user WHERE email = '{email}'")
    t = cur.fetchall()
    if len(t) > 1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "too_many_user_with_same_email", force_lang = au["language"])}
        
    if len(password) >= 8:
        if not (bool(re.match('((?=.*\d)(?=.*[a-z])(?=.*[A-Z])(?=.*[!@#$%^&*]).{8,30})',password))==True) and \
            (bool(re.match('((\d*)([a-z]*)([A-Z]*)([!@#$%^&*]*).{8,30})',password))==True):
            return {"error": True, "descriptor": ml.tr(request, "weak_password", force_lang = au["language"])}
    else:
        return {"error": True, "descriptor": ml.tr(request, "weak_password", force_lang = au["language"])}

    password = password.encode('utf-8')
    salt = bcrypt.gensalt()
    pwdhash = bcrypt.hashpw(password, salt).decode()

    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    cur.execute(f"INSERT INTO user_password VALUES ({discordid}, '{email}', '{b64e(pwdhash)}')")
    conn.commit()

    return {"error": False}
    
@app.delete(f'/{config.abbr}/user/password')
async def deletePassword(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /user/password', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    mfa_secret = t[0][0]
    if mfa_secret != "":
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    cur.execute(f"SELECT email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    email = t[0][0]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
    cur.execute(f"DELETE FROM user_password WHERE email = '{email}'")
    conn.commit()

    return {"error": False}

@app.post(f"/{config.abbr}/user/tip")
async def postTemporaryIdentityProof(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'POST /user/tip', 180, 20)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    stoken = str(uuid.uuid4())
    while stoken[0] == "f":
        stoken = str(uuid.uuid4())
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"INSERT INTO temp_identity_proof VALUES ('{stoken}', {discordid}, {int(time.time())+180})")
    conn.commit()

    return {"error": False, "response": {"token": stoken}}

@app.get(f"/{config.abbr}/user/tip")
async def getTemporaryIdentityProof(request: Request, response: Response, token: Optional[str] = ""):
    rl = ratelimit(request, request.client.host, 'GET /user/tip', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    token = token.replace("'","")

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM temp_identity_proof WHERE expire <= {int(time.time())}")
    cur.execute(f"SELECT discordid FROM temp_identity_proof WHERE token = '{token}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_token")}
    cur.execute(f"DELETE FROM temp_identity_proof WHERE token = '{token}'")
    conn.commit()
    return {"error": False, "response": {"user": getUserInfo(discordid = t[0][0])}}

@app.post(f"/{config.abbr}/user/mfa")
async def postMFA(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'POST /user/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    secret = t[0][0]
    if secret != "":
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "mfa_already_enabled", force_lang = au["language"])}
    
    form = await request.form()
    try:
        secret = form["secret"]
        otp = int(form["otp"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if len(secret) != 16 or not secret.isalnum():
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}
    
    try:
        base64.b32decode(secret)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_secret", force_lang = au["language"])}

    if not valid_totp(otp, secret):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    
    cur.execute(f"UPDATE user SET mfa_secret = '{secret}' WHERE discordid = {discordid}")
    conn.commit()
        
    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(-999, f"Enabled MFA for `{username}` (Discord ID: `{discordid}`)")

    return {"error": False}

@app.delete(f"/{config.abbr}/user/mfa")
async def deleteMFA(request: Request, response: Response, authorization: str = Header(None), discordid: Optional[str] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /user/mfa', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if discordid == -1:
        # self-disable mfa
        au = auth(authorization, request, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        discordid = au["discordid"]
        
        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "mfa_not_enabled", force_lang = au["language"])}
    
        form = await request.form()
        try:
            otp = int(form["otp"])
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        if not valid_totp(otp, secret):
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        
        cur.execute(f"UPDATE user SET mfa_secret = '' WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(-999, f"Disabled MFA for `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}
    
    else:
        # admin / hrm disable user mfa
        au = auth(authorization, request, required_permission = ["admin", "hrm", "disable_user_mfa"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"SELECT mfa_secret FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
        secret = t[0][0]
        if secret == "":
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "mfa_not_enabled")}
        
        cur.execute(f"UPDATE user SET mfa_secret = '' WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(adminid, f"Disabled MFA for `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}
        
@app.patch(f"/{config.abbr}/user/steam")
async def patchSteam(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/steam', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        openid = str(form["callback"]).replace("openid.mode=id_res", "openid.mode=check_authentication")
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    r = None
    try:
        r = requests.get("https://steamcommunity.com/openid/login?" + openid)
    except:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_steam_auth", force_lang = au["language"])}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    cur.execute(f"SELECT * FROM user WHERE discordid != '{discordid}' AND steamid = {steamid}")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "steam_bound_to_other_account", force_lang = au["language"])}

    cur.execute(f"SELECT roles, steamid, userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    while "" in roles:
        roles.remove("")
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid != 0 and userid >= 0:
        cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%Updated Steam ID%' AND userid = {userid} AND timestamp >= {int(time.time() - 86400 * 3)}")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 429
            return {"error": True, "descriptor": ml.tr(request, "steam_updated_within_3d", force_lang = au["language"])}

        for role in roles:
            if role == "100":
                try:
                    requests.delete(f"https://api.navio.app/v1/drivers/{orgsteamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
                    requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
                except:
                    traceback.print_exc()
                await AuditLog(userid, f"Updated Steam ID to `{steamid}`")

    cur.execute(f"UPDATE user SET steamid = {steamid} WHERE discordid = '{discordid}'")
    conn.commit()

    try:
        r = requests.get(f"https://api.truckersmp.com/v2/player/{steamid}")
        if r.status_code == 200:
            d = json.loads(r.text)
            if not d["error"]:
                truckersmpid = d["response"]["id"]
                cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
                conn.commit()
                return {"error": False}
    except:
        traceback.print_exc()

    # in case user changed steam
    cur.execute(f"UPDATE user SET truckersmpid = 0 WHERE discordid = '{discordid}'")
    conn.commit()
    
    return {"error": False}

@app.patch(f"/{config.abbr}/user/truckersmp")
async def patchTruckersMP(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/truckersmp', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        truckersmpid = form["truckersmpid"]
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    try:
        truckersmpid = int(truckersmpid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    r = requests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid))
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_api_error", force_lang = au["language"])}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    cur.execute(f"SELECT steamid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "steam_not_bound_before_truckersmp", force_lang = au["language"])}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    truckersmp_name = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_steam_mismatch", var = {"truckersmp_name": truckersmp_name, "truckersmpid": str(truckersmpid)}, force_lang = au["language"])}

    cur.execute(f"UPDATE user SET truckersmpid = {truckersmpid} WHERE discordid = '{discordid}'")
    conn.commit()
    return {"error": False}

# Manage User Section
@app.put(f'/{config.abbr}/user/ban')
async def userBan(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PUT /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
        expire = int(form["expire"])
        reason = convert_quotation(form["reason"])
        if len(reason) > 256:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "reason", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    if expire == -1:
        expire = 253402272000
    try:
        discordid = int(discordid)
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_discordid", force_lang = au["language"])}

    cur.execute(f"SELECT userid, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    username = "Unknown User"
    if len(t) > 0:
        userid = t[0][0]
        username = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "dismiss_before_ban", force_lang = au["language"])}

    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO banned VALUES ({discordid}, {expire}, '{reason}')")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        conn.commit()
        duration = "forever"
        if expire != 253402272000:
            duration = f'until `{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))}` UTC'
        await AuditLog(adminid, f"Banned `{username}` (Discord ID: `{discordid}`) {duration}.")
        return {"error": False}
    else:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_already_banned", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/user/ban')
async def userUnban(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_not_banned", force_lang = au["language"])}
    else:
        cur.execute(f"DELETE FROM banned WHERE discordid = {discordid}")
        conn.commit()
        
        username = getUserInfo(discordid = discordid)["name"]
        await AuditLog(adminid, f"Unbanned `{username}` (Discord ID: `{discordid}`)")
        return {"error": False}

# Higher Management Section
@app.patch(f"/{config.abbr}/user/discord")
async def patchUserDiscord(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /user/discord', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hrm", "update_user_discord"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        old_discord_id = int(form["old_discord_id"])
        new_discord_id = int(form["new_discord_id"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
        
    if old_discord_id == new_discord_id:
        return {"error": False}

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {old_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}

    cur.execute(f"SELECT discordid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "user_must_register_first", force_lang = au["language"])}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {new_discord_id}")
    t = cur.fetchall()
    if len(t) > 0 and t[0][0] != -1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "user_must_not_be_member", force_lang = au["language"])}

    # delete account of new discord, and both sessions
    cur.execute(f"DELETE FROM session WHERE discordid = {old_discord_id}")
    cur.execute(f"DELETE FROM appsession WHERE discordid = {old_discord_id}")
    cur.execute(f"DELETE FROM temp_identity_proof WHERE discordid = {old_discord_id}")

    cur.execute(f"DELETE FROM user WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM session WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM appsession WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM temp_identity_proof WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM user_password WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM user_activity WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM user_notification WHERE discordid = {new_discord_id}")
    cur.execute(f"DELETE FROM settings WHERE discordid = {new_discord_id}")

    # update discord binding
    cur.execute(f"UPDATE user SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    cur.execute(f"UPDATE user_password SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    cur.execute(f"UPDATE user_activity SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    cur.execute(f"UPDATE user_notification SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    cur.execute(f"UPDATE application SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    cur.execute(f"UPDATE settings SET discordid = {new_discord_id} WHERE discordid = {old_discord_id}")
    conn.commit()

    await AuditLog(adminid, f"Updated Discord ID from `{old_discord_id}` to `{new_discord_id}`")

    return {"error": False}
    
@app.delete(f"/{config.abbr}/user/connections")
async def deleteUserConnection(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /user/connections', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hrm", "delete_account_connections"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    try:
        discordid = int(form["discordid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "dismiss_before_unbind", force_lang = au["language"])}
    
    cur.execute(f"UPDATE user SET steamid = -1, truckersmpid = -1 WHERE discordid = {discordid}")
    conn.commit()

    username = getUserInfo(discordid = discordid)["name"]
    await AuditLog(adminid, f"Deleted connections of `{username}` (Discord ID: `{discordid}`)")

    return {"error": False}
    
@app.delete(f"/{config.abbr}/user")
async def deleteUser(request: Request, response: Response, authorization: str = Header(None), discordid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /user', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    auth_discordid = au["discordid"]
    if discordid == auth_discordid:
        discordid = -1

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if discordid != -1:
        au = auth(authorization, request, required_permission = ["admin", "hrm", "delete_user"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        conn = newconn()
        cur = conn.cursor()
        
        cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
        userid = t[0][0]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "dismiss_before_delete", force_lang = au["language"])}
        
        username = getUserInfo(discordid = discordid)["name"]
        cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_activity WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_notification WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM temp_identity_proof WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM settings WHERE discordid = {discordid}")
        conn.commit()

        await AuditLog(adminid, f"Deleted account: `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}
    
    else:
        discordid = auth_discordid
        
        conn = newconn()
        cur = conn.cursor()
        
        cur.execute(f"SELECT userid, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        userid = t[0][0]
        name = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "leave_company_before_delete", force_lang = au["language"])}
        
        username = getUserInfo(discordid = discordid)["name"]
        cur.execute(f"DELETE FROM user WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_password WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_activity WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM user_notification WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM session WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM temp_identity_proof WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM appsession WHERE discordid = {discordid}")
        cur.execute(f"DELETE FROM settings WHERE discordid = {discordid}")
        conn.commit()

        await AuditLog(-999, f"Deleted account: `{username}` (Discord ID: `{discordid}`)")

        return {"error": False}