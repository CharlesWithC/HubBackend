# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests
from discord import Webhook
from typing import Optional
from datetime import datetime

from app import app, config
from db import newconn
from functions import *

ROLES = {0: "root", 1: "Founder", 2: "Chief Executive Officer", 3: "Chief Operating Officer", \
    4: "Chief Administrative Officer", 5: "Chief Technology Officier", 9: "Leadership", \
        20: "Human Resources Manager", 21: "Human Resources Staff", 30: "Lead Developer", 31: "Development Staff", \
            40: "Event Manager", 41: "Event Staff", 50: "Media Manager", 51: "Official Streamer", 52: "Media Team",\
                60: "Convoy Supervisor", 61: "Convoy Control",\
                 71: "Division Manager", 72: "Division Supervisor",\
                 98: "Trial Staff", 99: "Leave of absence", 100: "Driver",  223: "Staff of the Month", 224: "Driver of the Month",\
                 251: "Construction Division", 252: "Chilled Division", 253:" ADR Division",\
                    1000: "Partner", 10000: "External Staff"}

RANKING = {0: 941548241126834206, 2000: 941544375790489660, 10000: 941544368928596008, 15000: 969678264832503828, 25000: 941544370467901480, 40000: 969727939686039572, 50000: 941544372669907045, 75000: 969678270398341220, 80000: 969727945075732570, 100000: 941544373710094456, 150000: 969727950016643122, 200000: 969727954433245234, 250000: 969678280112353340, 300000: 969727958749155348, 350000: 969727962905735178, 400000: 969727966999379988, 450000: 969727971428536440, 500000: 941734703210311740, 600000: 969727975358607380, 700000: 969727979368370188, 800000: 969728350564282398, 900000: 969678286332518460, 1000000: 941734710470651964}

@app.get('/atm/member/list')
async def memberSearch(page:int, request: Request, response: Response, authorization: str = Header(None), search: Optional[str] = ''):
    if page <= 0:
        page = 1
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
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    search = search.replace("'","''").lower()
    
    cur.execute(f"SELECT userid, name, discordid, roles, avatar FROM user WHERE LOWER(name) LIKE '%{search}%' AND userid >= 0 ORDER BY userid ASC LIMIT {(page-1) * 10}, 10")
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
        ret.append({"userid": tt[0], "name": tt[1], "discordid": f"{tt[2]}", "highestrole": highestrole, "avatar": tt[4]})
    
    cur.execute(f"SELECT COUNT(*) FROM user WHERE LOWER(name) LIKE '%{search}%' AND userid >= 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    cur.execute(f"SELECT userid, name, discordid, avatar FROM user WHERE roles LIKE '%223%'") # Staff of the month
    t = cur.fetchall()
    staff_of_the_month = {}
    if len(t) > 0:
        tt = t[0]
        staff_of_the_month = {"userid": tt[0], "name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[3]}

    cur.execute(f"SELECT userid, name, discordid, avatar FROM user WHERE roles LIKE '%224%'") # Driver of the month
    t = cur.fetchall()
    driver_of_the_month = {}
    if len(t) > 0:
        tt = t[0]
        driver_of_the_month = {"userid": tt[0], "name": tt[1], "discordid": f"{tt[2]}", "avatar": tt[3]}    

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot, "staff_of_the_month": staff_of_the_month, "driver_of_the_month": driver_of_the_month}}

@app.get('/atm/member/info')
async def member(request: Request, response: Response, userid: int, authorization: str = Header(None)):
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
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

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
    
    if userid < 0:
        return {"error": True, "descriptor": "Not a member"}

    if adminhighest >= 30: # non hr or upper
        cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 404
            return {"error": True, "descriptor": "Member not found."}
        roles = t[0][3].split(",")
        while "" in roles:
            roles.remove("")
        roles = [int(i) for i in roles]
        cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {userid} AND status = 1")
        o = cur.fetchall()
        divisionpnt = 0
        if len(o) > 0:
            divisionpnt = o[0][0] * 500
        return {"error": False, "response": {"userid": userid, "name": t[0][1], "discordid": t[0][0], "avatar": t[0][2], \
            "bio": b64d(t[0][7]), "roles": roles, "join": t[0][4], "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}", \
                "distance": distance, "totjobs": totjobs, "fuel": fuel, "xp": xp, "eventpnt": eventpnt, "divisionpnt": divisionpnt}}
    else:
        cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio, email FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 404
            return {"error": True, "descriptor": "Member not found."}
        roles = t[0][3].split(",")
        while "" in roles:
            roles.remove("")
        roles = [int(i) for i in roles]
        cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {userid} AND status = 1")
        o = cur.fetchall()
        divisionpnt = 0
        if len(o) > 0:
            divisionpnt = o[0][0] * 500
        return {"error": False, "response": {"userid": userid, "name": t[0][1], "email": t[0][8], \
            "discordid": f"{t[0][0]}", "avatar": t[0][2], "bio": b64d(t[0][7]), "roles": roles, "join": t[0][4], \
                "truckersmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}",\
                    "distance": distance, "totjobs": totjobs, "fuel": fuel, "xp": xp, "eventpnt": eventpnt, "divisionpnt": divisionpnt}}

