# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests

from app import app, config
from db import newconn
from functions import *

@app.post("/atm/navio")
async def navio(request: Request, Navio_Signature: str = Header(None)):
    conn = newconn()
    cur = conn.cursor()
    
    d = await request.json()
    print(d)
    if d["object"] != "event":
        return {"error": True, "response": "Only events are accepted."}
    e = d["type"]
    if e == "company_driver.detached":
        steamid = int(d["data"]["object"]["steam_id"])
        cur.execute(f"SELECT userid FROM user WHERE steamid = '{steamid}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "response": "User not found."}
        userid = t[0][0]
        await AuditLog(userid, "Member resigned from Navio")
        cur.execute(f"DELETE FROM driver WHERE userid = {userid}")
        cur.execute(f"DELETE FROM dlog WHERE userid = {userid}")
        cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
        conn.commit()
        
        return {"error": False, "response": "User resigned."}

    steamid = int(d["data"]["object"]["driver"]["steam_id"])
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid FROM user WHERE steamid = '{steamid}'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "response": "User not found."}
    userid = t[0][0]
    driven_distance = d["data"]["object"]["driven_distance"]
    fuel_used = d["data"]["object"]["fuel_used"]
    money = 0
    xp = 0
    if e == "job.cancelled":
        money = -float(d["data"]["object"]["events"][-1]["meta"]["penalty"])
    elif e == "job.delivered":
        money = d["data"]["object"]["events"][-1]["meta"]["revenue"]
        xp = d["data"]["object"]["events"][-1]["meta"]["earned_xp"]
    top_speed = d["data"]["object"]["truck"]["top_speed"]
    cur.execute(f"UPDATE driver SET distance = distance + {driven_distance}, fuel = fuel + {fuel_used}, revenue = revenue + {money}, xp = xp + {xp} WHERE userid = {userid}")
    
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtlogid'")
    t = cur.fetchall()
    logid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {logid+1} WHERE skey = 'nxtlogid'")
    conn.commit()

    cur.execute(f"INSERT INTO dlog VALUES ({logid}, {userid}, '{b64e(json.dumps(d))}', {top_speed}, {int(time.time())})")
    conn.commit()
    return {"error": False, "response": "Logged"}