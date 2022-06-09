# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
import json, time, math
from typing import Optional
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *

divisiontxt = {1: "Construction", 2: "Chilled", 3: "ADR"}

@app.post("/atm/division/validate")
async def divisionValidateRequest(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
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
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    logid = int(form["logid"])
    divisionid = int(form["divisionid"]) 
    # 1: Construction / 2: Chilled / 3: ADR

    cur.execute(f"SELECT userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    userid = t[0][0]
    if userid == -1:
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "Delivery log not found."}
    luserid = t[0][0]
    if userid != luserid:
        return {"error": True, "descriptor": "You can only request division validation for your own deliveries."}

    cur.execute(f"SELECT status FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) > 0:
        status = t[0][0]
        if status == 0:
            return {"error": True, "descriptor": "You have already requested validation and please wait patiently until supervisor check your request."}
        elif status == 1:
            return {"error": True, "descriptor": "The delivery has already been validated and you have been given 500 points."}
        elif status == 2:
            return {"error": True, "descriptor": "The delivery has been denied and you may not request validation again."}
    
    cur.execute(f"SELECT roles FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    roles = t[0][0].split(",")
    divisions = []
    for role in roles:
        if role == "251":
            divisions.append(1)
        elif role == "252":
            divisions.append(2)
        elif role == "253":
            divisions.append(3)
    if not divisionid in divisions:
        return {"error": True, "descriptor": "You are not a driver for the division."}
    
    cur.execute(f"INSERT INTO division VALUES ({logid}, {divisionid}, {userid}, {int(time.time())}, 0, -1, -1, '')")
    conn.commit()
    
    try:
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Division Validation Request for Delivery #{logid} Received",
                "description": f"Division supervisor will check your request and you will receive an update soon.",
                    "fields": [{"name": "Division", "value": divisiontxt[divisionid], "inline": True}, {"name": "Status", "value": "Pending", "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)
    except:
        pass

    cur.execute(f"SELECT userid, name, avatar FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    tt = t[0]
    msg = f"**User ID**: {tt[0]}\n**Name**: {tt[1]}\n**Discord**: <@{discordid}> (`{discordid}`)\n\n"
    msg += f"**Delivery ID**: [{logid}](https://{config.dhdomain}/delivery?logid={logid})\n**Division**: {divisiontxt[divisionid]}"
    avatar = tt[2]

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(config.divisionwebhook, session=session)

        embed = discord.Embed(title = f"New Division Validation Request for Delivery #{logid}", description = msg, color = 0x770202)
        if t[0][1].startswith("a_"):
            embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif")
        else:
            embed.set_author(name = tt[1], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png")
        embed.set_footer(text = f"Delivery ID: {logid} ")
        embed.timestamp = datetime.now()
        await webhook.send(content = "<@&943736126491987999> <@&943735031954821141>", embed = embed)

    return {"error": False, "response": "Request submitted."}

@app.get("/atm/division/validate")
async def divisionValidateList(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
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
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    divisionstaff = False
    for i in adminroles:
        if int(i) == 71 or int(i) == 72:
            divisionstaff = True
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 10 and not divisionstaff:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT logid, userid, divisionid FROM division WHERE status = 0 AND logid >= 0")
    t = cur.fetchall()
    ret = []
    for tt in t:
        name = "Unknown"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[1]}")
        ttt = cur.fetchall()
        if len(ttt) > 0:
            name = ttt[0][0]
        ret.append({"logid": tt[0], "divisionid": tt[2], "userid": tt[1], "name": name})
    
    return {"error": False, "response": ret}

@app.patch("/atm/division/validate")
async def divisionValidate(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
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
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    divisionstaff = False
    for i in adminroles:
        if int(i) == 71 or int(i) == 72:
            divisionstaff = True
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 10 and not divisionstaff:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    logid = int(form["logid"])
    divisionid = int(form["divisionid"])
    reason = form["reason"]
    status = int(form["status"])
    
    cur.execute(f"SELECT divisionid, status FROM division WHERE logid = {logid} AND logid >= 0")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": f"Validation request not found for delivery #{logid}"}
    if divisionid == 0:
        divisionid = t[0][0]
        
    cur.execute(f"UPDATE division SET divisionid = {divisionid}, status = {status}, staffid = {adminid}, updatets = {int(time.time())}, reason = '{b64e(reason)}' WHERE logid = {logid}")
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
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Division Validation Request for Delivery #{logid} Updated",
                "description": reason,
                    "fields": [{"name": "Division", "value": divisiontxt[divisionid], "inline": True}, {"name": "Status", "value": STATUS[status], "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True},\
                        {"name": "Division Supervisor", "value": f"<@{adiscordid}> (`{adiscordid}`)", "inline": False}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)
    except:
        pass

    return {"error": False, "response": "Status updated"}

@app.get("/atm/division/info")
async def divisionInfo(request: Request, response: Response, authorization: str = Header(None), logid: Optional[int] = -1):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
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
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
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
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT userid FROM user WHERE discordid = '{discordid}'")
    t = cur.fetchall()
    userid = t[0][0]
    if userid == -1:
        return {"error": True, "descriptor": "401: Unauthroized"}

    if logid != -1:
        cur.execute(f"SELECT divisionid, userid, requestts, status, updatets, staffid, reason FROM division WHERE logid = {logid} AND logid >= 0")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
            t = cur.fetchall()
            if len(t) == 0:
                return {"error": True, "descriptor": f"Delivery not found"}
            duserid = t[0][0]
            if duserid != userid:
                return {"error": True, "descriptor": f"This delivery is not validated as a division delivery!"}
            else:
                return {"error": False, "response": {"msg": "Division validation request not submitted", "requestSubmitted": False}}
        tt = t[0]
        divisionid = tt[0]
        duserid = tt[1]
        requestts = tt[2]
        status = tt[3]
        updatets = tt[4]
        staffid = tt[5]
        reason = b64d(tt[6])

        cur.execute(f"SELECT roles FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        adminroles = t[0][0].split(",")
        while "" in adminroles:
            adminroles.remove("")
        adminhighest = 99999
        divisionstaff = False
        for i in adminroles:
            if int(i) == 71 or int(i) == 72:
                divisionstaff = True
            if int(i) < adminhighest:
                adminhighest = int(i)
        if adminhighest >= 10 and not divisionstaff:
            if userid != duserid and status != 1:
                return {"error": True, "descriptor": f"This delivery is not validated as a division delivery!"}
        isstaff = False
        if adminhighest < 10 or divisionstaff:
            isstaff = True
        staffname = "/"
        if staffid != -1:
            cur.execute(f"SELECT name FROM user WHERE userid = {staffid}")
            t = cur.fetchall()
            staffname = t[0][0]
        if userid == duserid:
            return {"error": False, "response": {"divisionid": divisionid, "requestts": requestts, "status": status, \
                "updatets": updatets, "staffid": staffid, "staffname": staffname, "reason": reason, "isstaff": isstaff}}
        else:
            return {"error": False, "response": {"divisionid": divisionid, "status": status, \
                "updatets": updatets, "staffid": staffid, "staffname": staffname, "isstaff": isstaff}}

    construction = []
    cur.execute(f"SELECT name, userid FROM user WHERE roles LIKE '%251%'")
    t = cur.fetchall()
    for tt in t:
        cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {tt[1]} AND divisionid = 1 AND status = 1 ORDER BY COUNT(*) DESC")
        p = cur.fetchall()
        cnt = 0
        if len(p) > 0:
            cnt = p[0][0]
        construction.append({"userid": tt[1], "name": tt[0], "points": cnt * 500})

    chilled = []
    cur.execute(f"SELECT name, userid FROM user WHERE roles LIKE '%252%'")
    t = cur.fetchall()
    for tt in t:
        cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {tt[1]} AND divisionid = 2 AND status = 1 ORDER BY COUNT(*) DESC")
        p = cur.fetchall()
        cnt = 0
        if len(p) > 0:
            cnt = p[0][0]
        chilled.append({"userid": tt[1], "name": tt[0], "points": cnt * 500})

    adr = []
    cur.execute(f"SELECT name, userid FROM user WHERE roles LIKE '%253%'")
    t = cur.fetchall()
    for tt in t:
        cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {tt[1]} AND divisionid = 3 AND status = 1 ORDER BY COUNT(*) DESC")
        p = cur.fetchall()
        cnt = 0
        if len(p) > 0:
            cnt = p[0][0]
        adr.append({"userid": tt[1], "name": tt[0], "points": cnt * 500})
    
    delivery = []
    cur.execute(f"SELECT logid FROM division WHERE status = 1 AND logid >= 0 ORDER BY updatets DESC LIMIT 10")
    p = cur.fetchall()
    for pp in p:
        cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit, distance FROM dlog WHERE logid = {pp[0]}")
        t = cur.fetchall()
        tt = t[0]
        data = json.loads(b64d(tt[1]))
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

        delivery.append({"logid": tt[3], "userid": tt[0], "name": name, "distance": distance, \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": cargo_mass, "profit": profit, "unit": unit, "timestamp": tt[2]})
    
    return {"error": False, "response": {"construction": construction, "chilled": chilled, "adr": adr, "deliveries": delivery}}
