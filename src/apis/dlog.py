# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from fastapi.responses import StreamingResponse
import json, time, math
from typing import Optional
from datetime import datetime
import requests
from io import BytesIO
import zlib, base64

from app import app, config
from db import newconn
from functions import *
import multilang as ml

DIVISIONPNT = {}
for division in config.divisions:
    DIVISIONPNT[division["id"]] = division["point"]

@app.get(f"/{config.vtcprefix}/dlog/stats")
async def dlogStats(request: Request, response: Response):
    rl = ratelimit(request.client.host, 'GET /dlog/stats', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

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

    profit = {"euro": europrofit, "dollar": dollarprofit}
    newprofit = {"euro": neweuroprofit, "dollar": newdollarprofit}

    cur.execute(f"SELECT SUM(fuel) FROM dlog WHERE userid >=0")
    fuel = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(fuel) FROM dlog WHERE userid >=0 AND timestamp >= {int(time.time())-86400}")
    newfuel = cur.fetchone()[0]
    if fuel is None:
        fuel = 0
    if newfuel is None:
        newfuel = 0
    fuel = int(fuel)
    newfuel = int(newfuel)

    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid >=0")
    distance = cur.fetchone()[0]
    cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid >=0 AND timestamp >= {int(time.time())-86400}")
    newdistance = cur.fetchone()[0]
    if distance is None:
        distance = 0
    if newdistance is None:
        newdistance = 0
    distance = int(distance)
    newdistance = int(newdistance)

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE unit = 1")
    ets2jobs = cur.fetchone()[0]
    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE unit = 2")
    atsjobs = cur.fetchone()[0]
    
    cur.execute(f"SELECT userid, SUM(distance) FROM dlog WHERE timestamp >= {int(time.time())-86400} AND userid >= 0 GROUP BY userid ORDER BY SUM(distance) DESC LIMIT 1")
    t = cur.fetchall()
    username = "/"
    avatar = ""
    userid = ""
    distance = 0
    dotdiscordid = 0
    if len(t) > 0:
        userid = t[0][0]
        distance = t[0][1]
        cur.execute(f"SELECT name, avatar, discordid FROM user WHERE userid = {userid}")
        p = cur.fetchall()
        if len(p) > 0:
            username = p[0][0]
            avatar = p[0][1]
            dotdiscordid = p[0][2]
        else:
            username = "Unknown Driver"

    return {"error": False, "response": {"drivers": {"all": drivers, "new": newdrivers}, \
        "jobs": {"all": jobs, "new": newjobs, "ets2": ets2jobs, "ats": atsjobs}, \
        "profit": {"all": profit, "new": newprofit}, \
            "fuel": {"all": fuel, "new": newfuel}, "distance": {"all": distance, "new": newdistance}, 
                "driver_of_the_day": {"userid": userid, "discordid": str(dotdiscordid), "name": username, "avatar": avatar, "distance": int(distance)}}}

@app.get(f"/{config.vtcprefix}/dlog/chart")
async def dlogChart(request: Request, response: Response,
    scale: Optional[int] = 2, addup: Optional[bool] = False, quserid: Optional[int] = -1,
    authorization: Optional[str] = Header(None)):
    rl = ratelimit(request.client.host, 'GET /dlog/chart', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    if quserid != -1:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = 401
            return au

    conn = newconn()
    cur = conn.cursor()

    ret = []
    timerange = []
    if scale == 1:
        for i in range(24):
            starttime = int(time.time()) - ((i+1)*3600)
            endtime = starttime + 3600
            timerange.append((starttime, endtime))
    elif scale == 2:
        for i in range(7):
            starttime = int(time.time()) - ((i+1)*86400)
            endtime = starttime + 86400
            timerange.append((starttime, endtime))
    elif scale == 3:
        for i in range(30):
            starttime = int(time.time()) - ((i+1)*86400)
            endtime = starttime + 86400
            timerange.append((starttime, endtime))
    timerange = timerange[::-1]

    limit = ""
    if quserid != -1:
        limit = f"userid = {quserid} AND"

    basedistance = 0
    basefuel = 0
    baseeuro = 0
    basedollar = 0
    if addup:
        endtime = timerange[0][0]
        cur.execute(f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {endtime}")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            basedistance = int(t[0][0])
            basefuel = int(t[0][1])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {endtime} AND unit = 1")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            baseeuro = int(t[0][0])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {endtime} AND unit = 2")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            basedollar = int(t[0][0])

    for (starttime, endtime) in timerange:
        cur.execute(f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} timestamp >= {starttime} AND timestamp < {endtime}")
        t = cur.fetchall()
        distance = basedistance
        fuel = basefuel
        if len(t) > 0 and t[0][0] != None:
            distance += int(t[0][0])
            fuel += int(t[0][1])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= {starttime} AND timestamp < {endtime} AND unit = 1")
        t = cur.fetchall()
        euro = baseeuro
        if len(t) > 0 and t[0][0] != None:
            euro += int(t[0][0])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= {starttime} AND timestamp < {endtime} AND unit = 2")
        t = cur.fetchall()
        dollar = basedollar
        if len(t) > 0 and t[0][0] != None:
            dollar += int(t[0][0])
        profit = {"euro": euro, "dollar": dollar}
        ret.append({"starttime": starttime, "endtime": endtime, "distance": distance, "fuel": fuel, "profit": profit})
    
        if addup:
            basedistance = distance
            basefuel = fuel
            baseeuro = euro
            basedollar = dollar

    return {"error": False, "response": ret}

@app.get(f"/{config.vtcprefix}/dlog/leaderboard")
async def dlogLeaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, starttime: Optional[int] = -1, endtime: Optional[int] = -1, speedlimit: Optional[int] = 0, game: Optional[int] = 0, \
        noevent: Optional[bool] = False, nodivision: Optional[bool] = False, limituser: Optional[str] = ""):
    rl = ratelimit(request.client.host, 'GET /dlog/leaderboard', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()

    if page <= 0:
        page = 1

    limituser = limituser.split(",")
    while "" in limituser:
        limituser.remove("")
    if len(limituser) > 10:
        limituser = limituser[:10]

    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371

    if starttime != -1 and endtime != -1 or speedlimit != 0 or game != 0 or noevent or nodivision:
        if starttime > endtime:
            starttime, endtime = endtime, starttime
        if (starttime == -1 or endtime == -1):
            starttime = 0
            endtime = int(time.time())
        limit = ""
        if speedlimit != 0:
            limit = f" AND topspeed <= {int(speedlimit)}"
        gamelimit = ""
        if game == 1 or game == 2:
            gamelimit = f" AND unit = {game}"
        cur.execute(f"SELECT userid, distance FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} {limit} {gamelimit}")
        t = cur.fetchall()
        userdistance = {}
        for tt in t:
            if not tt[0] in userdistance.keys():
                userdistance[tt[0]] = tt[1]
            else:
                userdistance[tt[0]] += tt[1]
        userevent = {}
        if not noevent:
            cur.execute(f"SELECT attendee, eventpnt FROM event WHERE dts >= {starttime} AND dts <= {endtime}")
            t = cur.fetchall()
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
                rank[k] = round(userdistance[k] * ratio) + userevent[k]
            else:
                userevent[k] = 0
                rank[k] = round(userdistance[k] * ratio)
        for k in userevent.keys():
            if not k in rank.keys():
                rank[k] = userevent[k]
                userdistance[k] = 0

        rank = dict(sorted(rank.items(),key=lambda x:x[1]))
        rank = list(rank.keys())[::-1]

        cur.execute(f"SELECT logid FROM dlog WHERE timestamp >= {starttime} ORDER BY logid ASC")
        t = cur.fetchall()
        firstlogid = 0
        if len(t) > 0:
            firstlogid = t[0][0]

        ret = []
        users = []
        for userid in rank:
            cur.execute(f"SELECT name, discordid, avatar, roles FROM user WHERE userid = {userid} AND userid >= 0")
            p = cur.fetchall()
            if len(p) == 0:
                continue
            roles = p[0][3].split(",")
            while "" in roles:
                roles.remove("")
            ok = False
            for i in roles:
                if int(i) in config.perms.driver:
                    ok = True
            if not ok:
                continue
            if not noevent:
                cur.execute(f"SELECT distance * {ratio} + eventpnt FROM driver WHERE userid = {userid}")
            else:
                cur.execute(f"SELECT distance * {ratio} FROM driver WHERE userid = {userid}")
            o = cur.fetchall()
            totnolimit = 0
            if len(o) > 0:
                totnolimit = int(o[0][0])
            divisionpnt = 0
            if not nodivision:
                cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {userid} AND status = 1 AND logid >= {firstlogid} GROUP BY divisionid")
                o = cur.fetchall()
                for oo in o:
                    if o[0][0] in DIVISIONPNT.keys():
                        divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
            users.append(userid)
            if str(userid) in limituser or len(limituser) == 0:
                ret.append({"userid": userid, "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], \
                    "distance": userdistance[userid], "eventpnt": userevent[userid], "divisionpnt": divisionpnt, "totalpnt": round(userdistance[userid] * ratio) + userevent[userid] + divisionpnt, "totnolimit": totnolimit + divisionpnt})

        cur.execute(f"SELECT userid, distance * {ratio} + eventpnt, distance, eventpnt FROM driver WHERE userid >= 0")
        t = cur.fetchall()
        for tt in t:
            userid = tt[0]
            if not userid in users:
                cur.execute(f"SELECT userid, name, discordid, avatar, roles FROM user WHERE userid = {userid}")
                p = cur.fetchall()
                roles = p[0][4].split(",")
                while "" in roles:
                    roles.remove("")
                ok = False
                for i in roles:
                    if int(i) in config.perms.driver:
                        ok = True
                if not ok:
                    continue
                userid = p[0][0]
                name = p[0][1]
                discordid = p[0][2]
                avatar = p[0][3]
                divisionpnt = 0
                if not nodivision:
                    cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {userid} AND status = 1 AND logid >= 0 GROUP BY divisionid")
                    o = cur.fetchall()
                    for oo in o:
                        if o[0][0] in DIVISIONPNT.keys():
                            divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
                if str(userid) in limituser or len(limituser) == 0:
                    ret.append({"userid": userid, "name": name, "discordid": str(discordid), "avatar": avatar, \
                        "distance": 0, "eventpnt": 0, "divisionpnt": 0, "totalpnt": 0, "totnolimit": int(tt[1]) + divisionpnt})

        if (page - 1) * 10 >= len(ret):
            return {"error": False, "response": {"list": [], "page": page, "tot": len(ret)}}

        return {"error": False, "response": {"list": ret[(page - 1) * 10 : page * 10], "page": page, "tot": len(ret)}}

    cur.execute(f"SELECT userid, distance * {ratio} + eventpnt, distance, eventpnt FROM driver WHERE userid >= 0 ORDER BY distance * {ratio} + eventpnt DESC")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name, discordid, avatar, roles FROM user WHERE userid = {tt[0]} AND userid >= 0")
        p = cur.fetchall()
        if len(p) == 0:
            continue
        roles = p[0][3].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for i in roles:
            if int(i) in config.perms.driver:
                ok = True
        if not ok:
            continue
        divisionpnt = 0
        cur.execute(f"SELECT divisionid, COUNT(*) FROM division WHERE userid = {tt[0]} AND status = 1 AND logid >= 0 GROUP BY divisionid")
        o = cur.fetchall()
        for oo in o:
            if o[0][0] in DIVISIONPNT.keys():
                divisionpnt += o[0][1] * DIVISIONPNT[o[0][0]]
        cur.execute(f"SELECT status FROM division WHERE userid = {tt[0]} AND logid = -1")
        o = cur.fetchall()
        if len(o) > 0:
            divisionpnt += o[0][0]
        if str(tt[0]) in limituser or len(limituser) == 0:
            ret.append({"userid": tt[0], "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], "distance": tt[2], "eventpnt": tt[3], "divisionpnt": divisionpnt, "totalpnt": int(tt[1]), "totnolimit": int(tt[1]) + divisionpnt})

    if (page - 1) * 10 >= len(ret):
        return {"error": False, "response": {"list": [], "page": page, "tot": len(ret)}}

    cur.execute(f"SELECT COUNT(*) FROM driver WHERE userid >= 0")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret[(page - 1) * 10 : page * 10], "page": page, "tot": tot}}

@app.get(f"/{config.vtcprefix}/dlog/newdrivers")
async def dlogNewDriver(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /dlog/newdrivers', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}
        
    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au

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

@app.get(f"/{config.vtcprefix}/dlogs")
async def dlogs(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, speedlimit: Optional[int] = 0, quserid: Optional[int] = -1, starttime: Optional[int] = -1, endtime: Optional[int] = -1, game: Optional[int] = 0):
    rl = ratelimit(request.client.host, 'GET /dlogs', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = 401
            return au
        userid = au["userid"]
    
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

    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND unit = {game}"

    cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit, distance FROM dlog WHERE userid >= 0 {limit} {timelimit} {speedlimit} {gamelimit} ORDER BY timestamp DESC LIMIT {(page - 1) * 10}, 10")
    
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
        distance = tt[6]
        if distance < 0:
            distance = 0

        profit = tt[4]
        unit = tt[5]

        name = "Unknown"
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        if len(p) > 0:
            name = p[0][0]
        
        if userid == -1:
            name = "Anonymous"

        isdivision = False
        cur.execute(f"SELECT * FROM division WHERE logid = {tt[3]} AND status = 1 AND logid >= 0")
        p = cur.fetchall()
        if len(p) > 0:
            isdivision = True
        ret.append({"logid": tt[3], "userid": tt[0], "name": name, "distance": distance, \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": cargo_mass, "profit": profit, "unit": unit, "isdivision": isdivision, "timestamp": tt[2]})

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE userid >= 0 {limit} {timelimit} {speedlimit} {gamelimit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}

@app.get(f"/{config.vtcprefix}/dlog")
async def dlog(logid: int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /dlog', 60, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = 401
            return au
        userid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT userid, data, timestamp, distance FROM dlog WHERE userid >= 0 AND logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}
    data = json.loads(b64d(t[0][1]))
    del data["data"]["object"]["driver"]
    distance = t[0][3]
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
        telemetry = base64.b64decode(telemetry)
        telemetry = zlib.decompress(telemetry).decode()
        orgt = telemetry
        ver = "v1"
        telemetry = telemetry.split(";")
        t1 = telemetry[1].split(",")
        if len(t1) == 2:
            ver = "v2"
        basic = telemetry[0].split(",")
        if len(basic) == 3:
            if basic[2] == "v3":
                ver = "v3"
            elif basic[2] == "v4":
                ver = "v4"
            elif basic[2] == "v5":
                ver = "v5"
        telemetry = ver + orgt

    if userid == -1:
        name = "Anonymous"

    return {"error": False, "response": {"logid": logid, "userid": t[0][0], "name": name, "loggeddistance": distance, "data": data, "timestamp": t[0][2], "telemetry": telemetry}}

@app.get(f"/{config.vtcprefix}/dlog/export")
async def dlogExport(request: Request, response: Response, authorization: str = Header(None), \
        starttime: Optional[int] = -1, endtime: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /dlog/export', 3600, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}
        
    au = auth(authorization, request)
    if au["error"]:
        response.status_code = 401
        return au
    
    conn = newconn()
    cur = conn.cursor()

    if starttime == -1 or endtime == -1:
        starttime = 0
        endtime = int(time.time())

    f = BytesIO()
    f.write(b"logid, isdelivered, game, userid, username, source_company, source_city, destination_company, destination_city, distance, fuel, top_speed, truck, cargo, cargo_mass, damage, net_profit, profit, expense, offence, xp, time\n")
    cur.execute(f"SELECT logid, userid, topspeed, unit, profit, unit, fuel, distance, data, isdelivered, timestamp FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} AND userid >= 0")
    d = cur.fetchall()
    for dd in d:
        userid = dd[1]
        game = "unknown"
        if dd[3] == 1:
            game = "ets2"
        elif dd[3] == 2:
            game = "ats"
        
        cur.execute(f"SELECT name FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        name = "unknown"
        if len(t) > 0:
            name = t[0][0]

        data = json.loads(b64d(dd[8]))
        
        source_city = data["data"]["object"]["source_city"]
        source_company = data["data"]["object"]["source_company"]
        destination_city = data["data"]["object"]["destination_city"]
        destination_company = data["data"]["object"]["destination_company"]
        if source_city is None:
            source_city = ""
        else:
            source_city = source_city["name"]
        if source_company is None:
            source_company = ""
        else:
            source_company = source_company["name"]
        if destination_city is None:
            destination_city = ""
        else:
            destination_city = destination_city["name"]
        if destination_company is None:
            destination_company = ""
        else:
            destination_company = destination_company["name"]
        cargo = data["data"]["object"]["cargo"]["name"]
        cargo_mass = data["data"]["object"]["cargo"]["mass"]
        truckd = data["data"]["object"]["truck"]
        truck = ""
        if truckd["brand"] is None or truckd["name"] is None:
            truck = "Unknown"
        else:
            truck = truckd["brand"]["name"] + " " + truckd["name"]

        isdelivered = dd[9]
        profit = 0
        damage = 0
        xp = 0
        if isdelivered:
            profit = float(data["data"]["object"]["events"][-1]["meta"]["revenue"])
            damage = float(data["data"]["object"]["events"][-1]["meta"]["cargo_damage"])
            xp = float(data["data"]["object"]["events"][-1]["meta"]["earned_xp"])
        else:
            profit = -float(data["data"]["object"]["events"][-1]["meta"]["penalty"])
            damage = float(data["data"]["object"]["cargo"]["damage"])
        net_profit = profit
        allevents = data["data"]["object"]["events"]
        offence = 0
        expense = {"tollgate": 0, "ferry": 0, "train": 0}
        totalexpense = 0
        for eve in allevents:
            if eve["type"] == "fine":
                offence += int(eve["meta"]["amount"])
            elif eve["type"] in ["tollgate", "ferry", "train"]:
                expense[eve["type"]] += int(eve["meta"]["cost"])
                totalexpense += int(eve["meta"]["cost"])
        expensetxt = ""
        for k, v in expense.items():
            expensetxt += f"{k}: {v}, "
        expensetxt = expensetxt[:-2]
        net_profit = net_profit - offence - totalexpense
        
        data = [dd[0], isdelivered, game, userid, name, source_company, source_city, destination_company, destination_city, dd[7], dd[6], dd[2], truck, cargo, cargo_mass, damage, net_profit, profit, expensetxt, offence, xp, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dd[10]))]
        for i in range(len(data)):
            data[i] = '"' + str(data[i]) + '"'
        
        f.write(",".join(data).encode("utf-8"))
        f.write(b"\n")

    f.seek(0)
    
    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"

    return response