# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from uuid import uuid4
import json, time, math
import requests
from datetime import datetime

from app import app, config
from db import newconn
from functions import *

from random import randint
from dateutil import parser

import threading

GIFS = config.delivery_gifs

def UpdateTelemetry(steamid, userid, logid, starttime, endtime):
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT uuid FROM temptelemetry WHERE steamid = {steamid} AND timestamp > {int(starttime)} AND timestamp < {int(endtime)} LIMIT 1")
    p = cur.fetchall()
    if len(p) > 0:
        jobuuid = p[0][0]
        cur.execute(f"SELECT x, y, z, game, mods, timestamp FROM temptelemetry WHERE uuid = '{jobuuid}'")
        t = cur.fetchall()
        data = f"{t[0][3]},{t[0][4]},v4;"
        lastx = 0
        lastz = 0
        idle = 0
        for tt in t:
            if round(tt[0]) - lastx == 0 and round(tt[2]) - lastz == 0:
                idle += 1
                continue
            else:
                if idle > 0:
                    data += f"idle{idle};"
                    idle = 0
            data += f"{b62encode(round(tt[0]) - lastx)},{b62encode(round(tt[2]) - lastz)};"
            lastx = round(tt[0])
            lastz = round(tt[2])
        for _ in range(3):
            try:
                conn = newconn()
                cur = conn.cursor()
                cur.execute(f"SELECT logid FROM telemetry WHERE logid = {logid}")
                p = cur.fetchall()
                if len(p) > 0:
                    break
                cur.execute(f"INSERT INTO telemetry VALUES ({logid}, '{jobuuid}', {userid}, '{data}')")
                conn.commit()
                break
            except:
                continue
        conn = newconn()
        cur = conn.cursor()
        cur.execute(f"DELETE FROM temptelemetry WHERE uuid = '{jobuuid}'")
        conn.commit()

@app.post(f"/{config.vtcprefix}/navio")
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
        cur.execute(f"SELECT userid, name, discordid FROM user WHERE steamid = '{steamid}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "User not found."}
        userid = t[0][0]
        name = t[0][1].replace("'", "''")
        discordid = t[0][2]
        await AuditLog(-999, f"Member resigned from Navio: **{name}** (`{discordid}`)")
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
    navioid = d["data"]["object"]["id"]

    cur.execute(f"SELECT logid FROM dlog WHERE navioid = {navioid}")
    o = cur.fetchall()
    if len(o) > 0:
        return {"error": True, "descriptor": "Already logged"}

    driven_distance = float(d["data"]["object"]["driven_distance"])
    fuel_used = d["data"]["object"]["fuel_used"]
    game = d["data"]["object"]["game"]["short_name"]
    munitint = 1 # euro
    if not game.startswith("e"):
        munitint = 2 # dollar
    revenue = 0
    xp = 0
    isdelivered = 0
    offence = 0
    if e == "job.delivered":
        revenue = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
        isdelivered = 1
        xp = d["data"]["object"]["events"][-1]["meta"]["earned_xp"]
        meta_distance = int(d["data"]["object"]["events"][-1]["meta"]["distance"])
        if driven_distance < 0 or driven_distance > meta_distance * 1.5:
            driven_distance = 0
    else:
        revenue = -float(d["data"]["object"]["events"][-1]["meta"]["penalty"])
        driven_distance = 0

    allevents = d["data"]["object"]["events"]
    for eve in allevents:
        if eve["type"] == "fine":
            offence += int(eve["meta"]["amount"])
    revenue -= offence
    
    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"] * 3.6 # m/s => km/h
    starttime = parser.parse(d["data"]["object"]["start_time"]).timestamp()
    endtime = parser.parse(d["data"]["object"]["stop_time"]).timestamp()
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtlogid'")
    t = cur.fetchall()
    logid = int(t[0][0])
    threading.Thread(target=UpdateTelemetry,args=(steamid, userid, logid, starttime, endtime, )).start()
    
    cur.execute(f"UPDATE settings SET sval = {logid+1} WHERE skey = 'nxtlogid'")
    cur.execute(f"UPDATE driver SET totjobs = totjobs + 1, distance = distance + {driven_distance}, fuel = fuel + {fuel_used}, xp = xp + {xp} WHERE userid = {userid}")
    cur.execute(f"INSERT INTO dlog VALUES ({logid}, {userid}, '{b64e(json.dumps(d))}', {top_speed}, {int(time.time())}, \
        {isdelivered}, {revenue}, {munitint}, {fuel_used}, {driven_distance}, {navioid})")
    conn.commit()

    if config.delivery_log_channel_id != 0:
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
            headers = {"Authorization": f"Bot {config.bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{config.delivery_log_channel_id}/messages"
            munit = "€"
            if not game.startswith("e"):
                munit = "$"
            if e == "job.delivered":
                k = randint(0, len(GIFS)-1)
                if config.distance_unit == "imperial":
                    r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Job Completed - #{logid}", 
                            "url": f"https://{config.dhdomain}/delivery?logid={logid}",
                            "fields": [{"name": "From", "value": source_company + ", " + source_city, "inline": True},
                                    {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                                    {"name": "Distance", "value": f"{int(driven_distance * 0.621371)} mile", "inline": True},
                                    {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": False},
                                    {"name": "Fuel Cost", "value": f"{int(fuel_used * 0.26417205)} gallon", "inline": True},
                                    {"name": "Revenue", "value": f"{munit}{revenue}", "inline": True},
                                    {"name": "XP Earned", "value": f"{xp}", "inline": True}],
                            "footer": {"text": username}, "color": config.intcolor,\
                                "timestamp": str(datetime.now()), "image": {"url": GIFS[k]}, "color": config.intcolor}}), timeout=3)
                elif config.distance_unit == "metric":
                    r = requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Job Completed - #{logid}", 
                            "url": f"https://{config.dhdomain}/delivery?logid={logid}",
                            "fields": [{"name": "From", "value": source_company + ", " + source_city, "inline": True},
                                    {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                                    {"name": "Distance", "value": f"{int(driven_distance)} kilometre", "inline": True},
                                    {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": False},
                                    {"name": "Fuel Cost", "value": f"{int(fuel_used)} litre", "inline": True},
                                    {"name": "Revenue", "value": f"{munit}{revenue}", "inline": True},
                                    {"name": "XP Earned", "value": f"{xp}", "inline": True}],
                            "footer": {"text": username}, "color": config.intcolor,\
                                "timestamp": str(datetime.now()), "image": {"url": GIFS[k]}, "color": config.intcolor}}), timeout=3)
                cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
                p = cur.fetchall()
                udiscordid = p[0][0]

        except:
            import traceback
            traceback.print_exc()
            pass

    return {"error": False, "response": "Logged"}