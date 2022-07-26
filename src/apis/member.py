# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests
from discord import Webhook
from typing import Optional
from datetime import datetime
import collections

from app import app, config, tconfig
from db import newconn
from functions import *
import multilang as ml

DIVISIONPNT = {}
for division in config.divisions:
    DIVISIONPNT[division["id"]] = int(division["point"])

sroles = tconfig["roles"]
ROLES = {}
for key in sroles:
    ROLES[int(key)] = sroles[key]
ROLES = dict(collections.OrderedDict(sorted(ROLES.items())))

RANKS = tconfig["ranks"]
RANKROLE = {}
RANKNAME = {}
for t in RANKS:
    if t["discord_role_id"] != "":
        RANKROLE[int(t["distance"])] = int(t["discord_role_id"])
    else:
        RANKROLE[int(t["distance"])] = 0
    RANKNAME[int(t["distance"])] = t["name"]
RANKROLE = dict(collections.OrderedDict(sorted(RANKROLE.items())))
RANKNAME = dict(collections.OrderedDict(sorted(RANKNAME.items())))

divisions = config.divisions
divisionroles = []
for division in divisions:
    divisionroles.append(division["role_id"])

@app.get(f'/{config.vtc_abbr}/members')
async def getMembers(page:int, request: Request, response: Response, authorization: str = Header(None), \
    query: Optional[str] = '', pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /members', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()
    
    if page <= 0:
        page = 1

    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 250:
        pagelimit = 250

    query = query.replace("'","''").lower()
    
    cur.execute(f"SELECT userid, name, discordid, roles, avatar FROM user WHERE LOWER(name) LIKE '%{query}%' AND userid >= 0 ORDER BY userid ASC LIMIT {(page-1) * pagelimit}, {pagelimit}")
    t = cur.fetchall()
    ret = []
    for tt in t:
        roles = tt[3].split(",")
        while "" in roles:
            roles.remove("")
        highestrole = 99999
        for role in roles:
            if int(role) < highestrole:
                highestrole = int(role)
        ret.append({"userid": str(tt[0]), "name": tt[1], "discordid": f"{tt[2]}", "highestrole": str(highestrole), "avatar": tt[4]})
    
    cur.execute(f"SELECT COUNT(*) FROM user WHERE LOWER(name) LIKE '%{query}%' AND userid >= 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
    
    staff_of_the_month = {}
    driver_of_the_month = {}
    
    if "staff_of_the_month" in tconfig["perms"].keys() and len(tconfig["perms"]["staff_of_the_month"]) == 1:
        cur.execute(f"SELECT userid, name, discordid, avatar FROM user WHERE roles LIKE '%,{tconfig['perms']['staff_of_the_month'][0]},%'") # Staff of the month
        t = cur.fetchall()
        if len(t) > 0:
            tt = t[0]
            staff_of_the_month = {"userid": str(tt[0]), "name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[3]}

    if "driver_of_the_month" in tconfig["perms"].keys() and len(tconfig["perms"]["driver_of_the_month"]) == 1:
        cur.execute(f"SELECT userid, name, discordid, avatar FROM user WHERE roles LIKE '%,{tconfig['perms']['driver_of_the_month'][0]},%'") # Driver of the month
        t = cur.fetchall()
        if len(t) > 0:
            tt = t[0]
            driver_of_the_month = {"userid": str(tt[0]), "name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[3]}    

    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot), \
        "staff_of_the_month": staff_of_the_month, "driver_of_the_month": driver_of_the_month}}

@app.get(f'/{config.vtc_abbr}/member')
async def getMember(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /member', 30, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    roles = au["roles"]
    
    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True

    distance = 0
    totjobs = 0
    fuel = 0
    xp = 0
    eventpnt = 0
    cur.execute(f"SELECT * FROM driver WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) > 0:
        totjobs = t[0][1]
        distance = t[0][2]
        fuel = t[0][3]
        xp = t[0][4]
        eventpnt = t[0][5]

    europrofit = 0
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 1")
    t = cur.fetchall()
    if len(t) > 0:
        europrofit = t[0][0]
    if europrofit is None:
        europrofit = 0
    dollarprofit = 0
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 2")
    t = cur.fetchall()
    if len(t) > 0:
        dollarprofit = t[0][0]
    if dollarprofit is None:
        dollarprofit = 0
    profit = {"euro": str(europrofit), "dollar": str(dollarprofit)}
    
    if userid < 0:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "not_a_member")}

    if not isAdmin and not isHR:
        cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "member_not_found")}
        roles = t[0][3].split(",")
        while "" in roles:
            roles.remove("")
        roles = [int(i) for i in roles]
        divisionpnt = 0
        cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {userid} AND status = 1 AND logid >= 0 GROUP BY divisionid")
        o = cur.fetchall()
        for oo in o:
            if o[0][0] in DIVISIONPNT.keys():
                divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
        cur.execute(f"SELECT status FROM division WHERE userid = {userid} AND logid = -1")
        o = cur.fetchall()
        if len(o) > 0:
            divisionpnt += o[0][0]
        return {"error": False, "response": {"userid": str(userid), "name": t[0][1], "discordid": str(t[0][0]), "avatar": t[0][2], \
            "bio": b64d(t[0][7]), "roles": roles, "join": str(t[0][4]), "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
                "distance": str(distance), "totjobs": str(totjobs), "fuel": str(fuel), "xp": str(xp), "profit": profit, "eventpnt": str(eventpnt), "divisionpnt": str(divisionpnt)}}
    else:
        cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
            return {"error": True, "descriptor": ml.tr(request, "member_not_found")}
        roles = t[0][3].split(",")
        while "" in roles:
            roles.remove("")
        roles = [int(i) for i in roles]
        divisionpnt = 0
        cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {userid} AND status = 1 AND logid >= 0 GROUP BY divisionid")
        o = cur.fetchall()
        for oo in o:
            if o[0][0] in DIVISIONPNT.keys():
                divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
        cur.execute(f"SELECT status FROM division WHERE userid = {userid} AND logid = -1")
        o = cur.fetchall()
        if len(o) > 0:
            divisionpnt += o[0][0]
        return {"error": False, "response": {"userid": str(userid), "name": t[0][1], "email": t[0][8], \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "bio": b64d(t[0][7]), "roles": roles, "join": str(t[0][4]), \
                "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}",\
                    "distance": str(distance), "totjobs": str(totjobs), "fuel": str(fuel), "xp": str(xp), "profit": profit, "eventpnt": str(eventpnt), "divisionpnt": str(divisionpnt)}}

