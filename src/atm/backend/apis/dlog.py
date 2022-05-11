# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
import json, time, math, validators
from typing import Optional
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *

@app.get("/atm/dlog/stats")
async def dlotStats():
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM driver WHERE userid >= 0")
    drivers = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM driver WHERE userid >= 0 AND joints >= {int(time.time())-86400}")
    newdrivers = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE userid >=0 AND isdelivered = 1")
    jobs = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE userid >=0 AND isdelivered = 1 AND timestamp >= {int(time.time())-86400}")
    newjobs = cur.fetchone()[0]

    # euro profit
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid >=0 AND unit = 1")
    europrofit = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid >=0 AND unit = 1 AND timestamp >= {int(time.time())-86400}")
    neweuroprofit = cur.fetchone()[0]
    
    # dollar profit
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid >=0 AND unit = 2")
    dollarprofit = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE userid >=0 AND unit = 2 AND timestamp >= {int(time.time())-86400}")
    newdollarprofit = cur.fetchone()[0]

    if europrofit is None:
        europrofit = 0
    if dollarprofit is None:
        dollarprofit = 0
    if neweuroprofit is None:
        neweuroprofit = 0
    if newdollarprofit is None:
        newdollarprofit = 0

    cur.execute(f"SELECT SUM(fuel) FROM dlog WHERE userid >=0")
    fuel = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(fuel) FROM dlog WHERE userid >=0 AND timestamp >= {int(time.time())-86400}")
    newfuel = cur.fetchone()[0]
    if fuel is None:
        fuel = 0
    if newfuel is None:
        newfuel = 0

    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid >=0")
    distance = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid >=0 AND timestamp >= {int(time.time())-86400}")
    newdistance = cur.fetchone()[0]
    if distance is None:
        distance = 0
    if newdistance is None:
        newdistance = 0

    return {"error": False, "response": {"drivers": drivers, "newdrivers": newdrivers, \
        "jobs": jobs, "newjobs": newjobs, "europrofit": europrofit, "dollarprofit": dollarprofit, \
        "neweuroprofit": neweuroprofit, "newdollarprofit": newdollarprofit, \
            "fuel": fuel, "newfuel": newfuel, "distance": distance, "newdistance": newdistance}}

@app.get("/atm/dlog/leaderboard")
async def dlotLeaderboard():
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, distance / 1.6 + eventpnt FROM driver WHERE userid >= 0 ORDER BY distance / 1.6 + eventpnt DESC LIMIT 20")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name, discordid, avatar FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) == 0:
            continue
        ret.append({"userid": tt[0], "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], "totalpnt": tt[1]})
    return {"error": False, "response": ret[:5]}

@app.get("/atm/dlog/newdrivers")
async def dlotNewDriver():
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, joints FROM driver WHERE userid >= 0 ORDER BY joints DESC LIMIT 20")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name, discordid, avatar FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) == 0:
            continue
        ret.append({"userid": tt[0], "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], "joints": tt[1]})
    return {"error": False, "response": ret[:5]}

@app.get("/atm/dlog/list")
async def dlogList(page: int, speedlimit: Optional[int] = 0):
    conn = newconn()
    cur = conn.cursor()
    if page <= 0:
        page = 1
    if speedlimit == 0:
        cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit FROM dlog WHERE userid >= 0 ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
    else:
        cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit FROM dlog WHERE userid >= 0 AND topspeed <= {speedlimit} ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        data = json.loads(b64d(tt[1]))
        source_city = data["data"]["object"]["source_city"]["name"]
        source_company = data["data"]["object"]["source_company"]["name"]
        destination_city = data["data"]["object"]["destination_city"]["name"]
        destination_company = data["data"]["object"]["destination_company"]["name"]
        cargo = data["data"]["object"]["cargo"]["name"]
        cargo_mass = data["data"]["object"]["cargo"]["mass"]
        distance = data["data"]["object"]["driven_distance"]

        profit = tt[4]
        unit = tt[5]

        name = "Unknown Driver"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) > 0:
            name = p[0][0]

        ret.append({"logid": tt[3], "userid": tt[0], "name": name, "distance": distance, \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": cargo_mass, "profit": profit, "unit": unit, "timestamp": tt[2]})

    cur.execute(f"SELECT COUNT(*) FROM dlog")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get("/atm/dlog/detail")
async def dlogDetail(logid: int):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, data, timestamp FROM dlog WHERE userid >= 0 AND logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "response": "Log not found"}
    data = json.loads(b64d(t[0][1]))
    name = "Unknown Driver"
    cur.execute(f"SELECT name FROM user WHERE userid = {t[0][0]}")
    p = cur.fetchall()
    if len(p) > 0:
        name = p[0][0]
    return {"error": False, "response": {"logid": logid, "userid": t[0][0], "name": name, "data": data, "timestamp": t[0][2]}}