# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from discord import Webhook, Embed
from datetime import datetime
from aiohttp import ClientSession
import json, time, requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

divisions = config.divisions
divisionsGET = divisions
for i in range(len(divisions)):
    try:
        divisions[i]["id"] = int(divisions[i]["id"])
        divisionsGET[i]["id"] = str(divisions[i]["id"])
    except:
        pass
    
divisionroles = []
divisiontxt = {}
for division in divisions:
    try:
        divisionroles.append(int(division["role_id"]))
        divisiontxt[int(division["id"])] = division["name"]
    except:
        pass

DIVISIONPNT = {}
for division in divisions:
    try:
        DIVISIONPNT[int(division["id"])] = int(division["point"])
    except:
        pass

# Basic info
@app.get(f"/{config.vtc_abbr}/division/list")
async def getDivisions(request: Request, response: Response):
    return {"error": False, "response": divisionsGET}

# Get division info
@app.get(f"/{config.vtc_abbr}/division")
async def getDivision(request: Request, response: Response, authorization: str = Header(None), logid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /division', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]
        
    conn = newconn()
    cur = conn.cursor()

    if logid != -1:
        cur.execute(f"SELECT divisionid, userid, request_timestamp, status, update_timestamp, update_staff_userid, message FROM division WHERE logid = {logid} AND logid >= 0")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
            t = cur.fetchall()
            if len(t) == 0:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}
            duserid = t[0][0]
            if duserid != userid:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}
            else:
                return {"error": False, "response": {"status": "-1"}}
        tt = t[0]
        divisionid = tt[0]
        duserid = tt[1]
        request_timestamp = tt[2]
        status = tt[3]
        update_timestamp = tt[4]
        update_staff_userid = tt[5]
        message = b64d(tt[6])

        ok = False
        for i in roles:
            if int(i) in config.perms.admin or int(i) in config.perms.division:
                ok = True

        if not ok:
            if userid != duserid and status != 1:
                response.status_code = 404
                return {"error": True, "descriptor": ml.tr(request, "division_not_validated")}

        staffname = "/"
        if update_staff_userid != -1:
            cur.execute(f"SELECT name FROM user WHERE userid = {update_staff_userid}")
            t = cur.fetchall()
            staffname = t[0][0]
        if userid == duserid:
            return {"error": False, "response": {"divisionid": str(divisionid), "request_timestamp": str(request_timestamp), "status": str(status), \
                "update_timestamp": str(update_timestamp), "update_staff": {"userid": str(update_staff_userid), "name": staffname}, "message": message, "user_is_staff": ok}}
        else:
            return {"error": False, "response": {"divisionid": str(divisionid), "status": str(status), \
                "update_timestamp": str(update_timestamp), "update_staff": {"userid": str(update_staff_userid), "name": staffname}, "user_is_staff": ok}}

    stats = []
    for division in divisions:
        tstats = []
        cur.execute(f"SELECT name, userid FROM user WHERE roles LIKE '%,{division['role_id']},%'")
        t = cur.fetchall()
        userpnt = {}
        username = {}
        for tt in t:
            divisionpnt = 0
            cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {tt[1]} AND status = 1 AND logid >= 0 GROUP BY divisionid, userid")
            o = cur.fetchall()
            for oo in o:
                if o[0][0] in DIVISIONPNT.keys():
                    divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
            username[tt[1]] = tt[0]
            userpnt[tt[1]] = divisionpnt
        userpnt = dict(sorted(userpnt.items(), key=lambda item: item[1]))
        for uid in userpnt.keys():
            tstats.append({"userid": str(uid), "name": username[uid], "points": str(userpnt[uid])})
        stats.append({"divisionid": str(division['id']), "name": division['name'], "drivers": tstats[::-1]})
    
    delivery = []
    cur.execute(f"SELECT logid FROM division WHERE status = 1 AND logid >= 0 ORDER BY update_timestamp DESC LIMIT 10")
    p = cur.fetchall()
    for pp in p:
        cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit, distance FROM dlog WHERE logid = {pp[0]}")
        t = cur.fetchall()
        tt = t[0]
        data = json.loads(decompress(tt[1]))
        source_city = "Unknown city"
        source_company = "Unknown company"
        destination_city = "Unknown city"
        destination_company = "Unknown company"
        if data["data"]["object"]["source_city"] != None:
            source_city = data["data"]["object"]["source_city"]["name"]
        if data["data"]["object"]["source_company"] != None:
            source_company = data["data"]["object"]["source_company"]["name"]
        if data["data"]["object"]["destination_city"] != None:
            destination_city = data["data"]["object"]["destination_city"]["name"]
        if data["data"]["object"]["destination_company"] != None:
            destination_company = data["data"]["object"]["destination_company"]["name"]
        cargo = data["data"]["object"]["cargo"]["name"]
        cargo_mass = data["data"]["object"]["cargo"]["mass"]
        distance = tt[6]
        if distance < 0:
            distance = 0

        profit = tt[4]
        unit = tt[5]

        name = "Unknown"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) > 0:
            name = p[0][0]

        delivery.append({"logid": str(tt[3]), "userid": str(tt[0]), "name": name, "distance": str(distance), \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": str(cargo_mass), "profit": str(profit), "unit": str(unit), "timestamp": str(tt[2])})
    
    return {"error": False, "response": {"statistics": stats, "recent": delivery}}

# Self-operation
@app.post(f"/{config.vtc_abbr}/division")
async def postDivision(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /division', 180, 3)
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

    form = await request.form()
    try:
        logid = int(form["logid"])
        divisionid = int(form["divisionid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "delivery_log_not_found")}
    luserid = t[0][0]
    if userid != luserid:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    cur.execute(f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 409
        status = t[0][0]
        if status == 0:
            return {"error": True, "descriptor": ml.tr(request, "division_already_requested")}
        elif status == 1:
            return {"error": True, "descriptor": ml.tr(request, "division_already_validated")}
        elif status == 2:
            return {"error": True, "descriptor": ml.tr(request, "division_already_denied")}
    
    cur.execute(f"SELECT roles FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    while "" in roles:
        roles.remove("")
    udivisions = []
    for role in roles:
        if int(role) in divisionroles:
            for division in divisions:
                try:
                    if int(division["role_id"]) == int(role):
                        udivisions.append(int(division["id"]))
                except:
                    pass
    if not divisionid in udivisions:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "not_division_driver")}
    
    cur.execute(f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    conn.commit()
    
    try:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Division Validation Request for Delivery #{logid} Received",
                "description": f"Division supervisor will check your request and you will receive an update soon.",
                    "fields": [{"name": "Division", "value": divisiontxt[divisionid], "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)
    except:
        pass

    dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
    cur.execute(f"SELECT userid, name, avatar FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    tt = t[0]
    msg = f"**User ID**: {tt[0]}\n**Name**: {tt[1]}\n**Discord**: <@{discordid}> (`{discordid}`)\n\n"
    msg += f"**Delivery ID**: [{logid}]({dlglink})\n**Division**: {divisiontxt[divisionid]}"
    avatar = tt[2]

    if config.webhook_division != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_division, session=session)

                embed = Embed(title = f"New Division Validation Request for Delivery #{logid}", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif")
                else:
                    embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png")
                embed.set_footer(text = f"Delivery ID: {logid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = config.webhook_division_message, embed = embed)
        except:
            pass
        
    return {"error": False}

@app.get(f"/{config.vtc_abbr}/division/list/pending")
async def getDivisionsPending(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /division/list/pending', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = 401
        return au
        
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT logid, userid, divisionid FROM division WHERE status = 0 AND logid >= 0")
    t = cur.fetchall()
    ret = []
    for tt in t:
        name = "Unknown"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[1]}")
        ttt = cur.fetchall()
        if len(ttt) > 0:
            name = ttt[0][0]
        ret.append({"logid": str(tt[0]), "divisionid": str(tt[2]), "userid": str(tt[1]), "name": name})
    
    return {"error": False, "response": ret}

@app.patch(f"/{config.vtc_abbr}/division")
async def patchDivision(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /division', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "division"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    try:
        logid = int(form["logid"])
        divisionid = int(form["divisionid"])
        message = str(form["message"])
        status = int(form["status"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    
    cur.execute(f"SELECT divisionid, status FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "division_validation_not_found")}
    if divisionid == 0:
        divisionid = t[0][0]
        
    cur.execute(f"UPDATE division SET divisionid = {divisionid}, status = {status}, update_staff_userid = {adminid}, update_timestamp = {int(time.time())}, message = '{b64e(message)}' WHERE logid = {logid}")
    conn.commit()

    STATUS = {0: "pending", 1: "validated", 2: "denied"}
    await AuditLog(adminid, f"Updated division validation request for delivery #{logid} to {STATUS[status]}")

    cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    userid = t[0][0]
    cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    discordid = t[0][0]
    cur.execute(f"SELECT discordid FROM user WHERE userid = {adminid}")
    t = cur.fetchall()
    adiscordid = t[0][0]

    try:
        STATUS = {0: "Pending", 1: "Validated", 2: "Denied"}
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Division Validation Request for Delivery #{logid} Updated",
                "description": message,
                    "fields": [{"name": "Division", "value": divisiontxt[divisionid], "inline": True}, {"name": "Status", "value": STATUS[status], "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True},\
                        {"name": "Division Supervisor", "value": f"<@{adiscordid}> (`{adiscordid}`)", "inline": False}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)
    except:
        pass

    return {"error": False}