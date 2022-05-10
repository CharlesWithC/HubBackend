# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import FastAPI, Response, Request, Header
import json, time, math
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

    cur.execute(f"SELECT COUNT(*) FROM driver")
    drivers = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM driver WHERE joints >= {int(time.time())-86400}")
    newdrivers = cur.fetchone()[0]

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE isdelivered = 1")
    jobs = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE isdelivered = 1 AND timestamp >= {int(time.time())-86400}")
    newjobs = cur.fetchone()[0]

    # euro profit
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE isdelivered = 1 AND unit = 1")
    europrofit = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE isdelivered = 1 AND unit = 1 AND timestamp >= {int(time.time())-86400}")
    neweuroprofit = cur.fetchone()[0]
    
    # dollar profit
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE isdelivered = 1 AND unit = 2")
    dollarprofit = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE isdelivered = 1 AND unit = 2 AND timestamp >= {int(time.time())-86400}")
    newdollarprofit = cur.fetchone()[0]

    if europrofit is None:
        europrofit = 0
    if dollarprofit is None:
        dollarprofit = 0
    if neweuroprofit is None:
        neweuroprofit = 0
    if newdollarprofit is None:
        newdollarprofit = 0

    cur.execute(f"SELECT SUM(fuel) FROM dlog")
    fuel = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(fuel) FROM dlog WHERE timestamp >= {int(time.time())-86400}")
    newfuel = cur.fetchone()[0]
    if fuel is None:
        fuel = 0
    if newfuel is None:
        newfuel = 0

    cur.execute(f"SELECT SUM(distance) FROM dlog")
    distance = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE timestamp >= {int(time.time())-86400}")
    newdistance = cur.fetchone()[0]
    if distance is None:
        distance = 0
    if newdistance is None:
        newdistance = 0

    return {"error": False, "response": {"drivers": drivers, "newdrivers": newdrivers, \
        "jobs": jobs, "newjobs": newjobs, "europrofit": europrofit, "dollarprofit": dollarprofit, \
        "neweuroprofit": neweuroprofit, "newdollarprofit": newdollarprofit, \
            "fuel": fuel, "newfuel": newfuel, "distance": distance, "newdistance": newdistance}}

@app.get("/atm/dlog/list")
async def dlogList(page: int, speedlimit: Optional[int] = 0):
    conn = newconn()
    cur = conn.cursor()
    if speedlimit == 0:
        cur.execute(f"SELECT userid, data, timestamp, logid FROM dlog ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
    else:
        cur.execute(f"SELECT userid, data, timestamp, logid FROM dlog WHERE topspeed <= {speedlimit} ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
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
        distance = data["data"]["object"]["driven_distance"]/1.6

        name = "Unknown Driver"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) > 0:
            name = p[0][0]

        ret.append({"logid": tt[3], "userid": tt[0], "name": name, "distance": distance, "source_city": source_city, "source_company": source_company, "destination_city": destination_city, "destination_company": destination_company, "cargo": cargo, "cargo_mass": cargo_mass, "timestamp": tt[2]})

    return {"error": False, "response": ret}

@app.get("/atm/dlog/detail")
async def dlogDetail(logid: int):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, data, timestamp FROM dlog WHERE logid = {logid}")
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