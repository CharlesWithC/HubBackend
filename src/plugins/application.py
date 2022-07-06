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

@app.post(f"/{config.vtcprefix}/application")
async def newApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application', 60, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if iptype(ip) == "ipv6":
            orgiptype = 6
        curiptype = 4
        if iptype(request.client.host) == "ipv6":
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    form = await request.form()
    apptype = int(form["apptype"])
    data = json.loads(form["data"])
    data = b64e(json.dumps(data))

    cur.execute(f"SELECT userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    userid = t[0][0]

    if apptype == 1:
        cur.execute(f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = cur.fetchall()
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        for r in config.perms.driver:
            if str(r) in roles:
                return {"error": True, "descriptor": ml.tr(request, "already_a_driver")}
        cur.execute(f"SELECT * FROM application WHERE apptype = 1 AND discordid = {discordid} AND status = 0")
        p = cur.fetchall()
        if len(p) > 0:
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application")}
    if apptype == 4:
        cur.execute(f"SELECT * FROM application WHERE apptype = 4 AND discordid = {discordid} AND status = 0")
        p = cur.fetchall()
        if len(p) > 0:
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application")}

    cur.execute(f"SELECT * FROM application WHERE discordid = {discordid} AND submitTimestamp >= {int(time.time()) - 7200}")
    p = cur.fetchall()
    if len(p) > 0:
        return {"error": True, "descriptor": ml.tr(request, "no_multiple_application_2h")}

    if userid == -1 and apptype == 3:
        return {"error": True, "descriptor": ml.tr(request, "no_loa_application")}

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if t[0][4] <= 0:
        return {"error": True, "descriptor": ml.tr(request, "must_verify_steam")}
    if t[0][3] <= 0 and config.truckersmp_bind:
        return {"error": True, "descriptor": ml.tr(request, "must_verify_truckersmp")}
    userid = t[0][5]

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtappid'")
    t = cur.fetchall()
    applicationid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {applicationid+1} WHERE skey = 'nxtappid'")
    conn.commit()

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {apptype}, {discordid}, '{data}', 0, {int(time.time())}, 0, 0)")
    conn.commit()

    data = json.loads(form["data"])
    apptype = int(apptype)
    APPTYPE = {0: ml.tr(request, "unknown"), 1: ml.tr(request, "driver"), 2: ml.tr(request, "staff"), 3: ml.tr(request, "loa"), 4: ml.tr(request, "division")}
    apptypetxt = ml.tr(request, "unknown")
    if apptype in APPTYPE.keys():
        apptypetxt = APPTYPE[apptype]

    if config.assign_application_role:
        durl = ""
        if apptype == 1:
            durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.applicant_driver}'
        elif apptype == 2:
            durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.applicant_staff}'
        elif apptype == 3:
            durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.loa_request}'
        if durl != "":
            try:
                requests.put(durl, headers = {"Authorization": f"Bot {config.bot_token}"})
            except:
                pass

    try:
        headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "bot_application_received_title", var = {"apptypetxt": apptypetxt}),
                "description": ml.tr(request, "bot_application_received"),
                    "fields": [{"name": ml.tr(request, "application_id"), "value": applicationid, "inline": True}, {"name": ml.tr(request, "status"), "value": "Pending", "inline": True}, {"name": ml.tr(request, "creation"), "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtcname, "icon_url": config.vtclogo}, "thumbnail": {"url": config.vtclogo},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        pass

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    for d in data.keys():
        msg += f"**{d}**: {data[d]}\n\n"

    pingroles = config.human_resources_role
    webhookurl = config.webhook_application
    if apptype == 4:
        pingroles = config.division_manager_role
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
                await webhook.send(content = pingroles, embed = embed)

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
                    await webhook.send(content = pingroles, embed = embed)
            except:
                pass

    return {"error": False, "response": {"applicationid": applicationid}}

@app.patch(f"/{config.vtcprefix}/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /application', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if iptype(ip) == "ipv6":
            orgiptype = 6
        curiptype = 4
        if iptype(request.client.host) == "ipv6":
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT name, userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    name = t[0][0]
    userid = t[0][1]

    form = await request.form()
    applicationid = form["applicationid"]
    message = form["message"]

    cur.execute(f"SELECT discordid, data, status, apptype FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if discordid != t[0][0]:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "not_applicant")}
    if t[0][2] != 0:
        # 
        if t[0][2] == 1:
            return {"error": True, "descriptor": ml.tr(request, "application_already_accepted")}
        elif t[0][2] == 2:
            return {"error": True, "descriptor": ml.tr(request, "application_already_declined")}
        else:
            return {"error": True, "descriptor": ml.tr(request, "application_already_processed")}

    discordid = t[0][0]
    data = json.loads(b64d(t[0][1]))
    apptype = t[0][3]
    i = 1
    while 1:
        if not f"[Message] {name} #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {name} #{i}"] = message
    data = b64e(json.dumps(data))

    cur.execute(f"UPDATE application SET data = '{data}' WHERE applicationid = {applicationid}")
    conn.commit()

    data = json.loads(b64d(data))
    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    msg += f"**New message**: {message}\n\n"

    try:
        headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": ml.tr(request, "application_updated"),
                "description": ml.tr(request, "application_message_recorded"),
                    "fields": [{"name": "Application ID", "value": applicationid, "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Creation", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": config.vtcname, "icon_url": config.vtclogo}, "thumbnail": {"url": config.vtclogo},\
                         "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        pass

    pingroles = config.human_resources_role
    webhookurl = config.webhook_application
    if apptype == 4:
        pingroles = config.division_manager_role
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
                await webhook.send(content = pingroles, embed = embed)

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
                    await webhook.send(content = pingroles, embed = embed)
            except:
                pass

    return {"error": False, "response": {"applicationid": applicationid}}

@app.post(f"/{config.vtcprefix}/application/status")
async def updateApplicationStatus(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application/status', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles,name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminid = t[0][0]
    roles = t[0][1].split(",")
    adminname = t[0][2]
    admindiscord = discordid
    while "" in roles:
        roles.remove("")

    ok = False
    isAdmin = False
    isHR = False
    isDS = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True
        if int(i) in config.perms.admin or int(i) in config.perms.hr or int(i) in config.perms.division:
            ok = True

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
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}
    
    apptype = t[0][1]

    if not isAdmin:
        if apptype == 4:
            if not isDS:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        else:
            if not isHR:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    discordid = t[0][2]
    data = json.loads(b64d(t[0][3]))
    i = 1
    while 1:
        if not f"[Message] {adminname} #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {adminname} #{i}"] = message
    data = b64e(json.dumps(data))

    closedts = 0
    if status != 0:
        closedts = int(time.time())

    cur.execute(f"UPDATE application SET status = {status}, closedBy = {adminid}, closedTimestamp = {closedts}, data = '{data}' WHERE applicationid = {applicationid}")
    await AuditLog(adminid, f"Updated application {applicationid} status to {statustxt}")
    conn.commit()

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    try:
        STATUS = {0: "Pending", 1: "Accepted", 2: "Declined"}
        statustxt = f"Unknown Status ({status})"
        if int(status) in STATUS.keys():
            statustxt = STATUS[int(status)]
        headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
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
                    "footer": {"text": config.vtcname, "icon_url": config.vtclogo}, "thumbnail": {"url": config.vtclogo},\
                        "timestamp": str(datetime.now()), "color": config.intcolor}}), timeout=3)

    except:
        import traceback
        traceback.print_exc()
        pass

    return {"error": False, "response": {"applicationid": applicationid, "status": status}}

