# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from datetime import datetime
from discord import Webhook, Embed
from aiohttp import ClientSession
import json, time, requests, math

from app import app, config
from db import newconn
from functions import *
import multilang as ml

application_types = config.application_types
for i in range(len(application_types)):
    application_types[i]["id"] = int(application_types[i]["id"])

# Basic Info
@app.get(f"/{config.abbr}/application/types")
async def getApplicationTypes(request: Request, response: Response):
    APPLICATIONS_TYPES = []
    for t in application_types:
        APPLICATIONS_TYPES.append({"applicationid": str(t["id"]), "name": t["name"]})
    return {"error": False, "response": APPLICATIONS_TYPES}

@app.get(f"/{config.abbr}/application/positions")
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

# Get Application
@app.get(f"/{config.abbr}/application")
async def getApplication(request: Request, response: Response, authorization: str = Header(None), applicationid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /application', 180, 90)
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

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}

    application_type = t[0][1]
    
    isAdmin = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True

    if not isAdmin and discordid != t[0][2]:
        ok = False
        for tt in application_types:
            if str(tt["id"]) == str(application_type):
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    
    cur.execute(f"SELECT name FROM user WHERE userid = {t[0][6]}")
    p = cur.fetchall()
    staff_name = "Unknown"
    if len(p) > 0:
        staff_name = p[0][0]

    return {"error": False, "response": {"applicationid": str(t[0][0]), "application_type": str(t[0][1]),\
        "discordid": str(t[0][2]), "detail": json.loads(decompress(t[0][3])), "status": str(t[0][4]), "submit_timestamp": str(t[0][5]), \
            "update_timestamp": str(t[0][7]), "last_update_staff": {"userid": str(t[0][6]), "name": staff_name}}}

