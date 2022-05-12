# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math, validators
import requests
from datetime import datetime

from app import app, config
from db import newconn
from functions import *

from random import randint

GIFS = ["https://c.tenor.com/fjTTED8MZxIAAAAC/truck.gif",
    "https://c.tenor.com/QhMgCV8uMvIAAAAC/airtime-weeee.gif",
    "https://c.tenor.com/VYt4iLQJWhcAAAAd/kid-spin.gif",
    "https://c.tenor.com/_aICF_XLbR4AAAAC/ck8car-driving.gif",
    "https://c.tenor.com/jEW-3JELMG4AAAAM/skidding-white-pick-up.gif",
    "https://c.tenor.com/JGw-jxHDAGoAAAAC/truck-lol.gif",
    "https://c.tenor.com/2B9tkbj7CVEAAAAM/explode-truck.gif",
    "https://c.tenor.com/Tl6l934qO70AAAAC/driving-truck.gif",
    "https://c.tenor.com/1SPfoAWWejEAAAAC/chevy-truck.gif",
    "https://c.tenor.com/MfGOJIgU22UAAAAC/ford-f100-truck.gif"]

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
        cur.execute(f"UPDATE driver SET userid = -userid WHERE userid = {userid}")
        cur.execute(f"UPDATE dlog SET userid = -userid WHERE userid = {userid}")
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
    driven_distance = float(d["data"]["object"]["driven_distance"])
    fuel_used = d["data"]["object"]["fuel_used"]
    game = d["data"]["object"]["game"]["short_name"]
    munitint = 1 # euro
    if not game.startswith("e"):
        munitint = 2 # dollar
    revenue = 0
    xp = 0
    isdelivered = 0
    if e == "job.delivered":
        revenue = d["data"]["object"]["events"][-1]["meta"]["revenue"]
        isdelivered = 1
        xp = d["data"]["object"]["events"][-1]["meta"]["earned_xp"]
        driven_distance = float(d["data"]["object"]["events"][-1]["meta"]["distance"])
    else:
        revenue = -float(d["data"]["object"]["events"][-1]["meta"]["penalty"])
    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"] * 3.6 # m/s => km/h
    cur.execute(f"UPDATE driver SET totjobs = totjobs + 1, distance = distance + {driven_distance}, fuel = fuel + {fuel_used}, xp = xp + {xp} WHERE userid = {userid}")
    
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtlogid'")
    t = cur.fetchall()
    logid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {logid+1} WHERE skey = 'nxtlogid'")
    conn.commit()

    cur.execute(f"INSERT INTO dlog VALUES ({logid}, {userid}, '{b64e(json.dumps(d))}', {top_speed}, {int(time.time())}, \
        {isdelivered}, {revenue}, {munitint}, {fuel_used}, {driven_distance})")
    conn.commit()

    try:
        source_city = d["data"]["object"]["source_city"]["name"]
        source_company = d["data"]["object"]["source_company"]["name"]
        destination_city = d["data"]["object"]["destination_city"]["name"]
        destination_company = d["data"]["object"]["destination_company"]["name"]
        if source_city is None:
            source_city = ""
        if source_company is None:
            source_company = ""
        if destination_city is None:
            destination_city = ""
        if destination_company is None:
            destination_company = ""
        cargo = d["data"]["object"]["cargo"]["name"]
        cargo_mass = d["data"]["object"]["cargo"]["mass"]
        headers = {"Authorization": f"Bot {config.bottoken}", "Content-Type": "application/json"}
        ddurl = f"https://discord.com/api/v9/channels/942178734025371758/messages"
        munit = "€"
        if not game.startswith("e"):
            munit = "$"
        if e == "job.delivered":
            k = randint(0, len(GIFS)-1)
            r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Job Completed - #{logid}", 
                    "fields": [{"name": "From", "value": source_company + ", " + source_city, "inline": True},
                               {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                               {"name": "Distance", "value": f"{int(driven_distance/1.6)} miles", "inline": True},
                               {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": False},
                               {"name": "Fuel Cost", "value": f"{int(fuel_used)}L", "inline": True},
                               {"name": "Revenue", "value": f"{munit}{revenue}", "inline": True},
                               {"name": "XP Earned", "value": f"{xp}", "inline": True}],
                    "footer": {"text": username}, "color": 11730944,\
                        "timestamp": str(datetime.now()), "image": {"url": GIFS[k]}, "color": 11730944}}), timeout=3)

            cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
            p = cur.fetchall()
            udiscordid = p[0][0]
            requests.get(f"http://127.0.0.1:58001/internal/mile?user={udiscordid}&mile={int(driven_distance/1.6)}")

    except:
        import traceback
        traceback.print_exc()
        pass

    return {"error": False, "response": "Logged"}