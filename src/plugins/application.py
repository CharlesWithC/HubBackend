# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math
from datetime import datetime
import discord
from discord import Webhook
import aiohttp, requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

application_types = config.application_types
for i in range(len(application_types)):
    application_types[i]["id"] = int(application_types[i]["id"])

@app.get(f"/{config.vtc_abbr}/application/types")
async def getApplicationTypes(request: Request, response: Response):
    APPLICATIONS_TYPES = []
    for t in application_types:
        APPLICATIONS_TYPES.append({"id": t["id"], "name": t["name"]})
    return {"error": False, "response": APPLICATIONS_TYPES}

@app.post(f"/{config.vtc_abbr}/application")
async def newApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    apptype = int(form["apptype"])
    data = json.loads(form["data"])

    if apptype == 1:
        cur.execute(f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = cur.fetchall()
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        for r in config.perms.driver:
            if str(r) in roles:
                response.status_code = 409
                return {"error": True, "descriptor": ml.tr(request, "already_a_driver")}
        cur.execute(f"SELECT * FROM application WHERE apptype = 1 AND discordid = {discordid} AND status = 0")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 409
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application")}
    if apptype == 4:
        cur.execute(f"SELECT * FROM application WHERE apptype = 4 AND discordid = {discordid} AND status = 0")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 409
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application")}

    cur.execute(f"SELECT * FROM application WHERE discordid = {discordid} AND submitTimestamp >= {int(time.time()) - 7200}")
    p = cur.fetchall()
    if len(p) > 0:
        response.status_code = 429
        return {"error": True, "descriptor": ml.tr(request, "no_multiple_application_2h")}

    if userid == -1 and apptype == 3:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "no_loa_application")}

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if t[0][4] <= 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "must_verify_steam")}
    if t[0][3] <= 0 and config.truckersmp_bind:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "must_verify_truckersmp")}
    userid = t[0][5]

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtappid'")
    t = cur.fetchall()
    applicationid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {applicationid+1} WHERE skey = 'nxtappid'")
    conn.commit()

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {apptype}, {discordid}, '{compress(json.dumps(data))}', 0, {int(time.time())}, 0, 0)")
    conn.commit()

    apptype = int(apptype)

    apptypetxt = ""
    applicantrole = 0
    discord_message_content = ""
    for o in application_types:
        if apptype == o["id"]:
            apptypetxt = o["name"]
            applicantrole = o["discord_role_id"]
            discord_message_content = o["message"]
    if apptype < 1 and apptype > 4 and apptypetxt == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type")}
    if apptype >= 1 and apptype <= 4:
        APPTYPE = {1: ml.tr(request, "driver"), 2: ml.tr(request, "staff"), 3: ml.tr(request, "loa"), 4: ml.tr(request, "division")}
        apptypetxt = APPTYPE[apptype]

    if applicantrole != 0:
        durl = f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{applicantrole}'
        try:
            requests.put(durl, headers = {"Authorization": f"Bot {config.discord_bot_token}"})
        except:
            pass

    try:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "bot_application_received_title", var = {"apptypetxt": apptypetxt}),
                "description": ml.tr(request, "bot_application_received"),
                    "fields": [{"name": ml.tr(request, "application_id"), "value": applicationid, "inline": True}, {"name": ml.tr(request, "status"), "value": "Pending", "inline": True}, {"name": ml.tr(request, "creation"), "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        pass

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    for d in data.keys():
        msg += f"**{d}**: {data[d]}\n\n"

    webhookurl = config.webhook_application
    if apptype == 4:
        webhookurl = config.webhook_division
    if webhookurl != "":
        try:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = discord.Embed(title = f"New {apptypetxt} Application", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = discord.Embed(title = f"New {apptypetxt} Application", description = "*Message too long, please view application on website.*", color = config.rgbcolor)
                    if t[0][1].startswith("a_"):
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                    else:
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                    embed.set_footer(text = f"Application ID: {applicationid} ")
                    embed.timestamp = datetime.now()
                    await webhook.send(content = discord_message_content, embed = embed)
            except:
                pass

    return {"error": False, "response": {"applicationid": str(applicationid)}}

@app.patch(f"/{config.vtc_abbr}/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    name = au["name"]

    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    applicationid = form["applicationid"]
    message = form["message"]

    cur.execute(f"SELECT discordid, data, status, apptype FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if discordid != t[0][0]:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "not_applicant")}
    if t[0][2] != 0:
        response.status_code = 409
        if t[0][2] == 1:
            return {"error": True, "descriptor": ml.tr(request, "application_already_accepted")}
        elif t[0][2] == 2:
            return {"error": True, "descriptor": ml.tr(request, "application_already_declined")}
        else:
            return {"error": True, "descriptor": ml.tr(request, "application_already_processed")}

    discordid = t[0][0]
    data = json.loads(decompress(t[0][1]))
    apptype = t[0][3]
    i = 1
    while 1:
        if not f"[Message] {name} #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {name} #{i}"] = message

    cur.execute(f"UPDATE application SET data = '{compress(json.dumps(data))}' WHERE applicationid = {applicationid}")
    conn.commit()

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    msg += f"**New message**: {message}\n\n"

    try:
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "application_updated"),
                "description": ml.tr(request, "application_message_recorded"),
                    "fields": [{"name": "Application ID", "value": applicationid, "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Creation", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        pass

    apptypetxt = ""
    discord_message_content = ""
    for o in application_types:
        if apptype == o["id"]:
            apptypetxt = o["name"]
            discord_message_content = o["message"]
    if apptype < 1 and apptype > 4 and apptypetxt == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type")}

    webhookurl = config.webhook_application
    if apptype == 4:
        webhookurl = config.webhook_division
    if webhookurl != "":
        try:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = discord.Embed(title = f"Application #{applicationid} - New Message", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with aiohttp.ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = discord.Embed(title = f"Application #{applicationid} - New Message", description = "*Data too long, please view application on website.*", color = config.rgbcolor)
                    if t[0][1].startswith("a_"):
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                    else:
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                    embed.set_footer(text = f"Application ID: {applicationid} ")
                    embed.timestamp = datetime.now()
                    await webhook.send(content = discord_message_content, embed = embed)
            except:
                pass

    return {"error": False, "response": {"applicationid": str(applicationid)}}

@app.patch(f"/{config.vtc_abbr}/application/status")
async def updateApplicationStatus(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application/status', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    admindiscord = au["discordid"]
    adminid = au["userid"]
    adminname = au["name"]
    roles = au["roles"]

    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    isDS = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True

    form = await request.form()
    applicationid = form["applicationid"]
    status = form["status"]
    message = form["message"]
    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    statustxt = f"Unknown Status ({status})"
    if int(status) in STATUS.keys():
        statustxt = STATUS[int(status)]

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}
    
    apptype = t[0][1]

    if not isAdmin:
        if apptype == 4:
            if not isDS:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        else:
            if not isHR:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    discordid = t[0][2]
    data = json.loads(decompress(t[0][3]))
    i = 1
    while 1:
        if not f"[Message] {adminname} #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {adminname} #{i}"] = message

    closedts = 0
    if status != 0:
        closedts = int(time.time())

    cur.execute(f"UPDATE application SET status = {status}, closedBy = {adminid}, closedTimestamp = {closedts}, data = '{compress(json.dumps(data))}' WHERE applicationid = {applicationid}")
    await AuditLog(adminid, f"Updated application {applicationid} status to {statustxt}")
    conn.commit()

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    try:
        STATUS = {0: "Pending", 1: "Accepted", 2: "Declined"}
        statustxt = f"Unknown Status ({status})"
        if int(status) in STATUS.keys():
            statustxt = STATUS[int(status)]
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "application_status_updated"),
                "description": f"[{ml.tr(request, 'message')}] {message}",
                    "fields": [{"name": ml.tr(request, "application_id"), "value": applicationid, "inline": True}, {"name": ml.tr(request, "status"), "value": statustxt, "inline": True}, \
                        {"name": ml.tr(request, "time"), "value": f"<t:{int(time.time())}>", "inline": True}, {"name": ml.tr(request, "responsible_staff"), "value": f"<@{admindiscord}> (`{admindiscord}`)", "inline": True}],
                    "footer": {"text": config.vtc_name, "icon_url": config.vtc_logo_link}, "thumbnail": {"url": config.vtc_logo_link},\
                        "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        import traceback
        traceback.print_exc()
        pass

    return {"error": False, "response": {"applicationid": str(applicationid), "status": str(status)}}

@app.get(f"/{config.vtc_abbr}/application")
async def getApplication(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /application', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    isDS = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}
    
    if not isAdmin and discordid != t[0][2]:
        if t[0][1] == 4:
            if not isDS:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        else:
            if not isHR:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    return {"error": False, "response": {"applicationid": str(t[0][0]), "apptype": str(t[0][1]),\
        "discordid": str(t[0][2]), "detail": json.loads(decompress(t[0][3])), "status": str(t[0][4]), "submitTimestamp": str(t[0][5]), \
            "closedTimestamp": str(t[0][7]), "closedBy": str(t[0][6])}}

@app.get(f"/{config.vtc_abbr}/applications")
async def getApplications(page: int, apptype: int, request: Request, response: Response, authorization: str = Header(None), \
    showall: Optional[bool] = False, pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /applications', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if page <= 0:
        page = 1
        
    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    conn = newconn()
    cur = conn.cursor()

    isAdmin = False
    isHR = False
    isDS = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True

    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 100:
        pagelimit = 100

    t = None
    tot = 0
    if showall == False:
        limit = ""
        if apptype != 0:
            limit = f" AND apptype = {apptype}"

        cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application WHERE discordid = {discordid} {limit} ORDER BY applicationid DESC LIMIT {(page-1) * pagelimit}, {pagelimit}")
        t = cur.fetchall()
        
        cur.execute(f"SELECT COUNT(*) FROM application WHERE discordid = {discordid} {limit}")
        p = cur.fetchall()
        if len(t) > 0:
            tot = p[0][0]
    else:
        if isAdmin or isHR and isDS:
            limit = ""
            if apptype != 0:
                limit = f" WHERE apptype = {apptype}"
            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * pagelimit}, {pagelimit}")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
            
        elif isHR and not isDS:
            if apptype == 4:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

            limit = " WHERE apptype != 4"
            if apptype != 0:
                limit = f" WHERE apptype = {apptype}"

            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * pagelimit}, {pagelimit}")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
                
        elif not isHR and isDS:
            limit = " WHERE apptype = 4"

            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * pagelimit}, {pagelimit}")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
        
        else:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE discordid = {tt[2]}")
        p = cur.fetchall()
        name = "Unknown"
        if len(p) > 0:
            name = p[0][0]
        ret.append({"applicationid": str(tt[0]), "apptype": str(tt[1]), \
            "discordid": f"{tt[2]}", "name": name, \
                "status": str(tt[4]), "submitTimestamp": str(tt[3]), "closedTimestamp": str(tt[5])})

    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot)}}

@app.get(f"/{config.vtc_abbr}/application/positions")
async def getApplicationPositions(request: Request, response: Response):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": False, "response": []}
    else:
        ret = []
        for tt in t[0][0].split(","):
            ret.append(tt)
        return {"error": False, "response": ret}

@app.post(f"/{config.vtc_abbr}/application/positions")
async def setApplicationPositions(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application/positions', 60, 10)
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
    positions = form["positions"].replace("'", "''")

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO settings VALUES (0, 'applicationpositions', '{positions}')")
    else:
        cur.execute(f"UPDATE settings SET sval = '{positions}' WHERE skey = 'applicationpositions'")
    conn.commit()

    await AuditLog(adminid, f"Updated open staff positions to: {positions}")

    return {"error": False, "response": {"positions": positions}}