@app.get(f"/{config.abbr}/application/list")
async def getApplications(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, page_size: Optional[int] = 10, application_type: Optional[int] = 0, \
        all_user: Optional[bool] = False, order: Optional[str] = "desc"):
    rl = ratelimit(request.client.host, 'GET /application/list', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if page <= 0:
        page = 1

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
        
    au = auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = 401
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    conn = newconn()
    cur = conn.cursor()

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    t = None
    tot = 0
    if all_user == False:
        limit = ""
        if application_type != 0:
            limit = f" AND application_type = {application_type}"

        cur.execute(f"SELECT applicationid, application_type, discordid, submit_timestamp, status, update_staff_timestamp FROM application WHERE discordid = {discordid} {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = cur.fetchall()
        
        cur.execute(f"SELECT COUNT(*) FROM application WHERE discordid = {discordid} {limit}")
        p = cur.fetchall()
        if len(t) > 0:
            tot = p[0][0]
    else:
        isAdmin = False
        for i in roles:
            if int(i) in config.perms.admin:
                isAdmin = True
        
        allowed_application_types = []
        if not isAdmin:
            for tt in application_types:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        allowed_application_types.append(str(tt["id"]))
                        break
        else:
            for tt in application_types:
                allowed_application_types.append(str(tt["id"]))

        if len(allowed_application_types) == 0:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        limit = ""
        if application_type == 0: # show all type
            limit = " WHERE "
            for tt in allowed_application_types:
                limit += f"application_type = {tt} OR "
            limit = limit[:-3]
        else:
            if not str(application_type) in allowed_application_types:
                response.status_code = 403
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
            limit = f" WHERE application_type = {application_type} "

        cur.execute(f"SELECT applicationid, application_type, discordid, submit_timestamp, status, update_staff_timestamp FROM application {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = cur.fetchall()
        
        cur.execute(f"SELECT COUNT(*) FROM application {limit}")
        p = cur.fetchall()
        if len(t) > 0:
            tot = p[0][0]

    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE discordid = {tt[2]}")
        p = cur.fetchall()
        name = "Unknown"
        if len(p) > 0:
            name = p[0][0]
        ret.append({"applicationid": str(tt[0]), "application_type": str(tt[1]), \
            "discordid": f"{tt[2]}", "name": name, \
                "status": str(tt[4]), "submit_timestamp": str(tt[3]), "update_timestamp": str(tt[5])})

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

# Self-operation
@app.post(f"/{config.abbr}/application")
async def postApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application', 180, 3)
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
    try:
        application_type = int(form["application_type"])
        data = json.loads(form["data"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    application_type_text = ""
    applicantrole = 0
    discord_message_content = ""
    webhookurl = ""
    note = ""
    for o in application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            applicantrole = o["discord_role_id"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
            note = o["note"]
    if application_type_text == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type")}

    if note == "driver":
        cur.execute(f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = cur.fetchall()
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        for r in config.perms.driver:
            if str(r) in roles:
                response.status_code = 409
                return {"error": True, "descriptor": ml.tr(request, "already_a_driver")}
        cur.execute(f"SELECT * FROM application WHERE application_type = 1 AND discordid = {discordid} AND status = 0")
        p = cur.fetchall()
        if len(p) > 0:
            response.status_code = 409
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application")}

    if note == "division":
        cur.execute(f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = cur.fetchall()
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for r in config.perms.driver:
            if str(r) in roles:
                ok = True
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "must_be_driver_to_submit_division_application")}        

    cur.execute(f"SELECT * FROM application WHERE discordid = {discordid} AND submit_timestamp >= {int(time.time()) - 7200}")
    p = cur.fetchall()
    if len(p) > 0:
        response.status_code = 429
        return {"error": True, "descriptor": ml.tr(request, "no_multiple_application_2h")}

    if userid == -1 and application_type == 3:
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

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {application_type}, {discordid}, '{compress(json.dumps(data))}', 0, {int(time.time())}, 0, 0)")
    conn.commit()

    if applicantrole != 0:
        durl = f'https://discord.com/api/v9/guilds/{config.guild_id}/members/{discordid}/roles/{applicantrole}'
        try:
            requests.put(durl, headers = {"Authorization": f"Bot {config.discord_bot_token}"})
        except:
            pass

    if config.discord_bot_dm:
        try:
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            durl = "https://discord.com/api/v9/users/@me/channels"
            r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
            d = json.loads(r.text)
            if "id" in d:
                channelid = d["id"]
                ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
                r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "bot_application_received_title", var = {"application_type_text": application_type_text}),
                    "description": ml.tr(request, "bot_application_received"),
                        "fields": [{"name": ml.tr(request, "application_id"), "value": applicationid, "inline": True}, {"name": ml.tr(request, "status"), "value": "Pending", "inline": True}, {"name": ml.tr(request, "creation"), "value": f"<t:{int(time.time())}>", "inline": True}],
                        "footer": {"text": config.name, "icon_url": config.logo_url}, "thumbnail": {"url": config.logo_url},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

        except:
            pass

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    for d in data.keys():
        msg += f"**{d}**:\n{data[d]}\n\n"

    if webhookurl != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = Embed(title = f"New {application_type_text} Application", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = Embed(title = f"New {application_type_text} Application", description = "*Message too long, please view application on website.*", color = config.rgbcolor)
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

@app.patch(f"/{config.abbr}/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application', 180, 10)
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
    try:
        applicationid = int(form["applicationid"])
        message = str(form["message"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}

    cur.execute(f"SELECT discordid, data, status, application_type FROM application WHERE applicationid = {applicationid}")
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
    application_type = t[0][3]
    i = 1
    while 1:
        if not f"[Message] {name} ({userid}) #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {name} ({userid}) #{i}"] = message

    cur.execute(f"UPDATE application SET data = '{compress(json.dumps(data))}' WHERE applicationid = {applicationid}")
    conn.commit()

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    msg += f"**New message**: \n{message}\n\n"

    if config.discord_bot_dm:
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
                        "footer": {"text": config.name, "icon_url": config.logo_url}, "thumbnail": {"url": config.logo_url},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

        except:
            pass

    application_type_text = ""
    discord_message_content = ""
    webhookurl = ""
    for o in application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
    if application_type < 1 and application_type > 4 and application_type_text == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type")}

    if webhookurl != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = Embed(title = f"Application #{applicationid} - New Message", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = Embed(title = f"Application #{applicationid} - New Message", description = "*Data too long, please view application on website.*", color = config.rgbcolor)
                    if t[0][1].startswith("a_"):
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                    else:
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                    embed.set_footer(text = f"Application ID: {applicationid} ")
                    embed.timestamp = datetime.now()
                    await webhook.send(content = discord_message_content, embed = embed)
            except:
                pass

    return {"error": False}

# Management
@app.patch(f"/{config.abbr}/application/status")
async def updateApplicationStatus(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application/status', 180, 30)
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

    form = await request.form()
    try:
        applicationid = int(form["applicationid"])
        status = int(form["status"])
        message = str(form["message"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    statustxt = f"Unknown Status ({status})"
    if int(status) in STATUS.keys():
        statustxt = STATUS[int(status)]

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}
    
    application_type = t[0][1]

    isAdmin = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True

    if not isAdmin:
        ok = False
        for tt in application_types:
            if str(tt["id"]) == str(application_type):
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    discordid = t[0][2]
    data = json.loads(decompress(t[0][3]))
    i = 1
    while 1:
        if not f"[Message] {adminname} ({adminid}) #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {adminname} ({adminid}) #{i}"] = message

    update_timestamp = 0
    if status != 0:
        update_timestamp = int(time.time())

    cur.execute(f"UPDATE application SET status = {status}, update_staff_userid = {adminid}, update_staff_timestamp = {update_timestamp}, data = '{compress(json.dumps(data))}' WHERE applicationid = {applicationid}")
    await AuditLog(adminid, f"Updated application {applicationid} status to {statustxt}")
    conn.commit()

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    if config.discord_bot_dm:
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
                r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "application_status_updated", force_en = True),
                    "description": f"[{ml.tr(request, 'message', force_en = True)}] {message}",
                        "fields": [{"name": ml.tr(request, "application_id", force_en = True), "value": applicationid, "inline": True}, {"name": ml.tr(request, "status", force_en = True), "value": statustxt, "inline": True}, \
                            {"name": ml.tr(request, "time", force_en = True), "value": f"<t:{int(time.time())}>", "inline": True}, {"name": ml.tr(request, "responsible_staff", force_en = True), "value": f"<@{admindiscord}> (`{admindiscord}`)", "inline": True}],
                        "footer": {"text": config.name, "icon_url": config.logo_url}, "thumbnail": {"url": config.logo_url},\
                            "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

        except:
            pass

    return {"error": False}

# Higher-management
@app.patch(f"/{config.abbr}/application/positions")
async def patchApplicationPositions(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application/positions', 180, 3)
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

    return {"error": False}