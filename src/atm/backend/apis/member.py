# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests

from app import app, config
from db import newconn
from functions import *

ROLES = {0: "root", 1: "Founder", 2: "Chief Executive Officer", 3: "Chief Operating Officer", \
    4: "Chief Administrative Officer", 5: "Chief Technology Officier", 9: "Leadership", 10: "Lead Developer", 15: "Tester", \
        20: "Human Resources Manager", 21: "Human Resources Staff", 30: "Leave of absence", 31: "Development Staff", \
            40: "Event Manager", 41: "Event Staff", 50: "Media Manager", 51: "Official Streamer", 52: "Media Team",\
                60: "Convoy Supervisor", 61: "Convoy Control",\
                 100: "Driver", 10000: "External Staff"}

@app.get("/atm/member/list")
async def memberList(page:int, request: Request, response: Response, authorization: str = Header(None)):
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
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    cur.execute(f"SELECT userid, name, discordid FROM user WHERE userid >= 0 ORDER BY userid ASC")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"userid": tt[0], "name": tt[1], "discordid": f"{tt[2]}"})
    totpage = math.ceil(len(ret)/30)
    ret = ret[(page-1)*30:page*30]
    return {"error": False, "response": {"list": ret, "page": page, "tot": totpage}}
    
@app.get('/atm/member/info')
async def member(response: Response, userid: int, authorization: str = Header(None)):
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
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    conn = newconn()
    cur = conn.cursor()
    if adminhighest >= 30: # non hr or upper
        cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, bio FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 404
            return {"error": True, "descriptor": "Member not found."}
        roles = [int(i) for i in t[0][3].split(",")]
        return {"error": False, "response": {"userid": userid, "username": t[0][1], "avatar": t[0][2], "bio": b64e(t[0][7]), "roles": roles, "join": t[0][4], "truckesmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}"}}
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
        return {"error": False, "response": {"userid": userid, "username": t[0][1], "email": t[0][8], "discordid": f"{t[0][0]}", "avatar": t[0][2], "bio": b64e(t[0][7]), "roles": roles, "join": t[0][4], "truckesmpid": f"{t[0][5]}", "steamid": f"{t[0][6]}"}}

@app.post('/atm/member/add')
async def addMember(request: Request, response: Response, authorization: str = Header(None)):
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
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
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
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = form["discordid"]

    # get next userid by count(*)
    cur.execute(f"SELECT COUNT(*) FROM user WHERE userid >= 0")
    t = cur.fetchall()
    userid = 0
    if len(t) > 0:
        userid = t[0][0]
    
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
    await AuditLog(adminid, f'Added member **{name}** (User ID `{userid}`) (Discord ID `{discordid}`)')
    conn.commit()

    try:
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        durl = "https://discord.com/api/v9/users/@me/channels"
        r = requests.post(durl, headers = headers, data = json.dumps({"recipient_id": discordid}))
        d = json.loads(r.text)
        if "id" in d:
            channelid = d["id"]
            ddurl = f"https://discord.com/api/v9/channels/{channelid}/messages"
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Member Update",
                "description": f"You are now a member of At The Mile Logistics!",
                    "fields": [{"name": "User ID", "value": f"{userid}", "inline": True}, {"name": "Time", "value": f"<t:{int(time.time())}>", "inline": True}],
                    "footer": {"text": f"At The Mile Logistics", "icon_url": config.gicon}, "thumbnail": {"url": config.gicon},\
                         "timestamp": str(datetime.now())}}))

    except:
        pass

    return {"error": False, "response": {"message": "Member added", "userid": userid}}    

@app.post('/atm/member/role')
async def setMemberRole(request: Request, response: Response, authorization: str = Header(None)):
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
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    form = await request.form()
    userid = form["userid"]
    roles = form["roles"].split(",")
    while "" in roles:
        roles.remove("")
    roles = [int(i) for i in roles]
    cur.execute(f"SELECT name, roles FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Member not found."}
    username = t[0][0]
    oldroles = t[0][1].split(",")
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
            response.status_code = 401
            return {"error": True, "descriptor": "Member role to add higher / equal."}
    
    for remove in removedroles:
        if remove <= adminhighest:
            response.status_code = 401
            return {"error": True, "descriptor": "Member role to remove higher / equal."}

    if len(addedroles) + len(removedroles) == 0:
        return {"error": False, "response": {"message": "Role not updated: Member already have those roles.", "roles": roles}}
        
    roles = [str(i) for i in roles]
    cur.execute(f"UPDATE user SET roles = '{','.join(roles)}' WHERE userid = {userid}")

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