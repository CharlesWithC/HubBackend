# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from fastapi.responses import StreamingResponse, RedirectResponse
from discord import Webhook, Embed
from aiohttp import ClientSession
from typing import Optional
from datetime import datetime
from io import BytesIO
import json, time, requests, math
import collections, string

from app import app, config, tconfig
from db import newconn
from functions import *
import multilang as ml
from plugins.division import DIVISIONPNT

ROLES = {}
sroles = config.roles
for srole in sroles:
    try:
        ROLES[int(srole["id"])] = srole["name"]
    except:
        pass
ROLES = dict(collections.OrderedDict(sorted(ROLES.items())))

RANKS = config.ranks
RANKROLE = {}
RANKNAME = {}
for t in RANKS:
    try:
        if t["discord_role_id"] != "":
            RANKROLE[int(t["distance"])] = int(t["discord_role_id"])
        else:
            RANKROLE[int(t["distance"])] = 0
        RANKNAME[int(t["distance"])] = t["name"]
    except:
        pass
RANKROLE = dict(collections.OrderedDict(sorted(RANKROLE.items())))
RANKNAME = dict(collections.OrderedDict(sorted(RANKNAME.items())))

divisions = config.divisions
divisionroles = []
for division in divisions:
    divisionroles.append(division["role_id"])

PERMS_STR = {}
for perm in tconfig["perms"].keys():
    PERMS_STR[perm] = []
    for role in tconfig["perms"][perm]:
        PERMS_STR[perm].append(str(role))

