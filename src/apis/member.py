# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import collections
import json
import math
import os
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse

import multilang as ml
from app import app, config, tconfig
from db import aiosql
from functions import *
from plugins.division import DIVISIONPNT

TRACKERAPP = ""
if config.tracker.lower() == "tracksim":
    TRACKERAPP = "TrackSim"
elif config.tracker.lower() == "navio":
    TRACKERAPP = "Navio"

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
            RANKROLE[int(t["points"])] = int(t["discord_role_id"])
        else:
            RANKROLE[int(t["points"])] = 0
        RANKNAME[int(t["points"])] = t["name"]
    except:
        pass
RANKROLE = dict(collections.OrderedDict(sorted(RANKROLE.items())))
RANKNAME = dict(collections.OrderedDict(sorted(RANKNAME.items())))

divisions = config.divisions
divisionroles = []
for division in divisions:
    try:
        divisionroles.append(division["role_id"])
    except:
        pass

PERMS_STR = {}
for perm in tconfig["perms"].keys():
    PERMS_STR[perm] = []
    for role in tconfig["perms"][perm]:
        try:
            PERMS_STR[perm].append(str(int(role)))
        except:
            pass

def point2rankroleid(point):
    keys = list(RANKROLE.keys())
    if point < keys[0]:
        return -1
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
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
    if point >= keys[0] and (len(keys) == 1 or point < keys[1]):
        return RANKNAME[keys[0]]
    for i in range(1, len(keys)):
        if point >= keys[i-1] and point < keys[i]:
            return RANKNAME[keys[i-1]]
    if point >= keys[-1]:
        return RANKNAME[keys[-1]]

# Basic Info Section
@app.get(f"/{config.abbr}/member/roles")
async def getRoles():
    return config.roles

@app.get(f"/{config.abbr}/member/ranks")
async def getRanks():
    return config.ranks

@app.get(f"/{config.abbr}/member/perms")
async def getRanks():
    return PERMS_STR