@app.post('/atm/member/add')
async def addMember(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    if adminhighest >= 30: # not hr level or upper
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = int(form["discordid"])

    cur.execute(f"SELECT * FROM banned WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        return {"error": True, "descriptor": "Banned user cannot be accepted as member."}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtuserid'")
    t = cur.fetchall()
    userid = int(t[0][0])
    
    cur.execute(f"SELECT userid, truckersmpid, steamid, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 400
        return {"error": True, "descriptor": "User not found"}
    if t[0][0] != -1:
        # response.status_code = 400
        return {"error": True, "descriptor": "Member already registered."}
    if t[0][1] == 0 or t[0][2] == 0:
        # response.status_code = 400
        return {"error": True, "descriptor": "User must have verified their TruckersMP and Steam account."}
    name = t[0][3]
    cur.execute(f"UPDATE user SET userid = {userid}, joints = {int(time.time())} WHERE discordid = {discordid}")
    cur.execute(f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(adminid, f'Added member **{name}** (User ID `{userid}`) (Discord ID `{discordid}`)')
    conn.commit()

    try:
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}), timeout=3)
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Member Update",
                "description": f"You are now a member of At The Mile Logistics!",
                    "fields": [{"name": "User ID", "value": f"{userid}", "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)

    except:
        pass

    return {"error": False, "response": {"message": "Member added", "userid": userid}}    

@app.delete("/atm/member/resign")
async def deleteMember(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, steamid, name, discordid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        return {"error": False, "descriptor": "Not a member"}
    steamid = t[0][1]
    cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.naviotoken})
    
    name = t[0][2].replace("'", "''")
    discordid = t[0][3]

    await AuditLog(-999, f'Member resigned: **{name}** (`{discordid}`)')
    return {"error": False, "response": {"message": "Member resigned"}}

@app.delete("/atm/member/dismiss")
async def dismissMember(userid: int, request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT userid, steamid, roles FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "User not found"}
    userid = t[0][0]
    steamid = t[0][1]
    roles = t[0][2].split(",")
    while "" in roles:
        roles.remove("")
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    if adminhighest >= highest:
        return {"error": True, "descriptor": "User position is higher than or equal to you"}

    cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
    cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    conn.commit()

    r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.naviotoken})
    
    await AuditLog(adminid, f'Dismissed member {userid}')
    return {"error": False, "response": {"message": "Member dismissed"}}

@app.post('/atm/member/role')
async def setMemberRole(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)
    if adminhighest >= 30:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    userid = int(form["userid"])
    if userid < 0:
        return {"error": True, "descriptor": "Invalid userid"}
    roles = form["roles"].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    cur.execute(f"SELECT name, roles, steamid, discordid FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Member not found."}
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
            return {"error": True, "descriptor": "Member role to add higher / equal."}
    
    for remove in removedroles:
        if remove <= adminhighest:
            return {"error": True, "descriptor": "Member role to remove higher / equal."}

    if len(addedroles) + len(removedroles) == 0:
        return {"error": False, "response": {"message": "Role not updated: Member already have those roles.", "roles": roles}}
        
    roles = [str(i) for i in roles]
    cur.execute(f"UPDATE user SET roles = '{','.join(roles)}' WHERE userid = {userid}")

    if 100 in addedroles:
        cur.execute(f"SELECT * FROM driver WHERE userid = {userid}")
        p = cur.fetchall()
        if len(p) == 0:
            cur.execute(f"INSERT INTO driver VALUES ({userid}, 0, 0, 0, 0, 0, {int(time.time())})")
            conn.commit()
        r = requests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.naviotoken})
        
        cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        userdiscordid = t[0][0]
        usermention = f"<@{userdiscordid}>"

        async with aiohttp.ClientSession() as session:
            webhook = Webhook.from_url("https://discordapp.com/api/webhooks/938826735053594685/jKO8djrHZbzafVOb9ooQVNosHrcDP9Wu5WtA39MuLChW1NQiAnVXrwCyagL-tn3ruanA", session=session)
            embed = discord.Embed(title = "Team Update", description = f"{usermention} has joined **At The Mile Logistics** as a **Driver**. Welcome to the family <:atmlove:931247295201149038>", color = 0x770202)
            embed.set_footer(text = f"At The Mile | Team Update", icon_url = config.gicon)
            embed.set_image(url = "https://hub.atmvtc.com/images/TeamUpdate.png")
            embed.timestamp = datetime.now()
            await webhook.send(content = usermention, embed=embed)
        
        try:
            requests.delete(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/929761730450567194', headers = {"Authorization": f"Bot {config.bottoken}"}, timeout = 3)
        except:
            pass
        try:
            requests.delete(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/942478809175830588', headers = {"Authorization": f"Bot {config.bottoken}"}, timeout = 3)
        except:
            pass
        try:
            requests.put(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/941548239776272454', headers = {"Authorization": f"Bot {config.bottoken}"}, timeout = 3)
        except:
            pass
        try:
            requests.put(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/941548241126834206', headers = {"Authorization": f"Bot {config.bottoken}"}, timeout = 3)
        except:
            pass
        
        msg = f"""Welcome <@{userdiscordid}> to the family! Please make yourself at home and check around for what you will need.
 
Please do not forget to register with us in [TruckersMP](https://truckersmp.com/vtc/49940) <:TMP:929962995109462086>

Download our tracker **Navio** by [clicking here](https://navio.app/download)

If you need any help please ask us in <#941554016087834644> or create a Human Resources Ticket in <#929761731016786030> 

If you have issues about Drivers Hub, open a technical ticket at <#929761731016786030> """

        
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        ddurl = f"https://discord.com/api/v9/channels/941537154360823870/messages"
        r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": "Welcome", "description": msg, 
                "footer": {"text": f"You are our #{userid} driver", "icon_url": config.gicon}, "image": {"url": "https://hub.atmvtc.com/images/bg.jpg"},\
                        "timestamp": str(datetime.now()), "color": 11730944}}))

    if 100 in removedroles:
        cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
        cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
        r = requests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.naviotoken})
    
    audit = f"Updated **{username}** (User ID `{userid}`) roles:\n"
    for add in addedroles:
        audit += f"**+** {ROLES[add]}\n"
    for remove in removedroles:
        audit += f"**-** {ROLES[remove]}\n"
    audit = audit[:-1].replace("'","''")
    await AuditLog(adminid, audit)
    conn.commit()

    return {"error": False, "response": {"message": "Roles updated.", "roles": roles}}

