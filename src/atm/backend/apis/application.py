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

@app.post("/atm/application")
async def newApplication(response: Response, authorization: Optional[str] = Header(None)):
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

    form = await request.form()
    apptype = form["apptype"]
    truckerspmid = form["truckersmpid"]
    steamid = form["steamid"]
    data = b64e(json.dumps(form["data"]))

    # get application id count(*)
    cur.execute(f"SELECT COUNT(*) FROM application")
    t = cur.fetchall()
    applicationid = 0
    if len(t) != 0:
        applicationid = t[0][0]

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {apptype}, {discordid}, {truckerspmid}, {steamid}, '{data}', 0, 0, 0)")
    conn.commit()

    return {"error": False, "response": {"message": "Application added", "applicationid": applicationid}}

@app.patch("/atm/application")
async def updateApplication(response: Response, authorization: Optional[str] = Header(None)):
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

    form = await request.form()
    applicationid = form["applicationid"]
    truckerspmid = form["truckersmpid"]
    steamid = form["steamid"]
    data = b64e(json.dumps(form["data"]))

    cur.execute(f"UPDATE application SET truckersmpid = {truckerspmid}, steamid = {steamid}, data = '{data}' WHERE applicationid = {applicationid}")
    conn.commit()

    return {"error": False, "response": {"message": "Application updated", "applicationid": applicationid}}

@app.post("/atm/application/status")
async def updateApplicationStatus(response: Response, authorization: Optional[str] = Header(None)):
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
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1]
        adminhighest = 99999
        for i in roles.split(","):
            if int(i) < adminhighest:
                adminhighest = int(i)
        if adminhighest >= 30:
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    applicationid = form["applicationid"]
    status = form["status"]

    cur.execute(f"UPDATE application SET status = {status}, closedBy = {adminid}, closedTimestamp = {int(time.time())} WHERE applicationid = {applicationid}")
    cur.execute(f"INSERT INTO auditlog VALUES ({adminid}, 'Updated application {applicationid} status to {status}', {int(time.time())})")
    conn.commit()

    return {"error": False, "response": {"message": "Application status updated", "applicationid": applicationid, "status": status}}

@app.get("/atm/application")
async def getApplication(response: Response, applicationid: int, authorization: Optional[str] = Header(None)):
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
    adminhighest = 99999
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1]
        for i in roles.split(","):
            if int(i) < adminhighest:
                adminhighest = int(i)

    cur.execute(f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": "404: Not found"}
    
    if adminhighest >= 30 and discordid != t[0][1]:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    return {"error": False, "response": {"message": "Application found", "application": t[0], "truckersmpid": t[0][2], "steamid": t[0][3], "data": json.loads(b64d(t[0][4]))}}

@app.get("/atm/application/list")
async def getApplicationList(response: Response, authorization: Optional[str] = Header(None)):
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
    adminhighest = 99999
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1]
        for i in roles.split(","):
            if int(i) < adminhighest:
                adminhighest = int(i)

    if adminhighest >= 30 and discordid != t[0][1]:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT * FROM application")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": "404: Not found"}

    ret = []
    for tt in t:
        ret.append({"applicationid": tt[0], "discordid": tt[1], "truckersmpid": tt[2], "steamid": tt[3]})

    return {"error": False, "response": {"message": "Application list found", "applications": ret}}