# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

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
async def dlotLeaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, starttime: Optional[int] = -1, endtime: Optional[int] = -1, speedlimit: Optional[int] = 0):

    if page <= 0:
        page = 1
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    if starttime != -1 and endtime != -1 or speedlimit != 0:
        if starttime > endtime:
            starttime, endtime = endtime, starttime
        if speedlimit != 0 and (starttime == -1 or endtime == -1):
            starttime = 0
            endtime = int(time.time())
        limit = ""
        if speedlimit != 0:
            limit = f" AND topspeed <= {int(speedlimit)}"
        cur.execute(f"SELECT userid, distance FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} {limit}")
        t = cur.fetchall()
        userdistance = {}
        for tt in t:
            if not tt[0] in userdistance.keys():
                userdistance[tt[0]] = tt[1]
            else:
                userdistance[tt[0]] += tt[1]
        cur.execute(f"SELECT attendee, eventpnt FROM event WHERE dts >= {starttime} AND dts <= {endtime}")
        t = cur.fetchall()
        userevent = {}
        for tt in t:
            attendees = tt[0].split(",")
            while "" in attendees:
                attendees.remove("")
            for ttt in attendees:
                attendee = int(ttt)
                if not attendee in userevent.keys():
                    userevent[attendee] = tt[1]
                else:
                    userevent[attendee] += tt[1]
        rank = {}
        for k in userdistance.keys():
            if k in userevent.keys():
                rank[k] = round(userdistance[k]/1.6) + userevent[k]
            else:
                userevent[k] = 0
                rank[k] = round(userdistance[k]/1.6)
        for k in userevent.keys():
            if not k in rank.keys():
                rank[k] = userevent[k]
                userdistance[k] = 0

        rank = dict(sorted(rank.items(),key=lambda x:x[1]))
        rank = list(rank.keys())[::-1]

        ret = []
        for userid in rank:
            cur.execute(f"SELECT name, discordid, avatar FROM user WHERE userid = {userid}")
            p = cur.fetchall()
            ret.append({"userid": userid, "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], \
                "distance": userdistance[userid], "eventpnt": userevent[userid], "totalpnt": round(userdistance[userid] / 1.6) + userevent[userid]})

        if (page - 1) * 10 >= len(ret):
            return {"error": False, "response": {"list": [], "page": page, "tot": len(ret)}}

        ret = ret[(page - 1) * 10 : page * 10]
        return {"error": False, "response": {"list": ret, "page": page, "tot": len(ret)}}

    cur.execute(f"SELECT userid, distance / 1.6 + eventpnt, distance, eventpnt FROM driver WHERE userid >= 0 AND (distance > 0 OR eventpnt > 0) ORDER BY distance / 1.6 + eventpnt DESC LIMIT {(page - 1) * 10}, 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name, discordid, avatar FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        ret.append({"userid": tt[0], "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], "distance": tt[2], "eventpnt": tt[3], "totalpnt": tt[1]})

    cur.execute(f"SELECT COUNT(*) FROM driver WHERE userid >= 0 AND (distance > 0 OR eventpnt > 0)")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get("/atm/dlog/newdrivers")
async def dlotNewDriver(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, joints FROM driver WHERE userid >= 0 ORDER BY joints DESC LIMIT 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name, discordid, avatar FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        ret.append({"userid": tt[0], "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], "joints": tt[1]})

    return {"error": False, "response": {"list": ret, "page": 1, "tot": 10}}

@app.get("/atm/dlog/list")
async def dlogList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, speedlimit: Optional[int] = 0, quserid: Optional[int] = -1, starttime: Optional[int] = -1, endtime: Optional[int] = -1):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    userid = -1
    if stoken != "guest":
        isapptoken = False
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
            t = cur.fetchall()
            if len(t) == 0:
                userid = -1
            isapptoken = True
        discordid = t[0][0]
        if not isapptoken:
            ip = t[0][1]
            orgiptype = 4
            if validators.ipv6(ip) == True:
                orgiptype = 6
            curiptype = 4
            if validators.ipv6(request.client.host) == True:
                curiptype = 6
            if orgiptype != curiptype:
                cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                conn.commit()
            else:
                if ip != request.client.host:
                    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                    conn.commit()
                    response.status_code = 401
                    return {"error": True, "descriptor": "401: Unauthroized"}
        cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            userid = -1
        userid = t[0][0]

    conn = newconn()
    cur = conn.cursor()
    if page <= 0:
        page = 1

    limit = ""
    if quserid != -1:
        limit = f"AND userid = {quserid}"
    
    timelimit = ""
    if starttime != -1 and endtime != -1:
        timelimit = f"AND timestamp >= {starttime} AND timestamp <= {endtime}"
    
    if speedlimit != 0:
        speedlimit = f" AND topspeed <= {int(speedlimit)}"
    else:
        speedlimit = ""

    cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit FROM dlog WHERE userid >= 0 {limit} {timelimit} {speedlimit} ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
    
    t = cur.fetchall()
    ret = []
    for tt in t:
        data = json.loads(b64d(tt[1]))
        source_city = "Unknown city"
        source_company = "Unknown company"
        destination_city = "Unknown city"
        destination_company = "Unknown company"
        if data["data"]["object"]["source_city"] != None:
            source_city = data["data"]["object"]["source_city"]["name"]
        if data["data"]["object"]["source_company"] != None:
            source_company = data["data"]["object"]["source_company"]["name"]
        if data["data"]["object"]["destination_city"] != None:
            destination_city = data["data"]["object"]["destination_city"]["name"]
        if data["data"]["object"]["destination_company"] != None:
            destination_company = data["data"]["object"]["destination_company"]["name"]
        cargo = data["data"]["object"]["cargo"]["name"]
        cargo_mass = data["data"]["object"]["cargo"]["mass"]
        distance = data["data"]["object"]["driven_distance"]

        profit = tt[4]
        unit = tt[5]

        name = "Unknown"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) > 0:
            name = p[0][0]
        
        if userid == -1:
            name = "Anonymous"

        ret.append({"logid": tt[3], "userid": tt[0], "name": name, "distance": distance, \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": cargo_mass, "profit": profit, "unit": unit, "timestamp": tt[2]})

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE userid >= 0 {limit} {timelimit} {speedlimit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get("/atm/dlog/detail")
async def dlogDetail(logid: int, request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    isapptoken = False
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        isapptoken = True
    discordid = t[0][0]
    if not isapptoken:
        ip = t[0][1]
        orgiptype = 4
        if validators.ipv6(ip) == True:
            orgiptype = 6
        curiptype = 4
        if validators.ipv6(request.client.host) == True:
            curiptype = 6
        if orgiptype != curiptype:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            conn.commit()
        else:
            if ip != request.client.host:
                cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                conn.commit()
                response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    if userid == -1:
        response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

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

    cur.execute(f"SELECT data FROM telemetry WHERE logid = {logid}")
    p = cur.fetchall()
    telemetry = ""
    if len(p) > 0:
        telemetry = p[0][0]

    return {"error": False, "response": {"logid": logid, "userid": t[0][0], "name": name, "data": data, "timestamp": t[0][2], "telemetry": telemetry}}