@app.post(f'/{config.vtc_abbr}/member/add')
async def addMember(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /member/add', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    discordid = int(form["discordid"])

    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "banned_user_cannot_be_accepted")}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtuserid'")
    t = cur.fetchall()
    userid = int(t[0][0])
    
    cur.execute(f"SELECT userid, truckersmpid, steamid, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
    if t[0][0] != -1:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "member_registered")}
    if t[0][2] <= 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "steam_not_bound")}
    if t[0][1] <= 0 and config.truckersmp_bind:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "truckersmp_not_bound")}

    name = t[0][3]
    cur.execute(f"UPDATE user SET userid = {userid}, joints = {int(time.time())} WHERE discordid = {discordid}")
    cur.execute(f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(adminid, f'Added member **{name}** (User ID `{userid}`) (Discord ID `{discordid}`)')
    conn.commit()

    try:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "member_update_title"), 
                "description": ml.tr(request, "member_update", var = {"vtcname": config.vtc_name}),
                    "fields": [{"name": "User ID", "value": f"{userid}", "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        pass

    return {"error": False, "response": {"userid": str(userid)}}    

@app.delete(f"/{config.vtc_abbr}/member/resign")
async def deleteMember(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /member/resign', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    name = au["name"].replace("'", "''")
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT steamid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    steamid = t[0][0]
    cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})

    await AuditLog(-999, f'Member resigned: **{name}** (`{discordid}`)')
    return {"error": False}

@app.delete(f"/{config.vtc_abbr}/member/dismiss")
async def dismissMember(userid: int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'DELETE /member/dismiss', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hr", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    adminid = au["userid"]
    adminroles = au["roles"]

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
        return {"error": True, "descriptor": ml.tr(request, "user_not_found")}
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
        return {"error": True, "descriptor": ml.tr(request, "user_position_higher_or_equal")}

    cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
    
    await AuditLog(adminid, f'Dismissed member: **{name}** (`{udiscordid}`)')
    return {"error": False}

@app.post(f'/{config.vtc_abbr}/member/role')
async def setMemberRole(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /member/role', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "division"])
    if au["error"]:
        response.status_code = 401
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
    userid = int(form["userid"])
    if userid < 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_userid")}
    roles = form["roles"].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    cur.execute(f"SELECT name, roles, steamid, discordid FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "member_not_found")}
    username = t[0][0]
    oldroles = t[0][1].split(",")
    steamid = t[0][2]
    discordid = t[0][3]
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
            return {"error": True, "descriptor": ml.tr(request, "add_role_higher_or_equal")}
    
    for remove in removedroles:
        if remove <= adminhighest:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "remove_role_higher_or_equal")}

    if len(addedroles) + len(removedroles) == 0:
        return {"error": False, "response": {"roles": roles}}
        
    if not isAdmin and not isHR and isDS:
        for add in addedroles:
            if add not in divisionroles:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        for remove in removedroles:
            if remove not in divisionroles:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    roles = [str(i) for i in roles]
    cur.execute(f"UPDATE user SET roles = ',{','.join(roles)},' WHERE userid = {userid}")

    if config.perms.driver[0] in addedroles:
        cur.execute(f"SELECT * FROM driver WHERE userid = {userid}")
        p = cur.fetchall()
        if len(p) == 0:
            cur.execute(f"INSERT INTO driver VALUES ({userid}, 0, 0, 0, 0, 0, {int(time.time())})")
            conn.commit()
        r = requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.navio_api_token})
        
        cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        userdiscordid = t[0][0]
        usermention = f"<@{userdiscordid}>"
        
        if config.webhook_teamupdate != "":
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(config.webhook_teamupdate, session=session)
                    embed = discord.Embed(title = "Team Update", description = config.webhook_teamupdate_message.replace("{mention}", usermention).replace("{vtcname}", config.vtc_name), color = config.rgbcolor)
                    embed.set_footer(text = f"{config.vtc_name} | Team Update", icon_url = config.vtc_logo_link)
                    if config.team_update_image_link != "":
                        embed.set_image(url = config.team_update_image_link)
                    embed.timestamp = datetime.now()
                    await webhook.send(content = usermention, embed=embed)
            except:
                pass
        
        if config.welcome_message != "":
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{config.welcome_channel_id}/messages"
            requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": "Welcome", "description": config.welcome_message.replace("{mention}", usermention).replace("{vtcname}", config.vtc_name), 
                    "footer": {"text": f"You are our #{userid} driver", "icon_url": config.vtc_logo_link}, "image": {"url": config.welcome_image_link},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}))
        
        if config.welcome_role_change != []:
            for role in config.welcome_role_change:
                if int(role) < 0:
                    requests.delete(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}"}, timeout = 1)
                elif int(role) > 0:
                    requests.put(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}"}, timeout = 1)

    if config.perms.driver[0] in removedroles:
        cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
        cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
        r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.navio_api_token})
    
    audit = f"Updated **{username}** (User ID `{userid}`) roles:\n"
    for add in addedroles:
        audit += f"**+** {ROLES[add]}\n"
    for remove in removedroles:
        audit += f"**-** {ROLES[remove]}\n"
    audit = audit[:-1].replace("'","''")
    await AuditLog(adminid, audit)
    conn.commit()

    return {"error": False, "response": {"roles": roles}}

