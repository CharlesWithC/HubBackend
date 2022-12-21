# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional
from io import BytesIO
import json, time, math
import traceback

from app import app, config
from db import newconn
from functions import *
import multilang as ml
from plugins.division import divisiontxt, DIVISIONPNT

# cache (works in each worker process)
cstats = {}
cleaderboard = {}
cnlleaderboard = {}
callusers = []
callusers_ts = 0

@app.get(f"/{config.abbr}/dlog")
async def getDlogInfo(request: Request, response: Response, authorization: str = Header(None), logid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /dlog', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    stoken = "guest"
    if authorization != None:
        stoken = authorization.split(" ")[1]
    userid = -1
    discordid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        userid = au["userid"]
        discordid = au["discordid"]
    
    if logid < 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT userid, data, timestamp, distance FROM dlog WHERE logid >= 0 AND logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}
    activityUpdate(discordid, f"dlog_{logid}")
    data = {}
    if t[0][1] != "":
        data = json.loads(decompress(t[0][1]))
    if "data" in data.keys():
        del data["data"]["object"]["driver"]
    distance = t[0][3]

    cur.execute(f"SELECT data FROM telemetry WHERE logid = {logid}")
    p = cur.fetchall()
    telemetry = ""
    if len(p) > 0:
        telemetry = decompress(p[0][0])
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

    division = ""
    cur.execute(f"SELECT divisionid FROM division WHERE logid = {logid} AND status = 1 AND logid >= 0")
    p = cur.fetchall()
    if len(p) != 0:
        division = str(p[0][0])

    challenge_record = []
    cur.execute(f"SELECT challengeid FROM challenge_record WHERE logid = {logid}")
    o = cur.fetchall()
    for oo in o:
        challenge_record.append(oo[0])

    userinfo = None
    if userid == -1 and config.privacy:
        userinfo = getUserInfo(privacy = True)
    else:
        userinfo = getUserInfo(userid = t[0][0], tell_deleted = True)
        if "is_deleted" in userinfo:
            userinfo = getUserInfo(-1)

    return {"error": False, "response": {"dlog": {"logid": str(logid), "user": userinfo, \
        "distance": str(distance), "division": division, "challenge_record": challenge_record, \
            "detail": data, "telemetry": telemetry, "timestamp": str(t[0][2])}}}

@app.delete(f"/{config.abbr}/dlog")
async def deleteDlog(request: Request, response: Response, authorization: str = Header(None), logid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'DELETE /dlog', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, required_permission = ["admin", "hrm", "hr", "delete_dlog"], allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if logid < 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}

    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}
    userid = t[0][0]
    
    cur.execute(f"DELETE FROM dlog WHERE logid = {logid}")
    conn.commit()

    await AuditLog(adminid, f"Deleted delivery `#{logid}`")

    discordid = getUserInfo(userid = userid)["discordid"]
    notification("dlog", discordid, ml.tr(request, "job_deleted", var = {"logid": logid}, force_lang = GetUserLanguage(discordid, "en")))

    return {"error": False}

