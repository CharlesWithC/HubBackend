# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math, validators
from datetime import datetime
import discord
from discord import Webhook
import aiohttp, requests

from app import app, config
from db import newconn
from functions import *

@app.post("/atm/application")
async def newApplication(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    apptype = int(form["apptype"])
    data = json.loads(form["data"])
    data = b64e(json.dumps(data))

    cur.execute(f"SELECT userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    userid = t[0][0]

    if apptype == 1:
        cur.execute(f"SELECT * FROM driver WHERE userid = {userid}")
        p = cur.fetchall()
        if len(p) > 0:
            return {"error": True, "descriptor": "You are already a driver!"}
        cur.execute(f"SELECT * FROM application WHERE apptype = 1 AND discordid = {discordid}")
        p = cur.fetchall()
        if len(p) > 0:
            return {"error": True, "descriptor": "You have already made a driver application! Use 'Add Message' instead of creating new application!"}
    
    cur.execute(f"SELECT * FROM application WHERE discordid = {discordid} AND submitTimestamp >= {int(time.time()) - 7200}")
    p = cur.fetchall()
    if len(p) > 0:
        return {"error": True, "descriptor": "You cannot create multiple applications within 2 hours!"}

    if userid == -1 and apptype == 3:
        return {"error": True, "descriptor": "You cannot submit a LOA application until you become a member."}

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if t[0][3] == 0 or t[0][4] == 0:
        return {"error": True, "descriptor": "You must verify your TruckersMP and Steam before submitting an application"}
    userid = t[0][5]

    form = await request.form()
    apptype = form["apptype"]
    data = json.loads(form["data"])
    data = b64e(json.dumps(data))

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtappid'")
    t = cur.fetchall()
    applicationid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {applicationid+1} WHERE skey = 'nxtappid'")
    conn.commit()

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {apptype}, {discordid}, '{data}', 0, {int(time.time())}, 0, 0)")
    conn.commit()

    data = json.loads(form["data"])
    apptype = int(apptype)
    APPTYPE = {0: "Unknown", 1: "Driver", 2: "Staff", 3: "LOA"}
    apptypetxt = "Unknown"
    if apptype in APPTYPE.keys():
        apptypetxt = APPTYPE[apptype]

    durl = ""
    if apptype == 1:
        durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.applicant}'
    elif apptype == 2:
        durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.staffapplicant}'
    elif apptype == 3:
        durl = f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{config.loarequest}'
    if durl != "":
        try:
            requests.put(durl, headers = {"Authorization": f"Bot {config.bottoken}"})
        except:
            pass

    try:
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"{apptypetxt} Application Received",
                "description": f"One of our staff will get back to you shortly. If you want to update your application, please refer to `My Applications` in Drivers Hub.",
                    "fields": [{"name": "Application ID", "value": applicationid, "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Creation", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)

    except:
        pass

    cur.execute(f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    for d in data.keys():
        msg += f"**{d}**: {data[d]}\n\n"

    try:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(config.appwebhook, session=session)

            embed = discord.Embed(title = f"New {apptypetxt} Application", description = msg, color = 0x770202)
            if t[0][1].startswith("a_"):
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
            else:
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
            embed.set_footer(text = f"Application ID: {applicationid} ")
            embed.timestamp = datetime.now()
            await webhook.send(content = "<@&941544363878670366> <@&941544365950644224>", embed = embed)

    except:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(config.appwebhook, session=session)

            embed = discord.Embed(title = f"Application #{applicationid} Updated", description = "*Message too long, please view application on website.*", color = 0x770202)
            if t[0][1].startswith("a_"):
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
            else:
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
            embed.set_footer(text = f"Application ID: {applicationid} ")
            embed.timestamp = datetime.now()
            await webhook.send(content = "<@&941544363878670366> <@&941544365950644224>", embed = embed)

    return {"error": False, "response": {"message": "Application added", "applicationid": applicationid}}

@app.patch("/atm/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT name, userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    name = t[0][0]
    userid = t[0][1]

    form = await request.form()
    applicationid = form["applicationid"]
    message = form["message"]

    cur.execute(f"SELECT discordid, data, status FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if discordid != t[0][0]:
        # response.status_code = 401
        return {"error": True, "descriptor": "You are not the applicant"}
    if t[0][2] != 0:
        # response.status_code = 400
        if t[0][2] == 1:
            return {"error": True, "descriptor": "Application already accepted"}
        elif t[0][2] == 2:
            return {"error": True, "descriptor": "Application already declined"}
        else:
            return {"error": True, "descriptor": "Application already processed, status unknown."}

    discordid = t[0][0]
    data = json.loads(b64d(t[0][1]))
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
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Application Updated",
                "description": f"This is a reminder that your message has been recorded.",
                    "fields": [{"name": "Application ID", "value": applicationid, "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Creation", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)

    except:
        pass

    try:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(config.appwebhook, session=session)

            embed = discord.Embed(title = f"Application #{applicationid} - New Message", description = msg, color = 0x770202)
            if t[0][1].startswith("a_"):
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
            else:
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
            embed.set_footer(text = f"Application ID: {applicationid} ")
            embed.timestamp = datetime.now()
            await webhook.send(content = "<@&941544363878670366> <@&941544365950644224>", embed = embed)

    except:
        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url(config.appwebhook, session=session)

            embed = discord.Embed(title = f"Application #{applicationid} - New Message", description = "*Data too long, please view application on website.*", color = 0x770202)
            if t[0][1].startswith("a_"):
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
            else:
                embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
            embed.set_footer(text = f"Application ID: {applicationid} ")
            embed.timestamp = datetime.now()
            await webhook.send(content = "<@&941544363878670366> <@&941544365950644224>", embed = embed)

    return {"error": False, "response": {"message": "Message added", "applicationid": applicationid}}

@app.post("/atm/application/status")
async def updateApplicationStatus(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles,name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminid = t[0][0]
    roles = t[0][1].split(",")
    adminname = t[0][2]
    admindiscord = discordid
    while "" in roles:
        roles.remove("")
    adminhighest = 99999
    for i in roles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 30:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

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
        # response.status_code = 404
        return {"error": True, "descriptor": "404: Not found"}

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

    try:
        STATUS = {0: "Pending", 1: "Accepted", 2: "Declined"}
        statustxt = f"Unknown Status ({status})"
        if int(status) in STATUS.keys():
            statustxt = STATUS[int(status)]
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Application Status Updated",
                "description": f"[Message] {message}",
                    "fields": [{"name": "Application ID", "value": applicationid, "inline": True}, {"name": "Status", "value": statustxt, "inline": True}, \
                        {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}, {"name": "Responsible Staff", "value": f"<@{admindiscord}> (`{admindiscord}`)", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                        "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)

    except:
        import traceback
        traceback.print_exc()
        pass

    return {"error": False, "response": {"message": "Application status updated", "applicationid": applicationid, "status": status}}

@app.get("/atm/application")
async def getApplication(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminhighest = 99999
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1].split(",")
        while "" in roles:
            roles.remove("")
        for i in roles:
            if int(i) < adminhighest:
                adminhighest = int(i)

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "404: Not found"}
    
    if adminhighest >= 30 and discordid != t[0][1]:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    return {"error": False, "response": {"message": "Application found", "applicationid": t[0][0], "apptype": t[0][1],\
        "discordid": str(t[0][2]), "data": json.loads(b64d(t[0][3])), "status": t[0][4], "submitTimestamp": t[0][5], \
            "closedTimestamp": t[0][7], "closedBy": t[0][6]}}

@app.get("/atm/application/list")
async def getApplicationList(page: int, apptype: int, request: Request, response: Response, authorization: str = Header(None), showall: Optional[bool] = False):
    if page <= 0:
        page = 1
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    if isapptoken and showall:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminhighest = 99999
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1].split(",")
        while "" in roles:
            roles.remove("")
        for i in roles:
            if int(i) < adminhighest:
                adminhighest = int(i)

    t = None
    tot = 0
    if adminhighest >= 30 or showall == False:
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
        limit = ""
        if apptype != 0:
            limit = f" WHERE apptype = {apptype}"
        cur.execute(f"SELECT applicationid, apptype, discordid, submitTimestamp, status, closedTimestamp FROM application {limit} ORDER BY applicationid DESC LIMIT {(page-1) * 10}, 10")
        t = cur.fetchall()
        
        cur.execute(f"SELECT COUNT(*) FROM application")
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
        ret.append({"applicationid": tt[0], "apptype": tt[1], "discordid": f"{tt[2]}", "name": name, "status": tt[4], "submitTimestamp": tt[3], "closedTimestamp": tt[5]})

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get("/atm/application/positions")
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

@app.post("/atm/application/positions")
async def setApplicationPositions(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if validators.ipv6(ip) == True:
        orgiptype = 6
    curiptype = 4
    if validators.ipv6(request.client.host) == True:
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    adminid = t[0][0]
    roles = t[0][1].split(",")
    while "" in roles:
        roles.remove("")
    adminhighest = 99999
    for i in roles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 10:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

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

    return {"error": False, "response": {"message": "Application positions updated", "positions": positions}}