def point2rank(point):
    keys = list(RANKROLE.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and point < keys[1]:
        return RANKROLE[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return RANKROLE[keys[i-1]]
    if point >= keys[-1]:
        return RANKROLE[keys[-1]]

def point2rankname(point):
    keys = list(RANKNAME.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and point < keys[1]:
        return RANKNAME[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return RANKNAME[keys[i-1]]
    if point >= keys[-1]:
        return RANKNAME[keys[-1]]

# Basic Info Section
@app.get(f"/{config.abbr}/member/roles")
async def getRoles(request: Request, response: Response):
    return {"error": False, "response": config.roles}

@app.get(f"/{config.abbr}/member/ranks")
async def getRanks(request: Request, response: Response):
    return {"error": False, "response": config.ranks}

@app.get(f"/{config.abbr}/member/perms")
async def getRanks(request: Request, response: Response):
    return {"error": False, "response": PERMS_STR}

# Member Info Section
@app.get(f'/{config.abbr}/member/list')
async def getMemberList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        name: Optional[str] = '', roles: Optional[str] = '', last_seen_after: Optional[int] = -1,\
        order_by: Optional[str] = "highest_role", order: Optional[str] = "desc"):
    rl = ratelimit(request, request.client.host, 'GET /member/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if config.privacy:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        activityUpdate(au["discordid"], f"Viewing Members")
    
    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    lroles = roles.split(",")
    while "" in lroles:
        lroles.remove("")
    if len(lroles) > 5:
        lroles = lroles[:5]

    name = convert_quotation(name).lower()
    
    order_by_last_seen = False
    if not order_by in ["user_id", "name", "discord_id", "highest_role", "join_timestamp", "last_seen"]:
        order_by = "user_id"
        order = "asc"
    if order_by == "last_seen":
        order_by_last_seen = True
    cvt = {"user_id": "userid", "name": "name", "discord_id": "discordid", "join_timestamp": "join_timestamp", "highest_role": "highest_role", "last_seen": "userid"}
    order_by = cvt[order_by]

    sort_by_highest_role = False
    hrole_order_by = "asc"
    if order_by == "highest_role":
        sort_by_highest_role = True
        order_by = "userid"

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    if sort_by_highest_role:
        hrole_order_by = order
        if order == "ASC":
            order = "DESC"
        elif order == "DESC":
            order = "ASC"

    activity_limit = ""
    if last_seen_after >= 0:
        activity_limit = f"AND user.discordid IN (SELECT user_activity.discordid FROM user_activity WHERE user_activity.timestamp >= {last_seen_after}) "

    hrole = {}
    if order_by_last_seen:
        cur.execute(f"SELECT user.userid, user.name, user.discordid, user.roles, user.avatar, user.join_timestamp, user_activity.activity, user_activity.timestamp FROM user LEFT JOIN user_activity ON user.discordid = user_activity.discordid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {activity_limit} ORDER BY user_activity.timestamp {order}, user.userid ASC")
    else:
        cur.execute(f"SELECT user.userid, user.name, user.discordid, user.roles, user.avatar, user.join_timestamp, user_activity.activity, user_activity.timestamp FROM user LEFT JOIN user_activity ON user.discordid = user_activity.discordid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {activity_limit} ORDER BY {order_by} {order}")
    t = cur.fetchall()
    rret = {}
    for tt in t:
        if str(tt[0]) in hrole.keys(): # prevent duplicate result from SQL query
            continue
        roles = tt[3].split(",")
        while "" in roles:
            roles.remove("")
        highestrole = 99999
        ok = False
        if len(lroles) == 0:
            ok = True
        for role in roles:
            if int(role) < highestrole:
                highestrole = int(role)
            if str(role) in lroles:
                ok = True
        if not ok:
            continue
        activity_name = tt[6]
        activity_last_seen = tt[7]
        if activity_last_seen != None:
            if int(time.time()) - activity_last_seen >= 300:
                activity_name = "Offline"
            elif int(time.time()) - activity_last_seen >= 120:
                activity_name = "Online"
        else:
            activity_name = "Offline"
            activity_last_seen = ""
        hrole[str(tt[0])] = highestrole
        rret[str(tt[0])] = {"name": tt[1], "userid": str(tt[0]), "discordid": f"{tt[2]}", "avatar": tt[4], "roles": roles, \
            "join_timestamp": str(tt[5]), "activity": {"name": activity_name, "last_seen": str(activity_last_seen)}}

    ret = []
    if sort_by_highest_role:
        hrole = dict(sorted(hrole.items(), key=lambda x:x[1]))
        if hrole_order_by == "ASC":
            hrole = dict(reversed(list(hrole.items())))
    for userid in hrole.keys():
        ret.append(rret[userid])
        
    return {"error": False, "response": {"list": ret[(page - 1) * page_size : page * page_size], \
        "total_items": str(len(ret)), "total_pages": str(int(math.ceil(len(ret) / page_size)))}}

@app.get(f"/{config.abbr}/member/list/all")
async def getAllMemberList(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'GET /member/list/all', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if config.privacy:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
    
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT steamid, name, userid FROM user WHERE userid >= 0 ORDER BY userid ASC")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"name": tt[1], "userid": str(tt[2]), "steamid": str(tt[0])})
    return {"error": False, "response": {"list": ret}}

@app.get(f'/{config.abbr}/member/banner')
async def getUserBanner(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    if not "banner" in config.enabled_plugins:
        response.status_code = 404
        return {"error": True, "descriptor": "Not Found"}
    
    rl = ratelimit(request, request.client.host, 'GET /member/banner', 60, 60)
    if rl[0]:
        return rl

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
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}

    conn = newconn()
    cur = conn.cursor()
        
    cur.execute(f"SELECT name, discordid, avatar, join_timestamp, roles, userid FROM user WHERE {qu} AND userid >= 0")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}

    if userid == -1:
        return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={t[0][5]}", status_code=302)

    for param in request.query_params:
        if param != "userid":
            return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={userid}", status_code=302)
    
    rl = ratelimit(request, request.client.host, 'GET /member/banner', 10, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
            
    t = t[0]
    userid = t[5]
    name = t[0]
    tname = ""
    for i in range(len(name)):
        if name[i] in string.printable:
            tname += name[i]
    while tname.startswith(" "):
        tname = tname[1:]
    name = tname
    discordid = t[1]
    avatar = t[2]
    join_timestamp = t[3]
    roles = t[4].split(",")
    while "" in roles:
        roles.remove("")
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    highest_role = "Unknown Role"
    if highest in ROLES.keys():
        highest_role = ROLES[highest]
    joined = datetime.fromtimestamp(join_timestamp)
    since = f"{joined.year}/{joined.month}/{joined.day}"

    division = ""
    for i in roles:
        for divi in divisions:
            if str(divi["role_id"]) == str(i):
                division = divi["name"]
                break
    if division == "":
        division = "N/A"

    distance = 0
    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
    t = cur.fetchall()
    for tt in t:
        distance = 0 if t[0][0] is None else int(t[0][0])
        if config.distance_unit == "imperial":
            distance = int(distance * 0.621371)
            distance = f"{distance}mi"
        else:
            distance = f"{distance}km"
    
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 1")
    t = cur.fetchall()
    if len(t) > 0:
        europrofit = 0 if t[0][0] is None else int(t[0][0])
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 2")
    t = cur.fetchall()
    if len(t) > 0:
        dollarprofit = 0 if t[0][0] is None else int(t[0][0])
    profit = f"€{sigfig(europrofit)} + ${sigfig(dollarprofit)}"

    try:
        r = requests.post("http://127.0.0.1:8700/banner", data={"company_abbr": config.abbr, \
            "company_name": config.name, "logo_url": config.logo_url, "hex_color": config.hex_color,
            "discordid": discordid, "since": since, "highest_role": highest_role, \
                "avatar": avatar, "name": name, "division": division, "distance": distance, "profit": profit}, timeout = 10)
        if r.status_code != 200:
            response.status_code = r.status_code
            return {"error": True, "descriptor": r.text}
            
        response = StreamingResponse(iter([r.content]), media_type="image/jpeg")
        response.headers["Cache-Control"] = "public, max-age=7200, stale-if-error=604800"
        return response
        
    except:
        import traceback
        traceback.print_exc()
        response.status_code = 503
        return {"error": True, "descriptor": "Service Unavailable"}

@app.patch(f"/{config.abbr}/member/roles/rank")
async def patchMemberRankRoles(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /member/roles/rank', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    username = au["name"]
    
    conn = newconn()
    cur = conn.cursor()
    
    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371

    # calculate distance
    userdistance = {}
    cur.execute(f"SELECT userid, SUM(distance) FROM dlog WHERE userid = {userid} GROUP BY userid")
    t = cur.fetchall()
    for tt in t:
        if not tt[0] in userdistance.keys():
            userdistance[tt[0]] = tt[1]
        else:
            userdistance[tt[0]] += tt[1]
        userdistance[tt[0]] = int(userdistance[tt[0]])

    # calculate challenge
    userchallenge = {}
    cur.execute(f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid = {userid} GROUP BY userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in userchallenge.keys():
            userchallenge[oo[0]] = 0
        userchallenge[oo[0]] += oo[1]

    # calculate event
    userevent = {}
    cur.execute(f"SELECT attendee, points FROM event WHERE attendee LIKE '%,{userid},%'")
    t = cur.fetchall()
    for tt in t:
        attendees = tt[0].split(",")
        while "" in attendees:
            attendees.remove("")
        for ttt in attendees:
            attendee = int(ttt)
            if not attendee in userevent.keys():
                userevent[attendee] = tt[1]
            else:
                userevent[attendee] += tt[1]
    
    # calculate division
    userdivision = {}
    cur.execute(f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 AND userid = {userid} GROUP BY divisionid, userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in DIVISIONPNT.keys():
            userdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
    
    # calculate myth
    usermyth = {}
    cur.execute(f"SELECT userid, SUM(point) FROM mythpoint WHERE userid = {userid} GROUP BY userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in usermyth.keys():
            usermyth[oo[0]] = 0
        usermyth[oo[0]] += oo[1]
    
    distance = 0
    challengepnt = 0
    eventpnt = 0
    divisionpnt = 0
    mythpnt = 0
    if userid in userdistance.keys():
        distance = userdistance[userid]
    if userid in userchallenge.keys():
        challengepnt = userchallenge[userid]
    if userid in userevent.keys():
        eventpnt = userevent[userid]
    if userid in userdivision.keys():
        divisionpnt = userdivision[userid]
    if userid in usermyth.keys():
        mythpnt = usermyth[userid]

    totalpnt = distance + challengepnt + eventpnt + divisionpnt + mythpnt
    rank = point2rank(totalpnt)

    try:
        if config.discord_bot_token == "":
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3)
        except:
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
            
        if r.status_code == 401:
            DisableDiscordIntegration()
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        elif r.status_code != 200:
            response.status_code = 503
            return {"error": True, "descriptor": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        d = json.loads(r.text)
        if "roles" in d:
            roles = d["roles"]
            curroles = []
            for role in roles:
                if int(role) in list(RANKROLE.values()):
                    curroles.append(int(role))
            if rank in curroles:
                response.status_code = 409
                return {"error": True, "descriptor": ml.tr(request, "already_have_discord_role", force_lang = au["language"])}
            else:
                requests.put(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{rank}', headers=headers, timeout = 3)
                for role in curroles:
                    requests.delete(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3)
                
                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rank}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention)

                if config.rank_up.webhook_url != "" or config.rank_up.channel_id != "":
                    meta = config.rank_up
                    await AutoMessage(meta, setvar)

                rankname = point2rankname(totalpnt)
                notification(discordid, f"You have received a new rank: `{rankname}`")
                return {"error": False, "response": ml.tr(request, "discord_role_given")}
        else:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "must_join_discord", force_lang = au["language"])}

    except:
        import traceback
        traceback.print_exc()

# Member Operation Section
@app.put(f'/{config.abbr}/member')
async def putMember(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PUT /member', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "add_member"])
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
    if len(t) > 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "banned_user_cannot_be_accepted", force_lang = au["language"])}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtuserid'")
    t = cur.fetchall()
    userid = int(t[0][0])
    
    cur.execute(f"SELECT userid, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
    if t[0][0] != -1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "already_member", force_lang = au["language"])}

    name = t[0][1]
    cur.execute(f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE discordid = {discordid}")
    cur.execute(f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(adminid, f'Added member: `{name}` (User ID: `{userid}` | Discord ID: `{discordid}`)')
    conn.commit()

    notification(discordid, f"You have been accepted as a member of **{config.name}**!\nYour User ID is `#{userid}`")

    return {"error": False, "response": {"userid": userid}}   

@app.patch(f'/{config.abbr}/member/roles')
async def patchMemberRoles(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /member/roles', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "division", "update_member_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]

    conn = newconn()
    cur = conn.cursor()

    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)
            
    isAdmin = False
    isHR = False
    isDS = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True

    form = await request.form()
    try:
        userid = int(form["userid"])
        roles = str(form["roles"]).split(",")
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    if userid < 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_userid", force_lang = au["language"])}
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    cur.execute(f"SELECT name, roles, steamid, discordid, truckersmpid FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "member_not_found", force_lang = au["language"])}
    username = t[0][0]
    oldroles = t[0][1].split(",")
    steamid = t[0][2]
    discordid = t[0][3]
    truckersmpid = t[0][4]
    while "" in oldroles:
        oldroles.remove("")
    oldroles = [int(i) for i in oldroles]
    addedroles = []
    removedroles = []
    for role in roles:
        if role not in oldroles:
            addedroles.append(role)
    for role in oldroles:
        if role not in roles:
            removedroles.append(role)

    for add in addedroles:
        if add <= adminhighest:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "add_role_higher_or_equal", force_lang = au["language"])}
    
    for remove in removedroles:
        if remove <= adminhighest:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "remove_role_higher_or_equal", force_lang = au["language"])}

    if len(addedroles) + len(removedroles) == 0:
        return {"error": False}
        
    if not isAdmin and not isHR and isDS:
        for add in addedroles:
            if add not in divisionroles:
                response.status_code = 403
                return {"error": True, "descriptor": "Forbidden"}
        for remove in removedroles:
            if remove not in divisionroles:
                response.status_code = 403
                return {"error": True, "descriptor": "Forbidden"}

    if isAdmin and adminid == userid: # check if user will lose admin permission
        ok = False
        for role in roles:
            if int(role) in config.perms.admin:
                ok = True
        if not ok:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "losing_admin_permission", force_lang = au["language"])}

    if config.perms.driver[0] in addedroles:
        if steamid <= 0:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "steam_not_bound", force_lang = au["language"])}
        if truckersmpid <= 0 and config.truckersmp_bind:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "truckersmp_not_bound", force_lang = au["language"])}

    roles = [str(i) for i in roles]
    cur.execute(f"UPDATE user SET roles = ',{','.join(roles)},' WHERE userid = {userid}")
    conn.commit()

    navio_error = ""

    if config.perms.driver[0] in addedroles:
        r = requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
        if r.status_code == 401:
            navio_error = "Navio API Error: Invalid API Token"
        elif r.status_code != 200:
            try:
                err = json.loads(r.text)["error"]
                if err is None:
                    navio_error = "Navio API Error: `Unknown Error`"
                elif "message" in err.keys():
                    navio_error = "Navio API Error: `" + err["message"] + "`"
            except:
                navio_error = "Navio API Error: `Unknown Error`"
        
        cur.execute(f"SELECT discordid, name FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        userdiscordid = t[0][0]
        username = t[0][1]
        usermention = f"<@{userdiscordid}>"

        if navio_error != "":
            await AuditLog(adminid, f"Failed to add `{username}` (User ID: `{userid}`) to Navio Company.  \n"+navio_error)
        else:
            await AuditLog(adminid, f"Added `{username}` (User ID: `{userid}`) to Navio Company.")
        
        def setvar(msg):
            return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid))

        if config.team_update.webhook_url != "" or config.team_update.channel_id != "":
            meta = config.team_update
            await AutoMessage(meta, setvar)
        
        if config.member_welcome.webhook_url != "" or config.member_welcome.channel_id != "":
            meta = config.member_welcome
            await AutoMessage(meta, setvar)
        
        if config.member_welcome.role_change != [] and config.discord_bot_token != "":
            for role in config.member_welcome.role_change:
                try:
                    if int(role) < 0:
                        requests.delete(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 1)
                    elif int(role) > 0:
                        requests.put(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 1)
                except:
                    import traceback
                    traceback.print_exc()

    if config.perms.driver[0] in removedroles:
        r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
    
    audit = f"Updated `{username}` (User ID: `{userid}`) roles:  \n"
    upd = ""
    for add in addedroles:
        upd += f"`+ {ROLES[add]}`  \n"
        audit += f"`+ {ROLES[add]}`  \n"
    for remove in removedroles:
        upd += f"`- {ROLES[remove]}`  \n"
        audit += f"`- {ROLES[remove]}`  \n"
    audit = convert_quotation(audit[:-1])
    await AuditLog(adminid, audit)
    conn.commit()

    discordid = getUserInfo(userid = userid)["discordid"]
    notification(discordid, f"Your roles have been updated: \n"+upd)

    if navio_error != "":
        return {"error": False, "response": {"navio_api_error": navio_error.replace("Navio API Error: ", "")}}
    else:
        return {"error": False}

