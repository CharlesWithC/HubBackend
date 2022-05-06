# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from fastapi.responses import RedirectResponse
from discord_oauth2 import DiscordAuth
from uuid import uuid4
import json, time
from datetime import datetime
import discord, asyncio
from discord import Webhook
import aiohttp

from app import app, config
from db import newconn
from functions import *

@app.post("/atm/application")
async def newApplication(request: Request, response: Response, authorization: str = Header(None)):
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
    data = json.loads(form["data"])
    data = b64e(json.dumps(data))

    # get application id count(*)
    cur.execute(f"SELECT COUNT(*) FROM application")
    t = cur.fetchall()
    applicationid = 0
    if len(t) != 0:
        applicationid = t[0][0]

    cur.execute(f"INSERT INTO application VALUES ({applicationid}, {apptype}, {discordid}, '{data}', 0, 0, 0)")
    conn.commit()

    data = json.loads(form["data"])
    apptype = int(apptype)
    APPTYPE = {1: "Driver", 2: "Staff", 3: "LOA"}
    cur.execute(f"SELECT name, avatar, email FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    msg = f"Applicant: <@{discordid}> (`{discordid}`)\nEmail: {t[0][2]}\n\n"
    for d in data.keys():
        msg += f"**{d}**: {data[d]}\n\n"

    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(config.appwebhook, session=session)

        embed = discord.Embed(title = f"New {APPTYPE[apptype]} Application", description = msg, color = 0x770202)
        if t[0][1].startswith("a_"):
            embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
        else:
            embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
        embed.set_footer(text = f"Application ID: {applicationid} ")
        embed.timestamp = datetime.now()
        await webhook.send(embed = embed)

    return {"error": False, "response": {"message": "Application added", "applicationid": applicationid}}

@app.patch("/atm/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
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
    data = json.loads(form["data"])
    data = b64e(json.dumps(data))

    cur.execute(f"SELECT discordid, data, status FROM application WHERE applicationid = {applicationid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 400
        return {"error": True, "descriptor": "Application not found"}
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
    if data == t[0][1]:
        # response.status_code = 401
        return {"error": False, "response": {"message": "Application not updated: Data not changed", "applicationid": applicationid}}

    cur.execute(f"UPDATE application SET data = '{data}' WHERE applicationid = {applicationid}")
    conn.commit()

    return {"error": False, "response": {"message": "Application updated", "applicationid": applicationid}}

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
    cur.execute(f"SELECT discordid FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1].split(",")
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

    cur.execute(f"UPDATE application SET status = {status}, closedBy = {adminid}, closedTimestamp = {int(time.time())} WHERE applicationid = {applicationid}")
    await AuditLog(adminid, f"Updated application {applicationid} status to {status}")
    conn.commit()

    return {"error": False, "response": {"message": "Application status updated", "applicationid": applicationid, "status": status}}

@app.get("/atm/application")
async def getApplication(request: Request, response: Response, applicationid: int, authorization: str = Header(None)):
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

    return {"error": False, "response": {"message": "Application found", "application": t[0], "steamid": t[0][3], "data": json.loads(b64d(t[0][4]))}}

@app.get("/atm/application/list")
async def getApplicationList(request: Request, response: Response, authorization: str = Header(None)):
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
    adminhighest = 99999
    if len(t) > 0:
        adminid = t[0][0]
        roles = t[0][1].split(",")
        while "" in roles:
            roles.remove("")
        for i in roles:
            if int(i) < adminhighest:
                adminhighest = int(i)

    if adminhighest >= 30 and discordid != t[0][1]:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT applicationid, discordid FROM application")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "404: Not found"}

    ret = []
    for tt in t:
        ret.append({"applicationid": tt[0], "discordid": f"{tt[1]}"})

    return {"error": False, "response": ret}