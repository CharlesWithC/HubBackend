# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from uuid import uuid4
import json, time

from app import app, config
from db import newconn
from functions import *

ROLES = {1: "Founder", 2: "Chief Executive Officer", 3: "Chief Operating Officer", \
    4: "Chief Administrative Officer", 5: "Chief Technology Officier", 9: "Leadership", 10: "Lead Developer", 15: "Tester", \
        20: "Human Resources Manager", 21: "Human Resources Staff", 30: "Development Staff", \
            40: "Event Manager", 41: "Event Staff", 50: "Media Team", 100: "Driver"}

@app.get('/atm/member/info')
async def member(response: Response, memberid: int):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, name, avatar, roles, joints, truckersmpid, steamid, extra FROM member WHERE memberid = {memberid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": "Member not found."}
    roles = [int(i) for i in t[0][3].split(",")]
    extra = {}
    if t[0][7] != "":
        extra = json.loads(b64d(t[0][7]))
    return {"error": False, "response": {"memberid": memberid, "username": t[0][1], "avatar": t[0][2], "roles": roles, "join": t[0][4], "truckesmpid": t[0][5], "steamid": t[0][6], "extra": extra}}

@app.post('/atm/member/info')
async def addMember(request: Request, response: Response, authorization: Optional[str] = Header(None)):
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
    cur.execute(f"SELECT memberid, roles FROM member WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1]
    adminhighest = 99999
    for i in adminroles.split(","):
        if int(i) < adminhighest:
            adminhighest = int(i)

    if adminhighest >= 30: # not hr level or upper
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    
    form = await request.form()
    discordid = form["discordid"]

    # get next memberid by count(*)
    cur.execute(f"SELECT COUNT(*) FROM member")
    t = cur.fetchall()
    memberid = 0
    if len(t) > 0:
        memberid = t[0][0]

    name = ""
    avatar = ""
    email = ""
    cur.execute(f"SELECT data FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        data = json.loads(b64d(t[0][0]))
        name = data["username"]
        avatar = data["avatar"]
        name = name.replace("'","''")
        email = data["email"]
        email = email.replace("'","''")

    truckersmpid = 0
    steamid = 0
    cur.execute(f"SELECT truckersmpid, steamid FROM application WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        truckersmpid = t[0][0]
        steamid = t[0][1]
    
    cur.execute(f"SELECT * FROM member WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        response.status_code = 400
        return {"error": True, "descriptor": "Member already exists."}
    
    cur.execute(f"INSERT INTO member VALUES ({memberid}, '{name}', '{avatar}', {discordid}, '{email}', '', {int(time.time())}, {truckersmpid}, {steamid}, '')")
    cur.execute(f"INSERT INTO auditlog VALUES ({adminid}, 'Added member {memberid} (Discord ID {discordid})', {int(time.time())})")
    conn.commit()

    return {"error": False, "response": {"message": "Member added", "memberid": memberid}}    

@app.post('/atm/member/role')
async def setMemberRole(request: Request, response: Response, authorization: Optional[str] = Header(None)):
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
    cur.execute(f"SELECT memberid, roles FROM member WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1]
    adminhighest = 99999
    for i in adminroles.split(","):
        if int(i) < adminhighest:
            adminhighest = int(i)

    form = await request.form()
    memberid = form["memberid"]
    roles = form["roles"].split(",")
    roles = [int(i) for i in roles]
    cur.execute(f"SELECT roles FROM member WHERE memberid = {memberid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": "Member not found."}
    oldroles = t[0][0].split(",")
    if oldroles == [""]:
        oldroles = []
    else:
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
        if add < adminhighest:
            response.status_code = 401
            return {"error": True, "descriptor": "Member role to add higher than your role."}
    
    for remove in removedroles:
        if remove < adminhighest:
            response.status_code = 401
            return {"error": True, "descriptor": "Member role to remove higher than your role."}

    if len(addedroles) + len(removedroles) == 0:
        return {"error": False, "response": {"message": "Role not updated: Member already have those roles.", "roles": roles}}
        
    roles = [str(i) for i in roles]
    cur.execute(f"UPDATE member SET roles = '{','.join(roles)}' WHERE memberid = {memberid}")

    audit = f"Updated {memberid} roles: "
    for add in addedroles:
        audit += f"+{ROLES[add]},"
    for remove in removedroles:
        audit += f"-{ROLES[remove]},"
    audit = audit[:-1].replace("'","''")
    cur.execute(f"INSERT INTO auditlog VALUES ({adminid}, '{audit}', {int(time.time())})")
    conn.commit()

    return {"error": False, "response": {"message": "Roles updated.", "roles": roles}}