# Member Info Section
@app.get(f'/{config.abbr}/member/list')
async def getMemberList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        name: Optional[str] = '', roles: Optional[str] = '', last_seen_after: Optional[int] = -1,\
        order_by: Optional[str] = "highest_role", order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /member/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if config.privacy:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await ActivityUpdate(dhrid, au["uid"], f"members")
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    lroles = roles.split(",")
    lroles = [int(x) for x in lroles if isint(x)]
    if len(lroles) > 100:
        lroles = lroles[:100]

    name = convert_quotation(name).lower()
    
    order_by_last_seen = False
    if not order_by in ["user_id", "name", "uid", "discord_id", "highest_role", "join_timestamp", "last_seen"]:
        order_by = "user_id"
        order = "asc"
    if order_by == "last_seen":
        order_by_last_seen = True
    cvt = {"user_id": "userid", "name": "name", "uid": "uid", "discord_id": "discordid", "join_timestamp": "join_timestamp", "highest_role": "highest_role", "last_seen": "userid"}
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
        activity_limit = f"AND user.uid IN (SELECT user_activity.uid FROM user_activity WHERE user_activity.timestamp >= {last_seen_after}) "

    hrole = {}
    if order_by_last_seen:
        await aiosql.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {activity_limit} ORDER BY user_activity.timestamp {order}, user.userid ASC")
    else:
        await aiosql.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {activity_limit} ORDER BY {order_by} {order}")
    t = await aiosql.fetchall(dhrid)
    rret = {}
    for tt in t:
        if tt[0] in hrole.keys(): # prevent duplicate result from SQL query
            continue
        roles = tt[1].split(",")
        roles = [int(x) for x in roles if isint(x)]
        highestrole = 99999
        ok = False
        if len(lroles) == 0:
            ok = True
        for role in roles:
            if role < highestrole:
                highestrole = role
            if role in lroles:
                ok = True
        if not ok:
            continue
        hrole[tt[0]] = highestrole
        rret[tt[0]] = await GetUserInfo(dhrid, request, userid = tt[0])

    ret = []
    if sort_by_highest_role:
        hrole = dict(sorted(hrole.items(), key=lambda x:x[1]))
        if hrole_order_by == "ASC":
            hrole = dict(reversed(list(hrole.items())))
    for userid in hrole.keys():
        ret.append(rret[userid])
        
    return {"list": ret[(page - 1) * page_size : page * page_size], "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size))}

@app.get(f'/{config.abbr}/member/banner')
async def getUserBanner(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, uid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    if not "banner" in config.enabled_plugins:
        response.status_code = 404
        return {"error": "Not Found"}
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

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
        return {"error": ml.tr(request, "user_not_found")}

    await aiosql.execute(dhrid, f"SELECT name, discordid, avatar, join_timestamp, roles, userid FROM user WHERE {qu} AND userid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    if userid == -1:
        return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={t[0][5]}", status_code=302)

    for param in request.query_params:
        if param != "userid":
            return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={userid}", status_code=302)
            
    t = t[0]
    userid = t[5]
    name = t[0]
    tname = name
    while tname.startswith(" "):
        tname = tname[1:]
    name = tname
    discordid = t[1]
    avatar = t[2]
    join_timestamp = t[3]
    roles = t[4].split(",")
    roles = [int(x) for x in roles if isint(x)]
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    highest_role = ""
    if highest in ROLES.keys():
        highest_role = ROLES[highest]
    joined = datetime.fromtimestamp(join_timestamp)
    joined = f"{joined.year}/{str(joined.month).zfill(2)}/{str(joined.day).zfill(2)}"

    if os.path.exists(f"/tmp/hub/banner/{config.abbr}_{discordid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{config.abbr}_{discordid}.png") <= 3600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{config.abbr}_{discordid}.png","rb").read()]), media_type="image/jpeg")
            return response

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /member/banner', 10, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    division = ""
    for i in roles:
        for divi in divisions:
            if str(divi["role_id"]) == str(i):
                division = divi["name"]
                break
    if division == "":
        division = "N/A"

    distance = 0
    await aiosql.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        distance = 0 if t[0][0] is None else int(t[0][0])
        if config.distance_unit == "imperial":
            distance = int(distance * 0.621371)
            distance = f"{distance}mi"
        else:
            distance = f"{distance}km"
    
    await aiosql.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 1")
    t = await aiosql.fetchall(dhrid)
    europrofit = 0
    if len(t) > 0:
        europrofit = 0 if t[0][0] is None else nint(t[0][0])
    await aiosql.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 2")
    t = await aiosql.fetchall(dhrid)
    dollarprofit = 0
    if len(t) > 0:
        dollarprofit = 0 if t[0][0] is None else nint(t[0][0])
    profit = f"€{sigfig(europrofit)} + ${sigfig(dollarprofit)}"

    try:
        r = await arequests.post("http://127.0.0.1:8700/banner", data={"company_abbr": config.abbr, \
            "company_name": config.name, "logo_url": config.logo_url, "hex_color": config.hex_color,
            "discordid": discordid, "joined": joined, "highest_role": highest_role, \
                "avatar": avatar, "name": name, "division": division, "distance": distance, "profit": profit}, timeout = 5)
        if r.status_code // 100 != 2:
            response.status_code = r.status_code
            return {"error": r.text}
            
        response = StreamingResponse(iter([r.content]), media_type="image/jpeg")
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]
        response.headers["Cache-Control"] = "public, max-age=7200, stale-if-error=604800"
        return response
        
    except:
        response.status_code = 503
        return {"error": "Service Unavailable"}

@app.patch(f"/{config.abbr}/member/roles/rank")
async def patchMemberRankRoles(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /member/roles/rank', 60, 3)
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
    username = au["name"]
    
    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "discord_not_connected", force_lang = au["language"])}
    
    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371

    # calculate distance
    userdistance = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(distance) FROM dlog WHERE userid = {userid} GROUP BY userid")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        if not tt[0] in userdistance.keys():
            userdistance[tt[0]] = nint(tt[1])
        else:
            userdistance[tt[0]] += nint(tt[1])
        userdistance[tt[0]] = int(userdistance[tt[0]])

    # calculate challenge
    userchallenge = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid = {userid} GROUP BY userid")
    o = await aiosql.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userchallenge.keys():
            userchallenge[oo[0]] = 0
        userchallenge[oo[0]] += oo[1]

    # calculate event
    userevent = {}
    await aiosql.execute(dhrid, f"SELECT attendee, points FROM event WHERE attendee LIKE '%,{userid},%'")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        attendees = tt[0].split(",")
        attendees = [int(x) for x in attendees if isint(x)]
        for ttt in attendees:
            attendee = int(ttt)
            if not attendee in userevent.keys():
                userevent[attendee] = tt[1]
            else:
                userevent[attendee] += tt[1]
    
    # calculate division
    userdivision = {}
    await aiosql.execute(dhrid, f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 AND userid = {userid} GROUP BY divisionid, userid")
    o = await aiosql.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in DIVISIONPNT.keys():
            userdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
    
    # calculate myth
    usermyth = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(point) FROM mythpoint WHERE userid = {userid} GROUP BY userid")
    o = await aiosql.fetchall(dhrid)
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

    totalpnt = distance * ratio + challengepnt + eventpnt + divisionpnt + mythpnt
    rankroleid = point2rankroleid(totalpnt)

    if rankroleid == -1:
        response.status_code = 409
        return {"error": ml.tr(request, "already_have_discord_role", force_lang = au["language"])}

    try:
        if config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
        except:
            traceback.print_exc()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
            
        if r.status_code == 401:
            DisableDiscordIntegration()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        elif r.status_code // 100 != 2:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        d = json.loads(r.text)
        if "roles" in d:
            roles = d["roles"]
            curroles = []
            for role in roles:
                if int(role) in list(RANKROLE.values()):
                    curroles.append(int(role))
            if rankroleid in curroles:
                response.status_code = 409
                return {"error": ml.tr(request, "already_have_discord_role", force_lang = au["language"])}
            else:
                try:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{rankroleid}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{rankroleid}> to <@!{discordid}>: `{err["message"]}`')
                    else:
                        for role in curroles:
                            r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                            if r.status_code // 100 != 2:
                                err = json.loads(r.text)
                                await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()
                
                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rankroleid}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention)

                if config.rank_up.webhook_url != "" or config.rank_up.channel_id != "":
                    meta = config.rank_up
                    await AutoMessage(meta, setvar)

                rankname = point2rankname(totalpnt)
                await notification(dhrid, "member", uid, ml.tr(request, "new_rank", var = {"rankname": rankname}, force_lang = await GetUserLanguage(dhrid, uid)), discord_embed = {"title": ml.tr(request, "new_rank_title", force_lang = await GetUserLanguage(dhrid, uid)), "description": f"**{rankname}**", "fields": []})
                return Response(status_code=204)
        else:
            response.status_code = 428
            return {"error": ml.tr(request, "must_join_discord", force_lang = au["language"])}

    except:
        traceback.print_exc()