@app.get(f"/{config.abbr}/dlog/list")
async def getDlogList(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "logid", order: Optional[str] = "desc", \
        speed_limit: Optional[int] = 0, userid: Optional[int] = -1, \
        start_time: Optional[int] = -1, end_time: Optional[int] = -1, game: Optional[int] = 0, status: Optional[int] = 1,\
        challenge: Optional[str] = "any", division: Optional[str] = "any"):
    rl = ratelimit(request, request.client.host, 'GET /dlog/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    quserid = userid
    
    stoken = "guest"
    if authorization != None:
        stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        userid = au["userid"]
        activityUpdate(au["discordid"], "dlogs")
    
    conn = newconn()
    cur = conn.cursor()

    if page <= 0:
        page = 1
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if not order_by in ["logid", "max_speed", "profit", "fuel", "distance"]:
        order_by = "logid"
        order = "desc"
    if not order in ["asc", "desc"]:
        order = "desc"
    if order_by == "max_speed":
        order_by = "topspeed"
    order = order.upper()

    limit = ""
    if quserid != -1:
        limit += f"AND dlog.userid = {quserid} "
    if challenge == "include":
        limit = limit
    elif challenge == "only":
        limit += f"AND dlog.logid IN (SELECT challenge_record.logid FROM challenge_record) "
    elif challenge == "none":
        limit += f"AND dlog.logid NOT IN (SELECT challenge_record.logid FROM challenge_record) "
    else:
        try:
            challengeid = int(challenge)
            limit += f"AND dlog.logid IN (SELECT challenge_record.logid FROM challenge_record WHERE challenge_record.challengeid = {challengeid}) "
        except:
            pass
    if division == "include":
        limit = limit
    elif division == "only":
        limit += f"AND dlog.logid IN (SELECT division.logid FROM division WHERE division.status = 1) "
    elif division == "none":
        limit += f"AND dlog.logid NOT IN (SELECT division.logid FROM division WHERE division.status = 1) "
    else:
        try:
            divisionid = int(division)
            limit += f"AND dlog.logid IN (SELECT division.logid FROM division WHERE division.status = 1 AND division.divisionid = {divisionid}) "
        except:
            pass
    
    timelimit = ""
    if start_time != -1 and end_time != -1:
        timelimit = f"AND dlog.timestamp >= {start_time} AND dlog.timestamp <= {end_time}"
    
    if speed_limit > 0:
        speed_limit = f" AND dlog.topspeed <= {speed_limit}"
    else:
        speed_limit = ""

    status_limit = ""
    if status == 1:
        status_limit = f" AND dlog.isdelivered = 1"
    elif status == 2:
        status_limit = f" AND dlog.isdelivered = 0"

    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND dlog.unit = {game}"

    cur.execute(f"SELECT dlog.userid, dlog.data, dlog.timestamp, dlog.logid, dlog.profit, dlog.unit, dlog.distance, dlog.isdelivered, division.divisionid, dlog.topspeed, dlog.fuel FROM dlog \
        LEFT JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        WHERE dlog.logid >= 0 {limit} {timelimit} {speed_limit} {gamelimit} {status_limit} ORDER BY dlog.{order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    ret = []
    t = cur.fetchall()
    for ti in range(len(t)):
        tt = t[ti]

        logid = tt[3]

        division_id = tt[8]
        division_name = ""
        division = {}
        if division_id == None:
            division_id = ""
        else:
            if division_id in divisiontxt.keys():
                division_name = divisiontxt[division_id]
            division = {"divisionid": str(division_id), "name": division_name}

        cur.execute(f"SELECT dlog.logid, challenge_info.challengeid, challenge.title FROM dlog \
            LEFT JOIN (SELECT challengeid, logid FROM challenge_record) challenge_info ON challenge_info.logid = dlog.logid \
            LEFT JOIN challenge ON challenge.challengeid = challenge_info.challengeid \
            WHERE dlog.logid = {logid}")
        p = cur.fetchall()
        challengeids = []
        challengenames = []
        for pp in p:
            if pp[1] is None or pp[2] is None:
                continue
            challengeids.append(pp[1])
            challengenames.append(pp[2])
        
        challenge = []
        for i in range(len(challengeids)):
            challenge.append({"challengeid": str(challengeids[i]), "name": challengenames[i]})

        data = {}
        if tt[1] != "":
            data = json.loads(decompress(tt[1]))
        source_city = "N/A"
        source_company = "N/A"
        destination_city = "N/A"
        destination_company = "N/A"
        if "data" in data.keys() and data["data"]["object"]["source_city"] != None:
            source_city = data["data"]["object"]["source_city"]["name"]
        if "data" in data.keys() and data["data"]["object"]["source_company"] != None:
            source_company = data["data"]["object"]["source_company"]["name"]
        if "data" in data.keys() and data["data"]["object"]["destination_city"] != None:
            destination_city = data["data"]["object"]["destination_city"]["name"]
        if "data" in data.keys() and data["data"]["object"]["destination_company"] != None:
            destination_company = data["data"]["object"]["destination_company"]["name"]
        cargo = "N/A"
        cargo_mass = 0
        if "data" in data.keys() and data["data"]["object"]["cargo"] != None:
            cargo = data["data"]["object"]["cargo"]["name"]
            cargo_mass = data["data"]["object"]["cargo"]["mass"]
        distance = tt[6]
        if distance < 0:
            distance = 0

        profit = tt[4]
        unit = tt[5]
        
        userinfo = getUserInfo(userid = tt[0])
        if userid == -1 and config.privacy:
            userinfo = getUserInfo(privacy = True)

        status = "1"
        if tt[7] == 0:
            status = "2"

        ret.append({"logid": str(logid), "user": userinfo, "distance": str(distance), \
            "max_speed": str(tt[9]), "fuel": str(tt[10]), \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": str(cargo_mass), "profit": str(profit), "unit": str(unit), \
                        "division": division, "challenge": challenge, \
                            "status": status, "timestamp": str(tt[2])})

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE logid >= 0 {limit} {timelimit} {speed_limit} {gamelimit} {status_limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.get(f"/{config.abbr}/dlog/statistics/summary")
async def getDlogStats(request: Request, response: Response, authorization: str = Header(None), \
        start_time: Optional[int] = -1, end_time: Optional[int] = -1, userid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /dlog/statistics/summary', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if start_time == -1 or end_time == -1:
        start_time = 0
        end_time = max(int(time.time()), 32503651200)

    quser = ""
    if userid != -1:
        if config.privacy:
            au = auth(authorization, request, allow_application_token = True)
            if au["error"]:
                response.status_code = au["code"]
                del au["code"]
                return au
        quser = f"userid = {userid} AND"

    # cache
    global cstats
    l = list(cstats.keys())
    for ll in l:
        if ll < int(time.time()) - 120:
            del cstats[ll]
        else:
            tt = cstats[ll]
            for t in tt:
                if abs(t["start_time"] - start_time) <= 120 and abs(t["end_time"] - end_time) <= 120 and t["userid"] == userid:
                    ret = t["result"]
                    ret["cache"] = str(ll)
                    return {"error": False, "response": ret}

    conn = newconn()
    cur = conn.cursor()

    ret = {}
    # driver
    totdid = []
    newdid = []
    totdrivers = 0
    newdrivers = 0
    for rid in config.perms.driver:
        cur.execute(f"SELECT userid FROM user WHERE {quser} userid >= 0 AND join_timestamp <= {end_time} AND roles LIKE '%,{rid},%'")
        t = cur.fetchall()
        for tt in t:
            if not tt[0] in totdid:
                totdid.append(tt[0])
                totdrivers += 1
        cur.execute(f"SELECT userid FROM user WHERE {quser} userid >= 0 AND join_timestamp >= {start_time} AND join_timestamp <= {end_time} AND roles LIKE '%,{rid},%'")
        t = cur.fetchall()
        for tt in t:
            if not tt[0] in newdid:
                newdid.append(tt[0])
                newdrivers += 1

    ret["driver"] = {"tot": str(totdrivers), "new": str(newdrivers)}
    
    # job / delivered / cancelled
    item = {"job": "COUNT(*)", "distance": "SUM(distance)", "fuel": "SUM(fuel)"}
    for key in item.keys():
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} timestamp <= {end_time}")
        tot = cur.fetchone()[0]
        tot = 0 if tot is None else int(tot)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} timestamp >= {start_time} AND timestamp <= {end_time}")
        new = cur.fetchone()[0]
        new = 0 if new is None else int(new)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 1 AND timestamp <= {end_time}")
        totets2 = cur.fetchone()[0]
        totets2 = 0 if totets2 is None else int(totets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newets2 = cur.fetchone()[0]
        newets2 = 0 if newets2 is None else int(newets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 2 AND timestamp <= {end_time}")
        totats = cur.fetchone()[0]
        totats = 0 if totats is None else int(totats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newats = cur.fetchone()[0]
        newats = 0 if newats is None else int(newats)

        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND timestamp <= {end_time}")
        totdelivered = cur.fetchone()[0]
        totdelivered = 0 if totdelivered is None else int(totdelivered)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newdelivered = cur.fetchone()[0]
        newdelivered = 0 if newdelivered is None else int(newdelivered)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp <= {end_time}")
        totdelivered_ets2 = cur.fetchone()[0]
        totdelivered_ets2 = 0 if totdelivered_ets2 is None else int(totdelivered_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newdelivered_ets2 = cur.fetchone()[0]
        newdelivered_ets2 = 0 if newdelivered_ets2 is None else int(newdelivered_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp <= {end_time}")
        totdelivered_ats = cur.fetchone()[0]
        totdelivered_ats = 0 if totdelivered_ats is None else int(totdelivered_ats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newdelivered_ats = cur.fetchone()[0]
        newdelivered_ats = 0 if newdelivered_ats is None else int(newdelivered_ats)

        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND timestamp <= {end_time}")
        totcancelled = cur.fetchone()[0]
        totcancelled = 0 if totcancelled is None else int(totcancelled)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newcancelled = cur.fetchone()[0]
        newcancelled = 0 if newcancelled is None else int(newcancelled)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp <= {end_time}")
        totcancelled_ets2 = cur.fetchone()[0]
        totcancelled_ets2 = 0 if totcancelled_ets2 is None else int(totcancelled_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newcancelled_ets2 = cur.fetchone()[0]
        newcancelled_ets2 = 0 if newcancelled_ets2 is None else int(newcancelled_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp <= {end_time}")
        totcancelled_ats = cur.fetchone()[0]
        totcancelled_ats = 0 if totcancelled_ats is None else int(totcancelled_ats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
        newcancelled_ats = cur.fetchone()[0]
        newcancelled_ats = 0 if newcancelled_ats is None else int(newcancelled_ats)

        ret[key] = {"all": {"sum": {"tot": str(tot), "new": str(new)}, \
            "ets2": {"tot": str(totets2), "new": str(newets2)}, \
            "ats": {"tot": str(totats), "new": str(newats)}}, \
            "delivered": {"sum": {"tot": str(totdelivered), "new": str(newdelivered)}, \
                    "ets2": {"tot": str(totdelivered_ets2), "new": str(newdelivered_ets2)}, \
                    "ats": {"tot": str(totdelivered_ats), "new": str(newdelivered_ats)}}, \
                "cancelled": {"sum": {"tot": str(totcancelled), "new": str(newcancelled)}, \
                    "ets2": {"tot": str(totcancelled_ets2), "new": str(newcancelled_ets2)}, \
                    "ats": {"tot": str(totcancelled_ats), "new": str(newcancelled_ats)}}}

    # profit
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 1 AND timestamp <= {end_time}")
    toteuroprofit = cur.fetchone()[0]
    toteuroprofit = 0 if toteuroprofit is None else int(toteuroprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    neweuroprofit = cur.fetchone()[0]
    neweuroprofit = 0 if neweuroprofit is None else int(neweuroprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 2 AND timestamp <= {end_time}")
    totdollarprofit = cur.fetchone()[0]
    totdollarprofit = 0 if totdollarprofit is None else int(totdollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    newdollarprofit = cur.fetchone()[0]
    newdollarprofit = 0 if newdollarprofit is None else int(newdollarprofit)
    allprofit = {"tot": {"euro": str(toteuroprofit), "dollar": str(totdollarprofit)}, \
        "new": {"euro": str(neweuroprofit), "dollar": str(newdollarprofit)}}

    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp <= {end_time}")
    totdelivered_europrofit = cur.fetchone()[0]
    totdelivered_europrofit = 0 if totdelivered_europrofit is None else int(totdelivered_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    newdelivered_europrofit = cur.fetchone()[0]
    newdelivered_europrofit = 0 if newdelivered_europrofit is None else int(newdelivered_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp <= {end_time}")
    totdelivered_dollarprofit = cur.fetchone()[0]
    totdelivered_dollarprofit = 0 if totdelivered_dollarprofit is None else int(totdelivered_dollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    newdelivered_dollarprofit = cur.fetchone()[0]
    newdelivered_dollarprofit = 0 if newdelivered_dollarprofit is None else int(newdelivered_dollarprofit)
    deliveredprofit = {"tot": {"euro": str(totdelivered_europrofit), "dollar": str(totdelivered_dollarprofit)}, \
        "new": {"euro": str(newdelivered_europrofit), "dollar": str(newdelivered_dollarprofit)}}
    
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp <= {end_time}")
    totcancelled_europrofit = cur.fetchone()[0]
    totcancelled_europrofit = 0 if totcancelled_europrofit is None else int(totcancelled_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    newcancelled_europrofit = cur.fetchone()[0]
    newcancelled_europrofit = 0 if newcancelled_europrofit is None else int(newcancelled_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp <= {end_time}")
    totcancelled_dollarprofit = cur.fetchone()[0]
    totcancelled_dollarprofit = 0 if totcancelled_dollarprofit is None else int(totcancelled_dollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp >= {start_time} AND timestamp <= {end_time}")
    newcancelled_dollarprofit = cur.fetchone()[0]
    newcancelled_dollarprofit = 0 if newcancelled_dollarprofit is None else int(newcancelled_dollarprofit)
    cancelledprofit = {"tot": {"euro": str(totcancelled_europrofit), "dollar": str(totcancelled_dollarprofit)}, \
        "new": {"euro": str(newcancelled_europrofit), "dollar": str(newcancelled_dollarprofit)}}
    
    ret["profit"] = {"all": allprofit, "delivered": deliveredprofit, "cancelled": cancelledprofit}

    ts = int(time.time())
    if not ts in cstats.keys():
        cstats[ts] = []
    cstats[ts].append({"start_time": start_time, "end_time": end_time, "userid": userid, "result": ret})

    ret["cache"] = "-1"

    return {"error": False, "response": ret}

@app.get(f"/{config.abbr}/dlog/statistics/chart")
async def getDlogChart(request: Request, response: Response, authorization: Optional[str] = Header(None), \
        ranges: Optional[int] = 30, interval: Optional[int] = 86400, end_time: Optional[int] = -1, \
        sum_up: Optional[bool] = False, userid: Optional[int] = -1):
    rl = ratelimit(request, request.client.host, 'GET /dlog/statistics/chart', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    quserid = userid
    if quserid != -1:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au

    conn = newconn()
    cur = conn.cursor()

    if ranges > 100:
        ranges = 100
    elif ranges <= 0:
        ranges = 30
    
    if interval > 31536000: # a year
        interval = 31536000
    elif interval < 60:
        interval = 60
    
    if end_time < 0:
        end_time = int(time.time())

    ret = []
    timerange = []
    for i in range(ranges):
        r_start_time = end_time - ((i+1)*interval)
        if r_start_time <= 0:
            break
        r_end_time = r_start_time + interval
        timerange.append((r_start_time, r_end_time))
    timerange = timerange[::-1]

    limit = ""
    if quserid != -1:
        limit = f"userid = {quserid} AND"

    basedistance = 0
    basefuel = 0
    baseeuro = 0
    basedollar = 0
    if sum_up:
        end_time = timerange[0][0]
        cur.execute(f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {end_time}")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            basedistance = int(t[0][0])
            basefuel = int(t[0][1])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {end_time} AND unit = 1")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            baseeuro = int(t[0][0])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= 0 AND timestamp < {end_time} AND unit = 2")
        t = cur.fetchall()
        if len(t) > 0 and t[0][0] != None:
            basedollar = int(t[0][0])

    for (start_time, end_time) in timerange:
        cur.execute(f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} timestamp >= {start_time} AND timestamp < {end_time}")
        t = cur.fetchall()
        distance = basedistance
        fuel = basefuel
        if len(t) > 0 and t[0][0] != None:
            distance += int(t[0][0])
            fuel += int(t[0][1])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= {start_time} AND timestamp < {end_time} AND unit = 1")
        t = cur.fetchall()
        euro = baseeuro
        if len(t) > 0 and t[0][0] != None:
            euro += int(t[0][0])
        cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {limit} timestamp >= {start_time} AND timestamp < {end_time} AND unit = 2")
        t = cur.fetchall()
        dollar = basedollar
        if len(t) > 0 and t[0][0] != None:
            dollar += int(t[0][0])
        profit = {"euro": str(euro), "dollar": str(dollar)}
        ret.append({"start_time": str(start_time), "end_time": str(end_time), "distance": str(distance), "fuel": str(fuel), "profit": profit})
    
        if sum_up:
            basedistance = distance
            basefuel = fuel
            baseeuro = euro
            basedollar = dollar

    return {"error": False, "response": ret}

@app.get(f"/{config.abbr}/dlog/leaderboard")
async def getDlogLeaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        start_time: Optional[int] = -1, end_time: Optional[int] = -1, \
        speed_limit: Optional[int] = 0, game: Optional[int] = 0, \
        point_types: Optional[str] = "distance,challenge,event,division,myth", userids: Optional[str] = ""):
    rl = ratelimit(request, request.client.host, 'GET /dlog/leaderboard', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    activityUpdate(au["discordid"], "leaderboard")

    limittype = point_types
    limituser = userids

    usecache = False
    nlusecache = False
    cachetime = -1
    nlcachetime = -1

    userdistance = {}
    userchallenge = {}
    userevent = {}
    userdivision = {}
    usermyth = {}

    nluserdistance = {}
    nluserchallenge = {}
    nluserevent = {}
    nluserdivision = {}
    nlusermyth = {}
    nlusertot = {}
    nlusertot_id = []
    nlrank = 1
    nluserrank = {}

    # cache
    global cleaderboard
    l = list(cleaderboard.keys())
    for ll in l:
        if ll < int(time.time()) - 120:
            del cleaderboard[ll]
        else:
            tt = cleaderboard[ll]
            for t in tt:
                if abs(t["start_time"] - start_time) <= 120 and abs(t["end_time"] - end_time) <= 120 and \
                        t["speed_limit"] == speed_limit and t["game"] == game:
                    usecache = True
                    cachetime = ll
                    userdistance = t["userdistance"]
                    userchallenge = t["userchallenge"]
                    userevent = t["userevent"]
                    userdivision = t["userdivision"]
                    usermyth = t["usermyth"]
                    break
    global cnlleaderboard
    l = list(cnlleaderboard.keys())
    for ll in l:
        if ll < int(time.time()) - 120:
            del cnlleaderboard[ll]
        else:
            t = cnlleaderboard[ll]
            nlusecache = True
            nlcachetime = ll
            nluserdistance = t["nluserdistance"]
            nluserchallenge = t["nluserchallenge"]
            nluserevent = t["nluserevent"]
            nluserdivision = t["nluserdivision"]
            nlusermyth = t["nlusermyth"]
            nlusertot = t["nlusertot"]
            nlusertot_id = list(nlusertot.keys())[::-1]
            nlrank = t["nlrank"]
            nluserrank = t["nluserrank"]

    conn = newconn()
    cur = conn.cursor()

    global callusers, callusers_ts
    if int(time.time()) - callusers_ts <= 300:
        allusers = callusers
    else:
        allusers = []
        cur.execute(f"SELECT userid, roles FROM user WHERE userid >= 0")
        t = cur.fetchall()
        for tt in t:
            roles = tt[1].split(",")
            while "" in roles:
                roles.remove("")
            ok = False
            for i in roles:
                if int(i) in config.perms.driver:
                    ok = True
            if not ok:
                continue
            allusers.append(tt[0])
        callusers = allusers
        callusers_ts = int(time.time())

    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371
    
    # validate parameter
    page = max(page, 1)
    page_size = max(min(page_size, 250), 1)
    (start_time, end_time) = (0, max(int(time.time()), 32503651200)) if start_time == -1 or end_time == -1 else (min(start_time, end_time), max(start_time, end_time))

    # set limits
    limituser = limituser.split(",")
    while "" in limituser:
        limituser.remove("")
    if len(limituser) > 10:
        limituser = limituser[:10]
    limit = ""
    if speed_limit > 0:
        limit = f" AND topspeed <= {speed_limit}"
    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND unit = {game}"
    
    if not usecache:
        ##### WITH LIMIT (Parameter)
        # calculate distance
        cur.execute(f"SELECT userid, SUM(distance) FROM dlog WHERE userid >= 0 AND timestamp >= {start_time} AND timestamp <= {end_time} {limit} {gamelimit} GROUP BY userid")
        t = cur.fetchall()
        for tt in t:
            if not tt[0] in allusers:
                continue
            if not tt[0] in userdistance.keys():
                userdistance[tt[0]] = tt[1]
            else:
                userdistance[tt[0]] += tt[1]
            userdistance[tt[0]] = int(userdistance[tt[0]])
        
        # calculate challenge
        cur.execute(f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid >= 0 AND timestamp >= {start_time} AND timestamp <= {end_time} GROUP BY userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in userchallenge.keys():
                userchallenge[oo[0]] = 0
            userchallenge[oo[0]] += oo[1]

        # calculate event
        cur.execute(f"SELECT attendee, points FROM event WHERE departure_timestamp >= {start_time} AND departure_timestamp <= {end_time}")
        t = cur.fetchall()
        for tt in t:
            attendees = tt[0].split(",")
            while "" in attendees:
                attendees.remove("")
            for ttt in attendees:
                attendee = int(ttt)
                if not attendee in allusers:
                    continue
                if not attendee in userevent.keys():
                    userevent[attendee] = tt[1]
                else:
                    userevent[attendee] += tt[1]
        
        # calculate division
        cur.execute(f"SELECT logid FROM dlog WHERE userid >= 0 AND logid >= 0 AND timestamp >= {start_time} AND timestamp <= {end_time} ORDER BY logid ASC LIMIT 1")
        t = cur.fetchall()
        firstlogid = -1
        if len(t) > 0:
            firstlogid = t[0][0]

        cur.execute(f"SELECT logid FROM dlog WHERE userid >= 0 AND logid >= 0 AND timestamp >= {start_time} AND timestamp <= {end_time} ORDER BY logid DESC LIMIT 1")
        t = cur.fetchall()
        lastlogid = -1
        if len(t) > 0:
            lastlogid = t[0][0]
        
        cur.execute(f"SELECT userid, divisionid, COUNT(*) FROM division WHERE userid >= 0 AND status = 1 AND logid >= {firstlogid} AND logid <= {lastlogid} GROUP BY divisionid, userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in userdivision.keys():
                userdivision[oo[0]] = 0
            if oo[1] in DIVISIONPNT.keys():
                userdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
        
        # calculate myth
        cur.execute(f"SELECT userid, SUM(point) FROM mythpoint WHERE userid >= 0 AND timestamp >= {start_time} AND timestamp <= {end_time} GROUP BY userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in usermyth.keys():
                usermyth[oo[0]] = 0
            usermyth[oo[0]] += oo[1]

    # calculate total point
    limittype = limittype.split(",")
    usertot = {}
    for k in userdistance.keys():
        if "distance" in limittype:
            usertot[k] = round(userdistance[k] * ratio)
    for k in userchallenge.keys():
        if not k in usertot.keys():
            usertot[k] = 0
        if "challenge" in limittype:
            usertot[k] += userchallenge[k]
    for k in userevent.keys():
        if not k in usertot.keys():
            usertot[k] = 0
        if "event" in limittype:
            usertot[k] += userevent[k]
    for k in userdivision.keys():
        if not k in usertot.keys():
            usertot[k] = 0
        if "division" in limittype:
            usertot[k] += userdivision[k]
    for k in usermyth.keys():
        if not k in usertot.keys():
            usertot[k] = 0
        if "myth" in limittype:
            usertot[k] += usermyth[k]

    usertot = dict(sorted(usertot.items(),key=lambda x:x[1]))
    usertot_id = list(usertot.keys())[::-1]

    # calculate rank
    userrank = {}
    rank = 0
    lastpnt = -1
    for userid in usertot_id:
        if lastpnt != usertot[userid]:
            rank += 1
            lastpnt = usertot[userid]
        userrank[userid] = rank
        usertot[userid] = int(usertot[userid])
    for userid in allusers:
        if not userid in userrank.keys():
            userrank[userid] = rank
            usertot[userid] = 0

    if not nlusecache:
        ##### WITHOUT LIMIT
        # calculate distance
        cur.execute(f"SELECT userid, SUM(distance) FROM dlog WHERE userid >= 0 GROUP BY userid")
        t = cur.fetchall()
        for tt in t:
            if not tt[0] in allusers:
                continue
            if not tt[0] in nluserdistance.keys():
                nluserdistance[tt[0]] = tt[1]
            else:
                nluserdistance[tt[0]] += tt[1]
            nluserdistance[tt[0]] = int(nluserdistance[tt[0]])

        # calculate challenge
        cur.execute(f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid >= 0 GROUP BY userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in nluserchallenge.keys():
                nluserchallenge[oo[0]] = 0
            nluserchallenge[oo[0]] += oo[1]

        # calculate event
        cur.execute(f"SELECT attendee, points FROM event")
        t = cur.fetchall()
        for tt in t:
            attendees = tt[0].split(",")
            while "" in attendees:
                attendees.remove("")
            for ttt in attendees:
                attendee = int(ttt)
                if not attendee in allusers:
                    continue
                if not attendee in nluserevent.keys():
                    nluserevent[attendee] = tt[1]
                else:
                    nluserevent[attendee] += tt[1]
        
        # calculate division    
        cur.execute(f"SELECT userid, divisionid, COUNT(*) FROM division WHERE userid >= 0 AND status = 1 GROUP BY divisionid, userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in nluserdivision.keys():
                nluserdivision[oo[0]] = 0
            if oo[1] in DIVISIONPNT.keys():
                nluserdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
        
        # calculate myth
        cur.execute(f"SELECT userid, SUM(point) FROM mythpoint WHERE userid >= 0 GROUP BY userid")
        o = cur.fetchall()
        for oo in o:
            if not oo[0] in allusers:
                continue
            if not oo[0] in nlusermyth.keys():
                nlusermyth[oo[0]] = 0
            nlusermyth[oo[0]] += oo[1]

        # calculate total point
        for k in nluserdistance.keys():
            nlusertot[k] = round(nluserdistance[k] * ratio)
        for k in nluserchallenge.keys():
            if not k in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserchallenge[k]
        for k in nluserevent.keys():
            if not k in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserevent[k]
        for k in nluserdivision.keys():
            if not k in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserdivision[k]
        for k in nlusermyth.keys():
            if not k in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nlusermyth[k]

        nlusertot = dict(sorted(nlusertot.items(),key=lambda x:x[1]))
        nlusertot_id = list(nlusertot.keys())[::-1]

        # calculate rank
        nluserrank = {}
        nlrank = 0
        lastpnt = -1
        for userid in nlusertot_id:
            if lastpnt != nlusertot[userid]:
                nlrank += 1
                lastpnt = nlusertot[userid]
            nluserrank[userid] = nlrank
            nlusertot[userid] = int(nlusertot[userid])
        for userid in allusers:
            if not userid in nluserrank.keys():
                nluserrank[userid] = nlrank
                nlusertot[userid] = 0

    # order by usertot first, if usertot is the same, then order by nlusertot, if nlusertot is the same, then order by userid
    s = []
    for userid in nlusertot_id:
        if userid in usertot_id:
            s.append((userid, -usertot[userid], -nlusertot[userid]))
        else:
            s.append((userid, 0, -nlusertot[userid]))
    s.sort(key=lambda t: (t[1], t[2], t[0]))
    usertot_id = []
    for ss in s:
        usertot_id.append(ss[0])

    ret = []
    withpoint = []
    # drivers with points (WITH LIMIT)
    for userid in usertot_id:
        # check if have driver role
        if not userid in allusers:
            continue

        withpoint.append(userid)

        distance = 0
        challengepnt = 0
        eventpnt = 0
        divisionpnt = 0
        mythpnt = 0
        if userid in userdistance.keys():
            distance = userdistance[userid]
        if userid in userchallenge.keys():
            challengepnt = userchallenge[userid]
        if userid in userevent.keys():
            eventpnt = userevent[userid]
        if userid in userdivision.keys():
            divisionpnt = userdivision[userid]
        if userid in usermyth.keys():
            mythpnt = usermyth[userid]

        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"user": getUserInfo(userid = userid), \
                "points": {"distance": str(distance), "challenge": str(challengepnt), "event": str(eventpnt), \
                    "division": str(divisionpnt), "myth": str(mythpnt), "total": str(usertot[userid]), \
                    "rank": str(userrank[userid]), "total_no_limit": str(nlusertot[userid]), "rank_no_limit": str(nluserrank[userid])}})

    # drivers with points (WITHOUT LIMIT)
    for userid in nlusertot_id:
        if userid in withpoint:
            continue

        # check if have driver role
        if not userid in allusers:
            continue

        withpoint.append(userid)

        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"user": getUserInfo(userid = userid), \
                "points": {"distance": "0", "challenge": "0", "event": "0", "division": "0", "myth": "0", "total": "0", \
                "rank": str(rank), "total_no_limit": str(nlusertot[userid]), "rank_no_limit": str(nluserrank[userid])}})

    # drivers without ponts (EVEN WITHOUT LIMIT)
    for userid in allusers:
        if userid in withpoint:
            continue
        
        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"user": getUserInfo(userid = userid), 
                "points": {"distance": "0", "challenge": "0", "event": "0", "division": "0", "myth": "0", "total": "0", \
                    "rank": str(rank), "total_no_limit": "0", "rank_no_limit": str(nlrank)}})

    if not usecache:
        ts = int(time.time())
        if not ts in cleaderboard.keys():
            cleaderboard[ts] = []
        cleaderboard[ts].append({"start_time": start_time, "end_time": end_time, "speed_limit": speed_limit, "game": game,\
            "userdistance": userdistance, "userchallenge": userchallenge, "userevent": userevent, \
            "userdivision": userdivision, "usermyth": usermyth})

    if not nlusecache:
        ts = int(time.time())
        cnlleaderboard[ts]={"nluserdistance": nluserdistance, "nluserchallenge": nluserchallenge, \
            "nluserevent": nluserevent, "nluserdivision": nluserdivision, "nlusermyth": nlusermyth, \
            "nlusertot": nlusertot, "nlrank": nlrank, "nluserrank": nluserrank}

    if (page - 1) * page_size >= len(ret):
        return {"error": False, "response": {"list": [], "total_items": str(len(ret)), \
            "total_pages": str(int(math.ceil(len(ret) / page_size))), \
                "cache": str(cachetime), "cache_no_limit": str(nlcachetime)}}

    return {"error": False, "response": {"list": ret[(page - 1) * page_size : page * page_size], \
        "total_items": str(len(ret)), "total_pages": str(int(math.ceil(len(ret) / page_size))), \
            "cache": str(cachetime), "cache_no_limit": str(nlcachetime)}}

@app.get(f"/{config.abbr}/dlog/export")
async def getDlogExport(request: Request, response: Response, authorization: str = Header(None), \
        start_time: Optional[int] = -1, end_time: Optional[int] = -1, include_ids: Optional[bool] = False):
    rl = ratelimit(request, request.client.host, 'GET /dlog/export', 600, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    conn = newconn()
    cur = conn.cursor()

    if start_time == -1 or end_time == -1:
        start_time = 0
        end_time = max(int(time.time()), 32503651200)

    f = BytesIO()
    if not include_ids:
        f.write(b"logid, navioid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park\n")
    else:
        f.write(b"logid, navioid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park\n")
    cur.execute(f"SELECT dlog.logid, dlog.userid, dlog.topspeed, dlog.unit, dlog.profit, dlog.unit, dlog.fuel, dlog.distance, dlog.data, dlog.isdelivered, dlog.timestamp, division.divisionid, challenge_info.challengeid, challenge.title FROM dlog \
        LEFT JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        LEFT JOIN (SELECT challengeid, logid FROM challenge_record) challenge_info ON challenge_info.logid = dlog.logid \
        LEFT JOIN challenge ON challenge.challengeid = challenge_info.challengeid \
        WHERE dlog.timestamp >= {start_time} AND dlog.timestamp <= {end_time} AND dlog.logid >= 0")
    d = cur.fetchall()
    for di in range(len(d)):
        dd = d[di]
        logid = dd[0]

        division_id = dd[11]
        division = ""
        if division_id == None:
            division_id = ""
        else:
            if division_id in divisiontxt.keys():
                division = divisiontxt[division_id]

        challengeids = dd[12]
        challengenames = dd[13]
        if challengeids == None:
            challengeids = []
            challengenames = []
        else:
            challengeids = [str(dd[12])]
            challengenames = [dd[13]]
            while di + 1 < len(d):
                if d[di + 1][0] == logid: # same log => multiple challenge id
                    challengeids.append(str(d[di+1][12]))
                    challengenames.append(d[di+1][13])
                    di += 1
                else:
                    break
        
        challenge_id = ", ".join(challengeids)
        challenge = ", ".join(challengenames)

        navioid = 0
        game = ""
        if dd[3] == 1:
            game = "ets2"
        elif dd[3] == 2:
            game = "ats"

        time_submitted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dd[10]))
        start_time = "1970-01-01 00:00:00"
        stop_time = "1970-01-01 00:00:00"

        is_delivered = dd[9]

        user_id = dd[1]
        user = getUserInfo(userid = user_id, tell_deleted = True)
        username = user["name"]
        if "is_deleted" in user.keys():
            user_id = "-1"
            username = "Unknown"        

        source_city = ""
        source_city_id = ""
        source_company = ""
        source_company_id = ""
        destination_city = ""
        destination_city_id = ""
        destination_company = ""
        destination_company_id = ""

        logged_distance = dd[7]
        planned_distance = 0
        reported_distance = 0

        cargo = ""
        cargo_id = ""
        cargo_mass = 0
        cargo_damage = 0

        truck_brand = ""
        truck_brand_id = ""
        truck_name = ""
        truck_id = ""
        license_plate = ""
        license_plate_country = ""
        license_plate_country_id = ""
        
        fuel = dd[6]
        avg_fuel = 0
        if logged_distance != 0:
            avg_fuel = round(fuel / logged_distance * 100, 2)
        adblue = 0
        max_speed = dd[2]
        avg_speed = 0

        revenue = 0
        expense = ""
        offence = 0
        net_profit = dd[4]

        xp = 0

        is_special = 0
        is_late = 0
        has_police_enabled = 0
        market = ""
        multiplayer = ""
        auto_load = 0
        auto_park = 0

        if dd[8] != "":
            try:
                data = json.loads(decompress(dd[8]))["data"]["object"]
                last_event = data["events"][-1]
                
                navioid = data["id"]
                
                start_time = data["start_time"]
                stop_time = data["stop_time"]

                if data["source_city"] != None:
                    source_city = data["source_city"]["name"]
                    source_city_id = data["source_city"]["unique_id"]
                if data["source_company"] != None:
                    source_company = data["source_company"]["name"]
                    source_company_id = data["source_company"]["unique_id"]
                if data["destination_city"] != None:
                    destination_city = data["destination_city"]["name"]
                    destination_city_id = data["destination_city"]["unique_id"]
                if data["destination_company"] != None:
                    destination_company = data["destination_company"]["name"]
                    destination_company_id = data["destination_company"]["unique_id"]
                
                planned_distance = data["planned_distance"]
                if "distance" in last_event["meta"]:
                    reported_distance = last_event["meta"]["distance"]

                if data["cargo"] != None:
                    cargo = data["cargo"]["name"]
                    cargo_id = data["cargo"]["unique_id"]
                    cargo_mass = data["cargo"]["mass"]
                    cargo_damage = data["cargo"]["damage"]

                if data["truck"] != None:
                    truck = data["truck"]
                    if truck["brand"] != None:
                        truck_brand = truck["brand"]["name"]
                        truck_brand_id = truck["brand"]["unique_id"]
                    truck_name = truck["name"]
                    truck_id = truck["unique_id"]
                    license_plate = truck["license_plate"]
                    if truck["license_plate_country"] != None:
                        license_plate_country = truck["license_plate_country"]["name"]
                        license_plate_country_id = truck["license_plate_country"]["unique_id"]
                    avg_speed = truck["average_speed"]

                adblue = data["adblue_used"]

                if is_delivered:
                    revenue = float(last_event["meta"]["revenue"])
                    xp = float(last_event["meta"]["earned_xp"])
                    auto_load = last_event["meta"]["auto_load"]
                    auto_park = last_event["meta"]["auto_park"]
                else:
                    revenue = -float(last_event["meta"]["penalty"])
                
                expensedict = {"tollgate": 0, "ferry": 0, "train": 0, "total": 0}
                allevents = data["events"]
                for eve in allevents:
                    if eve["type"] == "fine":
                        offence += int(eve["meta"]["amount"])
                    elif eve["type"] in ["tollgate", "ferry", "train"]:
                        expensedict[eve["type"]] += int(eve["meta"]["cost"])
                        expensedict["total"] += int(eve["meta"]["cost"])
                for k, v in expensedict.items():
                    expense += f"{k}: {v}, "
                expense = expense[:-2]

                is_special = int(data["is_special"])
                is_late = int(data["is_late"])
                had_police_enabled = int(data["game"]["had_police_enabled"])
                market = data["market"]
                if data["multiplayer"] != None:
                    multiplayer = data["multiplayer"]["type"]

            except:
                traceback.print_exc()

        if not include_ids:
            data = [logid, navioid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park]
        else:
            data = [logid, navioid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park]

        for i in range(len(data)):
            data[i] = '"' + str(data[i]) + '"'
        
        f.write(",".join(data).encode("utf-8"))
        f.write(b"\n")

    f.seek(0)
    
    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"

    return response