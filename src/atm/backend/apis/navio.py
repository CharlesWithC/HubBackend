# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests
from datetime import datetime

from app import app, config
from db import newconn
from functions import *

@app.post("/atm/navio")
async def navio(request: Request, Navio_Signature: str = Header(None)):
    conn = newconn()
    cur = conn.cursor()

    if request.client.host != "185.233.107.244":
        await AuditLog(0, f"Detected suspicious navio webhook post from {request.client.host} - REJECTED")
        return {"error": True, "descriptor": "Validation failed"}
    
    d = await request.json()
    if d["object"] != "event":
        return {"error": True, "descriptor": "Only events are accepted."}
    e = d["type"]
    if e == "company_driver.detached":
        steamid = int(d["data"]["object"]["steam_id"])
        cur.execute(f"SELECT userid FROM user WHERE steamid = '{steamid}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "User not found."}
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
    cur.execute(f"SELECT userid, name FROM user WHERE steamid = '{steamid}'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "User not found."}
    userid = t[0][0]
    username = t[0][1]
    driven_distance = d["data"]["object"]["driven_distance"]
    fuel_used = d["data"]["object"]["fuel_used"]
    xp = 0
    if e == "job.delivered":
        xp = d["data"]["object"]["events"][-1]["meta"]["earned_xp"]
        if driven_distance < 0:
            driven_distance = d["data"]["object"]["events"][-1]["meta"]["distance"]
    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"]
    cur.execute(f"UPDATE driver SET totjobs = totjobs + 1, distance = distance + {driven_distance}, fuel = fuel + {fuel_used}, xp = xp + {xp} WHERE userid = {userid}")
    
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtlogid'")
    t = cur.fetchall()
    logid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {logid+1} WHERE skey = 'nxtlogid'")
    conn.commit()

    cur.execute(f"INSERT INTO dlog VALUES ({logid}, {userid}, '{b64e(json.dumps(d))}', {top_speed}, {int(time.time())})")
    conn.commit()

    try:
        source_city = d["data"]["object"]["source_city"]["name"]
        source_company = d["data"]["object"]["source_company"]["name"]
        destination_city = d["data"]["object"]["destination_city"]["name"]
        destination_company = d["data"]["object"]["destination_company"]["name"]
        cargo = d["data"]["object"]["cargo"]["name"]
        cargo_mass = d["data"]["object"]["cargo"]["mass"]
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        ddurl = f"https://discord.com/api/v9/channels/942178734025371758/messages"
        game = d["data"]["object"]["game"]["short_name"]
        munit = "€"
        if not game.startswith("e"):
            munit = "$"
        if e == "job.delivered":
            revenue = d["data"]["object"]["events"][-1]["meta"]["revenue"]
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Job Completed - #{logid}", 
                    "fields": [{"name": "From", "value": source_company + ", " + source_city, "inline": True},
                               {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                               {"name": "Distance", "value": f"{int(driven_distance/1.6)} miles", "inline": True},
                               {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": False},
                               {"name": "Fuel Cost", "value": f"{int(fuel_used)}L", "inline": True},
                               {"name": "Revenue", "value": f"{munit}{revenue}", "inline": True},
                               {"name": "XP Earned", "value": f"{xp}", "inline": True}],
                    "footer": {"text": username}, "color": 11730944,\
                        "timestamp": str(datetime.now()), "color": 11730944}}), timeout=3)

    except:
        import traceback
        traceback.print_exc()
        pass

    return {"error": False, "response": "Logged"}