# Member Operation Section
@app.put(f'/{config.abbr}/member')
async def putMember(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PUT /member', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "add_member"])
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
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "banned_user_cannot_be_accepted", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    if t[0][0] != -1:
        response.status_code = 409
        return {"error": ml.tr(request, "already_member", force_lang = au["language"])}
    name = t[0][1]

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
    t = await aiosql.fetchall(dhrid)
    userid = int(t[0][0])

    await aiosql.execute(dhrid, f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(dhrid, adminid, f'Added member: `{name}` (User ID: `{userid}` | UID: `{uid}`)')
    await aiosql.commit(dhrid)

    await notification(dhrid, "member", uid, ml.tr(request, "member_accepted", var = {"userid": userid}, force_lang = await GetUserLanguage(dhrid, uid, "en")))

    return {"userid": userid}   

@app.patch(f'/{config.abbr}/member/roles')
async def patchMemberRoles(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /member/roles', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "division", "update_member_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]

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

    data = await request.json()
    try:
        userid = int(data["userid"])
        roles = str(data["roles"]).split(",")
        roles = [int(x) for x in roles if isint(x)]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if userid < 0:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_userid", force_lang = au["language"])}
    await aiosql.execute(dhrid, f"SELECT name, roles, steamid, discordid, truckersmpid, uid FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "member_not_found", force_lang = au["language"])}
    username = t[0][0]
    oldroles = t[0][1].split(",")
    steamid = t[0][2]
    discordid = t[0][3]
    truckersmpid = t[0][4]
    uid = t[0][5]
    oldroles = [int(x) for x in oldroles if isint(x)]
    addedroles = []
    removedroles = []
    for role in roles:
        if role not in oldroles:
            addedroles.append(role)
    for role in oldroles:
        if role not in roles:
            removedroles.append(role)

    highestActiveRole = await getHighestActiveRole(dhrid)
    if adminhighest != highestActiveRole: 
        # if operation user doesn't have the highest role,
        # then check if the role to add is lower than operation user's highest role
        for add in addedroles:
            if add <= adminhighest:
                response.status_code = 403
                return {"error": ml.tr(request, "add_role_higher_or_equal", force_lang = au["language"])}
    
        for remove in removedroles:
            if remove <= adminhighest:
                response.status_code = 403
                return {"error": ml.tr(request, "remove_role_higher_or_equal", force_lang = au["language"])}

    if len(addedroles) + len(removedroles) == 0:
        return Response(status_code=204)
        
    if not isAdmin and not isHR and isDS:
        for add in addedroles:
            if add not in divisionroles:
                response.status_code = 403
                return {"error": "Forbidden"}
        for remove in removedroles:
            if remove not in divisionroles:
                response.status_code = 403
                return {"error": "Forbidden"}

    if isAdmin and adminid == userid: # check if user will lose admin permission
        ok = False
        for role in roles:
            if int(role) in config.perms.admin:
                ok = True
        if not ok:
            response.status_code = 400
            return {"error": ml.tr(request, "losing_admin_permission", force_lang = au["language"])}

    if config.perms.driver[0] in addedroles:
        if steamid <= 0:
            response.status_code = 428
            return {"error": ml.tr(request, "steam_not_bound", force_lang = au["language"])}
        if truckersmpid <= 0 and config.truckersmp_bind:
            response.status_code = 428
            return {"error": ml.tr(request, "truckersmp_not_bound", force_lang = au["language"])}

    roles = [str(i) for i in roles]
    await aiosql.execute(dhrid, f"UPDATE user SET roles = ',{','.join(roles)},' WHERE userid = {userid}")
    await aiosql.commit(dhrid)

    def setvar(msg):
        return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid))

    tracker_app_error = ""
    if config.perms.driver[0] in addedroles:
        try:
            if config.tracker.lower() == "tracksim":
                r = await arequests.post("https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
            elif config.tracker.lower() == "navio":
                r = await arequests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
            if r.status_code == 401:
                tracker_app_error = f"{TRACKERAPP} API Error: Invalid API Token"
            elif r.status_code // 100 != 2:
                try:
                    err = json.loads(r.text)["error"]
                    if err is None:
                        tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
                    elif "message" in err.keys():
                        tracker_app_error = f"{TRACKERAPP} API Error: `" + err["message"] + "`"
                except:
                    tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
        except:
            tracker_app_error = f"{TRACKERAPP} API Timeout"

        if tracker_app_error != "":
            await AuditLog(dhrid, adminid, f"Failed to add `{username}` (User ID: `{userid}`) to {TRACKERAPP} Company.  \n"+tracker_app_error)
        else:
            await AuditLog(dhrid, adminid, f"Added `{username}` (User ID: `{userid}`) to {TRACKERAPP} Company.")

        if config.team_update.webhook_url != "" or config.team_update.channel_id != "":
            meta = config.team_update
            await AutoMessage(meta, setvar)
        
        if config.member_welcome.webhook_url != "" or config.member_welcome.channel_id != "":
            meta = config.member_welcome
            await AutoMessage(meta, setvar)
        
        if discordid is not None and config.member_welcome.role_change != [] and config.discord_bot_token != "":
            for role in config.member_welcome.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()

    if config.perms.driver[0] in removedroles:
        try:
            if config.tracker.lower() == "tracksim":
                r = await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
            elif config.tracker.lower() == "navio":
                r = await arequests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
            if r.status_code == 401:
                tracker_app_error = f"{TRACKERAPP} API Error: Invalid API Token"
            elif r.status_code // 100 != 2:
                try:
                    err = json.loads(r.text)["error"]
                    if err is None:
                        tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
                    elif "message" in err.keys():
                        tracker_app_error = f"{TRACKERAPP} API Error: `" + err["message"] + "`"
                except:
                    tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
        except:
            tracker_app_error = f"{TRACKERAPP} API Timeout"

        if tracker_app_error != "":
            await AuditLog(dhrid, adminid, f"Failed to remove `{username}` (User ID: `{userid}`) from {TRACKERAPP} Company.  \n"+tracker_app_error)
        else:
            await AuditLog(dhrid, adminid, f"Removed `{username}` (User ID: `{userid}`) from {TRACKERAPP} Company.")

        if config.member_leave.webhook_url != "" or config.member_leave.channel_id != "":
            meta = config.member_leave
            await AutoMessage(meta, setvar)
        
        if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
            for role in config.member_leave.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()
    
    audit = f"Updated `{username}` (User ID: `{userid}`) roles:  \n"
    upd = ""
    for add in addedroles:
        role_name = f"Role #{add}\n"
        if add in ROLES.keys():
            role_name = ROLES[add]
        upd += f"`+ {role_name}`  \n"
        audit += f"`+ {role_name}`  \n"
    for remove in removedroles:
        role_name = f"Role #{remove}\n"
        if remove in ROLES.keys():
            role_name = ROLES[remove]
        upd += f"`- {role_name}`  \n"
        audit += f"`- {role_name}`  \n"
    audit = audit[:-1]
    await AuditLog(dhrid, adminid, audit)
    await aiosql.commit(dhrid)

    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "role_updated", var = {"detail": upd}, force_lang = await GetUserLanguage(dhrid, uid, "en")))

    if tracker_app_error != "":
        return {"tracker_api_error": tracker_app_error.replace(f"{TRACKERAPP} API Error: ", "")}
    else:
        return Response(status_code=204)

@app.patch(f"/{config.abbr}/member/point")
async def patchMemberPoint(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /member/point', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "update_member_points"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    data = await request.json()
    try:
        userid = int(data["userid"])
        distance = int(data["distance"])
        mythpoint = int(data["mythpoint"])
        if mythpoint > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "mythpoint", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if distance != 0:
        if distance > 0:
            await aiosql.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES (-1, {userid}, '', 0, {int(time.time())}, 1, 0, 1, 0, {distance}, -1, 0, 0)")
        else:
            await aiosql.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES (-1, {userid}, '', 0, {int(time.time())}, 0, 0, 1, 0, {distance}, -1, 0, 0)")
        await aiosql.commit(dhrid)
    if mythpoint != 0:
        await aiosql.execute(dhrid, f"INSERT INTO mythpoint VALUES ({userid}, {mythpoint}, {int(time.time())})")
        await aiosql.commit(dhrid)
    
    if int(distance) > 0:
        distance = "+" + data["distance"]
    
    username = (await GetUserInfo(dhrid, request, userid = userid))["name"]
    await AuditLog(dhrid, adminid, f"Updated points of `{username}` (User ID: `{userid}`):\n  Distance: `{distance}km`\n  Myth Point: `{mythpoint}`")
    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "point_updated", var = {"distance": distance, "mythpoint": mythpoint}, force_lang = await GetUserLanguage(dhrid, uid, "en")))

    return Response(status_code=204)