@app.get(f"/{config.vtcprefix}/application")
async def getApplication(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /application', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if iptype(ip) == "ipv6":
            orgiptype = 6
        curiptype = 4
        if iptype(request.client.host) == "ipv6":
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    userid = t[0][0]
    roles = t[0][1].split(",")
    while "" in roles:
        roles.remove("")
    ok = False
    isAdmin = False
    isHR = False
    isDS = False
    if len(t) > 0:
        for i in roles:
            if int(i) in config.perms.admin:
                isAdmin = True
            if int(i) in config.perms.hr:
                isHR = True
            if int(i) in config.perms.division:
                isDS = True
            if int(i) in config.perms.admin or int(i) in config.perms.hr or int(i) in config.perms.division:
                ok = True

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": ml.tr(request, "application_not_found")}
    
    if not isAdmin and discordid != t[0][2]:
        if t[0][1] == 4:
            if not isDS:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        else:
            if not isHR:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    return {"error": False, "response": {"applicationid": t[0][0], "apptype": t[0][1],\
        "discordid": str(t[0][2]), "data": json.loads(b64d(t[0][3])), "status": t[0][4], "submitTimestamp": t[0][5], \
            "closedTimestamp": t[0][7], "closedBy": t[0][6]}}

@app.get(f"/{config.vtcprefix}/application/list")
async def getApplicationList(page: int, apptype: int, request: Request, response: Response, authorization: str = Header(None), showall: Optional[bool] = False):
    rl = ratelimit(request.client.host, 'GET /application/list', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if page <= 0:
        page = 1
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if iptype(ip) == "ipv6":
            orgiptype = 6
        curiptype = 4
        if iptype(request.client.host) == "ipv6":
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    if isapptoken and showall:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    userid = t[0][0]
    roles = t[0][1].split(",")
    while "" in roles:
        roles.remove("")
    ok = False
    isAdmin = False
    isHR = False
    isDS = False
    if len(t) > 0:
        for i in roles:
            if int(i) in config.perms.admin:
                isAdmin = True
            if int(i) in config.perms.hr:
                isHR = True
            if int(i) in config.perms.division:
                isDS = True
            if int(i) in config.perms.admin or int(i) in config.perms.hr or int(i) in config.perms.division:
                ok = True

    t = None
    tot = 0
    if showall == False:
        limit = ""
        if apptype != 0:
            limit = f" AND apptype = {apptype}"

        cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application WHERE discordid = {discordid} {limit} ORDER BY applicationid DESC LIMIT {(page-1) * 10}, 10")
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
            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * 10}, 10")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
            
        elif isHR and not isDS:
            if apptype == 4:
                response.status_code = 401
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

            limit = " WHERE apptype != 4"
            if apptype != 0:
                limit = f" WHERE apptype = {apptype}"

            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * 10}, 10")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
                
        elif not isHR and isDS:
            limit = " WHERE apptype = 4"

            cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * 10}, 10")
            t = cur.fetchall()
            
            cur.execute(f"SELECT COUNT(*) FROM application {limit}")
            p = cur.fetchall()
            if len(t) > 0:
                tot = p[0][0]
        
        else:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE discordid = {tt[2]}")
        p = cur.fetchall()
        name = "Unknown"
        if len(p) > 0:
            name = p[0][0]
        ret.append({"applicationid": tt[0], "apptype": tt[1], "discordid": f"{tt[2]}", "name": name, "status": tt[4], "submitTimestamp": tt[3], "closedTimestamp": tt[5]})

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get(f"/{config.vtcprefix}/application/positions")
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

@app.post(f"/{config.vtcprefix}/application/positions")
async def setApplicationPositions(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /application/positions', 60, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminid = t[0][0]
    roles = t[0][1].split(",")
    while "" in roles:
        roles.remove("")

    isAdmin = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True

    if not isAdmin:
        response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

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