@app.get("/atm/member/roles")
async def getRoles(request: Request, response: Response):
    return {"error": False, "response": ROLES}

@app.post("/atm/member/point")
async def setMemberRole(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
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
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    if adminhighest >= 30: # not hr level or upper
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    userid = int(form["userid"])
    distance = int(int(form["mile"])*1.6)
    eventpnt = form["eventpnt"]

    cur.execute(f"UPDATE driver SET distance = distance + {distance}, eventpnt = eventpnt + {eventpnt} WHERE userid = {userid}")
    conn.commit()

    cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
    p = cur.fetchall()
    udiscordid = p[0][0]

    if int(distance) > 0:
        distance = "+" + form["mile"]
    if int(eventpnt) > 0:
        eventpnt = "+" + str(eventpnt)

    await AuditLog(adminid, f"Updated user #{userid} points:\n{distance} Miles\n{eventpnt} Event Points")

    return {"error": False, "response": {"message": "Points updated."}}

@app.get("/atm/member/steam")
async def memberSteam(request: Request, response: Response, authorization: str = Header(None)):
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
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    cur.execute(f"SELECT steamid, name, userid FROM user")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"steamid": str(tt[0]), "name": tt[1], "userid": tt[2]})
    return {"error": False, "response": {"list": ret}}

def point2rank(point):
    keys = list(RANKING.keys())
    for i in range(len(keys)):
        if point < keys[i]:
            return RANKING[keys[i-1]]
    return RANKING[1000000]

@app.patch("/atm/member/discordrole")
async def memberDiscordrole(request: Request, response: Response, authorization: str = Header(None)):
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
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    cur.execute(f"SELECT distance, eventpnt FROM driver WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "Member not driver"}
    totalpnt = int(t[0][0] / 1.6 + t[0][1])
    cur.execute(f"SELECT COUNT(*) FROM division WHERE userid = {userid} AND status = 1")
    o = cur.fetchall()
    divisionpnt = 0
    if len(o) > 0:
        divisionpnt = o[0][0] * 500
    totalpnt += divisionpnt
    
    rank = point2rank(totalpnt)

    try:
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        r=requests.get(f"https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}", headers=headers, timeout = 3)
        d = json.loads(r.text)
        if "roles" in d:
            roles = d["roles"]
            curroles = []
            for role in roles:
                if int(role) in list(RANKING.values()):
                    curroles.append(int(role))
            if rank in curroles:
                return {"error": True, "descriptor": "You already have the role."}
            else:
                requests.put(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{rank}', headers=headers, timeout = 3)
                for role in curroles:
                    requests.delete(f'https://discord.com/api/v9/guilds/{config.guild}/members/{discordid}/roles/{role}', headers=headers, timeout = 3)
                try:
                    msg = f"""GG <@{discordid}>! You have ranked up to <@&{rank}>!"""

                    headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
                    ddurl = f"https://discord.com/api/v9/channels/941537154360823870/messages"
                    r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": "Driver Rank Up", "description": msg, 
                            "footer": {"text": f"Congratulations!", "icon_url": config.gicon},\
                                    "timestamp": str(datetime.now()), "color": 11730944}}))
                                    
                except:
                    import traceback
                    traceback.print_exc()
                    pass
                return {"error": False, "response": "You have been given the role."}
        else:
            return {"error": True, "descriptor": "Member not in Discord Server"}

    except:
        pass