@app.post(f"/{config.abbr}/member/resign")
async def postMemberResign(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /member/resign', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    userid = au["userid"]
    discordid = au["discordid"]
    name = convert_quotation(au["name"])

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret, steamid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    steamid = t[0][1]
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

    await aiosql.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    await aiosql.commit(dhrid)

    tracker_app_error = ""
    try:
        if config.tracker.lower() == "tracksim":
            r = await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
        elif config.tracker.lower() == "navio":
            r = await arequests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
        if r.status_code == 401:
            tracker_app_error = f"{TRACKERAPP} API Error: Invalid API Token"
        elif r.status_code // 100 != 2:
            try:
                err = json.loads(r.text)["error"]
                if err is None:
                    tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
                elif "message" in err.keys():
                    tracker_app_error = f"{TRACKERAPP} API Error: `" + err["message"] + "`"
            except:
                tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
    except:
        tracker_app_error = f"{TRACKERAPP} API Timeout"

    if tracker_app_error != "":
        await AuditLog(dhrid, -999, f"Failed to remove `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.  \n"+tracker_app_error)
    else:
        await AuditLog(dhrid, -999, f"Removed `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.")

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid))

    if config.member_leave.webhook_url != "" or config.member_leave.channel_id != "":
        meta = config.member_leave
        await AutoMessage(meta, setvar)
    
    if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
        for role in config.member_leave.role_change:
            try:
                if int(role) < 0:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                elif int(role) > 0:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
            except:
                traceback.print_exc()
    
    if discordid is not None:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                roles = d["roles"]
                curroles = []
                for role in roles:
                    if int(role) in list(RANKROLE.values()):
                        curroles.append(int(role))
                for role in curroles:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
        except:
            pass

    await AuditLog(dhrid, -999, f'Member resigned: `{name}` (UID: `{uid}`)')
    await notification(dhrid, "member", uid, ml.tr(request, "member_resigned", force_lang = await GetUserLanguage(dhrid, uid)))
    
    return Response(status_code=204)