@app.patch(f"/{config.abbr}/member/point")
async def patchMemberPoint(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'PATCH /member/point', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hrm", "hr", "update_member_points"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        userid = int(form["userid"])
        distance = int(form["distance"])
        mythpoint = int(form["mythpoint"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if distance != 0:
        if distance > 0:
            cur.execute(f"INSERT INTO dlog VALUES (-1, {userid}, '', 0, {int(time.time())}, 1, 0, 1, 0, {distance}, -1)")
        else:
            cur.execute(f"INSERT INTO dlog VALUES (-1, {userid}, '', 0, {int(time.time())}, 0, 0, 1, 0, {distance}, -1)")
        conn.commit()
    if mythpoint != 0:
        cur.execute(f"INSERT INTO mythpoint VALUES ({userid}, {mythpoint}, {int(time.time())})")
        conn.commit()
    
    if int(distance) > 0:
        distance = "+" + form["distance"]
    
    username = getUserInfo(userid = userid)["name"]
    await AuditLog(adminid, f"Updated points of `{username}` (User ID: `{userid}`):\n  Distance: `{distance}km`\n  Myth Point: `{mythpoint}`")
    discordid = getUserInfo(userid = userid)["discordid"]
    notification(discordid, f"You have been given `{distance}km` and `{mythpoint}` myth points.")

    return {"error": False}

@app.delete(f"/{config.abbr}/member/resign")
async def deleteMember(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request, request.client.host, 'DELETE /member/resign', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    name = convert_quotation(au["name"])

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

    cur.execute(f"SELECT steamid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    steamid = t[0][0]
    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})

    await AuditLog(-999, f'Member resigned: `{name}` (Discord ID: `{discordid}`)')
    notification(discordid, f"You have resigned.")
    
    return {"error": False}

@app.delete(f"/{config.abbr}/member/dismiss")
async def dismissMember(request: Request, response: Response, authorization: str = Header(None), userid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /member/dismiss', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm", "dismiss_member"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    adminid = au["userid"]
    adminroles = au["roles"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    conn = newconn()
    cur = conn.cursor()

    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    cur.execute(f"SELECT userid, steamid, name, roles, discordid FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    steamid = t[0][1]
    name = t[0][2]
    roles = t[0][3].split(",")
    udiscordid = t[0][4]
    while "" in roles:
        roles.remove("")
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    if adminhighest >= highest:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "user_position_higher_or_equal", force_lang = au["language"])}

    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
    
    await AuditLog(adminid, f'Dismissed member: `{name}` (Discord ID: `{udiscordid}`)')
    notification(udiscordid, f"You have been dismissed.")
    return {"error": False}