@app.get(f"/{config.vtc_abbr}/member/roles")
async def getRoles(request: Request, response: Response):
    return {"error": False, "response": ROLES}

@app.get(f"/{config.vtc_abbr}/member/ranks")
async def getRanks(request: Request, response: Response):
    return {"error": False, "response": RANKS}

@app.get(f"/{config.vtc_abbr}/member/perms")
async def getRanks(request: Request, response: Response):
    return {"error": False, "response": config.perms}

@app.post(f"/{config.vtc_abbr}/member/point")
async def setMemberRole(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /member/point', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "hrm"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    userid = int(form["userid"])
    distance = int(int(form["distance"]))
    eventpnt = int(form["eventpnt"])
    divisionpnt = int(form["divisionpnt"])

    cur.execute(f"UPDATE driver SET distance = distance + {distance}, eventpnt = eventpnt + {eventpnt} WHERE userid = {userid}")
    
    divisionorg = 0
    cur.execute(f"SELECT status FROM division WHERE logid = -1 AND userid = {userid}")
    p = cur.fetchall()
    if len(p) > 0:
        divisionorg = p[0][0]
        cur.execute(f"DELETE FROM division WHERE logid = -1 AND userid = {userid}")
    divisionpnt += divisionorg
    if divisionpnt > 0:
        cur.execute(f"INSERT INTO division VALUES (-1, -1, {userid}, 0, {divisionpnt}, 0, 0, 0)")

    conn.commit()

    cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
    p = cur.fetchall()
    udiscordid = p[0][0]

    if int(distance) > 0:
        distance = "+" + form["distance"]
    if int(eventpnt) > 0:
        eventpnt = "+" + str(eventpnt)

    await AuditLog(adminid, f"Updated user #{userid} points:\n{distance} km\n{eventpnt} Event Points\n{divisionpnt} Division Points")

    return {"error": False}

@app.get(f"/{config.vtc_abbr}/member/steam")
async def memberSteam(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /member/steam', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT steamid, name, userid FROM user")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"steamid": str(tt[0]), "name": tt[1], "userid": str(tt[2])})
    return {"error": False, "response": {"list": ret}}

def point2rank(point):
    keys = list(RANKROLE.keys())
    for i in range(len(keys)):
        if point < keys[i]:
            return RANKROLE[keys[i-1]]
    return RANKROLE[keys[-1]]

@app.patch(f"/{config.vtc_abbr}/member/role/rank")
async def memberDiscordrole(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /member/role/rank', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()
    
    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371

    cur.execute(f"SELECT distance, eventpnt FROM driver WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "member_not_driver")}
    totalpnt = int(t[0][0] * ratio + t[0][1])
    divisionpnt = 0
    cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {userid} AND status = 1 AND logid >= 0 GROUP BY divisionid")
    o = cur.fetchall()
    for oo in o:
        if o[0][0] in DIVISIONPNT.keys():
            divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
    cur.execute(f"SELECT status FROM division WHERE userid = {userid} AND logid = -1")
    o = cur.fetchall()
    if len(o) > 0:
        divisionpnt += o[0][0]
    totalpnt += divisionpnt
    
    rank = point2rank(totalpnt)

    try:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        r=requests.get(f"https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3)
        d = json.loads(r.text)
        if "roles" in d:
            roles = d["roles"]
            curroles = []
            for role in roles:
                if int(role) in list(RANKROLE.values()):
                    curroles.append(int(role))
            if rank in curroles:
                response.status_code = 409
                return {"error": True, "descriptor": ml.tr(request, "already_have_discord_role")}
            else:
                requests.put(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{rank}', headers=headers, timeout = 3)
                for role in curroles:
                    requests.delete(f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3)
                
                if config.rank_up_channel_id != "" and config.rank_up_message != "":
                    try:
                        usermention = f"<@{discordid}>"
                        rankmention = f"<@&{rank}>"
                        msg = config.rank_up_message.replace("{mention}", usermention).replace("{rank}", rankmention)

                        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
                        ddurl = f"https://discord.com/api/v9/channels/{config.rank_up_channel_id}/messages"
                        r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": "Driver Rank Up", "description": msg, 
                                "footer": {"text": f"Congratulations!", "icon_url": config.vtc_logo_link},\
                                        "timestamp": str(datetime.now()), "color": config.intcolor}}))                       
                    except:
                        pass

                return {"error": False, "response": ml.tr(request, "discord_role_given")}
        else:
            response.status_code = 428
            return {"error": True, "descriptor": ml.tr(request, "not_in_discord_server")}

    except:
        pass