@app.post(f"/{config.abbr}/member/dismiss/{{userid}}")
async def postMemberDismiss(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /member/dismiss', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "dismiss_member"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    await aiosql.execute(dhrid, f"SELECT userid, steamid, name, roles, discordid, uid FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    steamid = t[0][1]
    name = t[0][2]
    roles = t[0][3].split(",")
    discordid = t[0][4]
    uid = t[0][5]
    roles = [int(x) for x in roles if isint(x)]
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    if adminhighest >= highest:
        response.status_code = 403
        return {"error": ml.tr(request, "user_position_higher_or_equal", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    await aiosql.commit(dhrid)

    tracker_app_error = ""
    try:
        if config.tracker.lower() == "tracksim":
            r = await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
        elif config.tracker.lower() == "navio":
            r = await arequests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
        if r.status_code == 401:
            tracker_app_error = f"{TRACKERAPP} API Error: Invalid API Token"
        elif r.status_code // 100 != 2:
            try:
                err = json.loads(r.text)["error"]
                if err is None:
                    tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
                elif "message" in err.keys():
                    tracker_app_error = f"{TRACKERAPP} API Error: `" + err["message"] + "`"
            except:
                tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
    except:
        tracker_app_error = f"{TRACKERAPP} API Timeout"

    if tracker_app_error != "":
        await AuditLog(dhrid, -999, f"Failed to remove `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.  \n"+tracker_app_error)
    else:
        await AuditLog(dhrid, -999, f"Removed `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.")

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid))

    if config.member_leave.webhook_url != "" or config.member_leave.channel_id != "":
        meta = config.member_leave
        await AutoMessage(meta, setvar)
    
    if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
        for role in config.member_leave.role_change:
            try:
                if int(role) < 0:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                elif int(role) > 0:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
            except:
                traceback.print_exc() 
    
    if discordid is not None:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                roles = d["roles"]
                curroles = []
                for role in roles:
                    if int(role) in list(RANKROLE.values()):
                        curroles.append(int(role))
                for role in curroles:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
        except:
            pass   
        
    await AuditLog(dhrid, adminid, f'Dismissed member: `{name}` (UID: `{uid}`)')
    await notification(dhrid, "member", uid, ml.tr(request, "member_dismissed", force_lang = await GetUserLanguage(dhrid, uid, "en")))
    return Response(status_code=204)