# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from fastapi.responses import StreamingResponse
from typing import Optional
from datetime import datetime
from io import BytesIO
import json, time

from app import app, config
from db import newconn
from functions import *
import multilang as ml

DIVISIONPNT = {}
for division in config.divisions:
    DIVISIONPNT[int(division["id"])] = int(division["point"])

@app.get(f"/{config.vtc_abbr}/dlog/stats")
async def getDlogStats(request: Request, response: Response, starttime: Optional[int] = -1, endtime: Optional[int] = -1, userid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /dlog/stats', 180, 60)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    conn = newconn()
    cur = conn.cursor()

    if starttime == -1 or endtime == -1:
        starttime = 0
        endtime = int(time.time())

    quser = ""
    if userid != -1:
        if config.privacy:
            response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        quser = f"userid = {userid} AND"

    ret = {}
    # driver
    cur.execute(f"SELECT COUNT(*) FROM driver WHERE {quser} userid >= 0 AND joints <= {endtime}")
    totdrivers = cur.fetchone()[0]
    totdrivers = 0 if totdrivers is None else int(totdrivers)
    cur.execute(f"SELECT COUNT(*) FROM driver WHERE {quser} userid >= 0 AND joints >= {starttime} AND joints <= {endtime}")
    newdrivers = cur.fetchone()[0]
    newdrivers = 0 if newdrivers is None else int(newdrivers)

    ret["driver"] = {"tot": str(totdrivers), "new": str(newdrivers)}
    
    # job / delivered / cancelled
    item = {"job": "COUNT(*)", "distance": "SUM(distance)", "fuel": "SUM(fuel)"}
    for key in item.keys():
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} timestamp <= {endtime}")
        tot = cur.fetchone()[0]
        tot = 0 if tot is None else int(tot)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} timestamp >= {starttime} AND timestamp <= {endtime}")
        new = cur.fetchone()[0]
        new = 0 if new is None else int(new)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 1 AND timestamp <= {endtime}")
        totets2 = cur.fetchone()[0]
        totets2 = 0 if totets2 is None else int(totets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newets2 = cur.fetchone()[0]
        newets2 = 0 if newets2 is None else int(newets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 2 AND timestamp <= {endtime}")
        totats = cur.fetchone()[0]
        totats = 0 if totats is None else int(totats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newats = cur.fetchone()[0]
        newats = 0 if newats is None else int(newats)

        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND timestamp <= {endtime}")
        totdelivered = cur.fetchone()[0]
        totdelivered = 0 if totdelivered is None else int(totdelivered)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newdelivered = cur.fetchone()[0]
        newdelivered = 0 if newdelivered is None else int(newdelivered)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp <= {endtime}")
        totdelivered_ets2 = cur.fetchone()[0]
        totdelivered_ets2 = 0 if totdelivered_ets2 is None else int(totdelivered_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newdelivered_ets2 = cur.fetchone()[0]
        newdelivered_ets2 = 0 if newdelivered_ets2 is None else int(newdelivered_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp <= {endtime}")
        totdelivered_ats = cur.fetchone()[0]
        totdelivered_ats = 0 if totdelivered_ats is None else int(totdelivered_ats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newdelivered_ats = cur.fetchone()[0]
        newdelivered_ats = 0 if newdelivered_ats is None else int(newdelivered_ats)

        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND timestamp <= {endtime}")
        totcancelled = cur.fetchone()[0]
        totcancelled = 0 if totcancelled is None else int(totcancelled)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newcancelled = cur.fetchone()[0]
        newcancelled = 0 if newcancelled is None else int(newcancelled)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp <= {endtime}")
        totcancelled_ets2 = cur.fetchone()[0]
        totcancelled_ets2 = 0 if totcancelled_ets2 is None else int(totcancelled_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
        newcancelled_ets2 = cur.fetchone()[0]
        newcancelled_ets2 = 0 if newcancelled_ets2 is None else int(newcancelled_ets2)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp <= {endtime}")
        totcancelled_ats = cur.fetchone()[0]
        totcancelled_ats = 0 if totcancelled_ats is None else int(totcancelled_ats)
        cur.execute(f"SELECT {item[key]} FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
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
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 1 AND timestamp <= {endtime}")
    toteuroprofit = cur.fetchone()[0]
    toteuroprofit = 0 if toteuroprofit is None else int(toteuroprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    neweuroprofit = cur.fetchone()[0]
    neweuroprofit = 0 if neweuroprofit is None else int(neweuroprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 2 AND timestamp <= {endtime}")
    totdollarprofit = cur.fetchone()[0]
    totdollarprofit = 0 if totdollarprofit is None else int(totdollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    newdollarprofit = cur.fetchone()[0]
    newdollarprofit = 0 if newdollarprofit is None else int(newdollarprofit)
    allprofit = {"tot": {"euro": str(toteuroprofit), "dollar": str(totdollarprofit)}, \
        "new": {"euro": str(neweuroprofit), "dollar": str(newdollarprofit)}}

    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp <= {endtime}")
    totdelivered_europrofit = cur.fetchone()[0]
    totdelivered_europrofit = 0 if totdelivered_europrofit is None else int(totdelivered_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    newdelivered_europrofit = cur.fetchone()[0]
    newdelivered_europrofit = 0 if newdelivered_europrofit is None else int(newdelivered_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp <= {endtime}")
    totdelivered_dollarprofit = cur.fetchone()[0]
    totdelivered_dollarprofit = 0 if totdelivered_dollarprofit is None else int(totdelivered_dollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 1 AND unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    newdelivered_dollarprofit = cur.fetchone()[0]
    newdelivered_dollarprofit = 0 if newdelivered_dollarprofit is None else int(newdelivered_dollarprofit)
    deliveredprofit = {"tot": {"euro": str(totdelivered_europrofit), "dollar": str(totdelivered_dollarprofit)}, \
        "new": {"euro": str(newdelivered_europrofit), "dollar": str(newdelivered_dollarprofit)}}
    
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp <= {endtime}")
    totcancelled_europrofit = cur.fetchone()[0]
    totcancelled_europrofit = 0 if totcancelled_europrofit is None else int(totcancelled_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 1 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    newcancelled_europrofit = cur.fetchone()[0]
    newcancelled_europrofit = 0 if newcancelled_europrofit is None else int(newcancelled_europrofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp <= {endtime}")
    totcancelled_dollarprofit = cur.fetchone()[0]
    totcancelled_dollarprofit = 0 if totcancelled_dollarprofit is None else int(totcancelled_dollarprofit)
    cur.execute(f"SELECT SUM(profit) FROM dlog WHERE {quser} isdelivered = 0 AND unit = 2 AND timestamp >= {starttime} AND timestamp <= {endtime}")
    newcancelled_dollarprofit = cur.fetchone()[0]
    newcancelled_dollarprofit = 0 if newcancelled_dollarprofit is None else int(newcancelled_dollarprofit)
    cancelledprofit = {"tot": {"euro": str(totcancelled_europrofit), "dollar": str(totcancelled_dollarprofit)}, \
        "new": {"euro": str(newcancelled_europrofit), "dollar": str(newcancelled_dollarprofit)}}
    
    ret["profit"] = {"all": allprofit, "delivered": deliveredprofit, "cancelled": cancelledprofit}

    return {"error": False, "response": ret}

@app.get(f"/{config.vtc_abbr}/dlog/chart")
async def getDlogChart(request: Request, response: Response,
    scale: Optional[int] = 2, sumup: Optional[bool] = False, quserid: Optional[int] = -1,
    authorization: Optional[str] = Header(None)):
    rl = ratelimit(request.client.host, 'GET /dlog/chart', 180, 60)
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
    if sumup:
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
        profit = {"euro": str(euro), "dollar": str(dollar)}
        ret.append({"starttime": str(starttime), "endtime": str(endtime), "distance": str(distance), "fuel": str(fuel), "profit": profit})
    
        if sumup:
            basedistance = distance
            basefuel = fuel
            baseeuro = euro
            basedollar = dollar

    return {"error": False, "response": ret}

@app.get(f"/{config.vtc_abbr}/dlog/leaderboard")
async def getDlogLeaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, starttime: Optional[int] = -1, endtime: Optional[int] = -1, \
        speedlimit: Optional[int] = 0, game: Optional[int] = 0, \
        limittype: Optional[str] = "distance", \
        limituser: Optional[str] = "", pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /dlog/leaderboard', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    
    debug_start = time.time()

    conn = newconn()
    cur = conn.cursor()

    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371
    
    # validate parameter
    page = max(page, 1)
    pagelimit = max(min(pagelimit, 250), 1)
    (starttime, endtime) = (0, int(time.time())) if starttime == -1 or endtime == -1 else (min(starttime, endtime), max(starttime, endtime))

    # set limits
    limituser = limituser.split(",")
    while "" in limituser:
        limituser.remove("")
    if len(limituser) > 10:
        limituser = limituser[:10]
    limit = ""
    if speedlimit != 0:
        limit = f" AND topspeed <= {int(speedlimit)}"
    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND unit = {game}"

    ##### WITH LIMIT (Parameter)
    # calculate distance
    userdistance = {}
    cur.execute(f"SELECT userid, SUM(distance) FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} {limit} {gamelimit} GROUP BY userid")
    t = cur.fetchall()
    for tt in t:
        if not tt[0] in userdistance.keys():
            userdistance[tt[0]] = tt[1]
        else:
            userdistance[tt[0]] += tt[1]
        userdistance[tt[0]] = int(userdistance[tt[0]])

    # calculate event
    userevent = {}
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
    
    # calculate division
    cur.execute(f"SELECT logid FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} ORDER BY logid ASC")
    t = cur.fetchall()
    firstlogid = 0
    if len(t) > 0:
        firstlogid = t[0][0]

    cur.execute(f"SELECT logid FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} ORDER BY logid DESC")
    t = cur.fetchall()
    lastlogid = 100000000
    if len(t) > 0:
        lastlogid = t[0][0]
    
    userdivision = {}
    cur.execute(f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 AND logid >= {firstlogid} AND logid <= {lastlogid} GROUP BY divisionid, userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in DIVISIONPNT.keys():
            userdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
    
    # calculate myth
    usermyth = {}
    cur.execute(f"SELECT userid, SUM(point) FROM mythpoint WHERE timestamp >= {starttime} AND timestamp <= {endtime} GROUP BY userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in usermyth.keys():
            usermyth[oo[0]] = 0
        usermyth[oo[0]] += oo[1]

    # calculate total point
    limittype = limittype.split(",")
    usertot = {}
    for k in userdistance.keys():
        if "distance" in limittype:
            usertot[k] = round(userdistance[k] * ratio)
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

    ##### WITHOUT LIMIT
    # calculate distance
    nluserdistance = {}
    cur.execute(f"SELECT userid, SUM(distance) FROM dlog GROUP BY userid")
    t = cur.fetchall()
    for tt in t:
        if not tt[0] in nluserdistance.keys():
            nluserdistance[tt[0]] = tt[1]
        else:
            nluserdistance[tt[0]] += tt[1]
        nluserdistance[tt[0]] = int(nluserdistance[tt[0]])

    # calculate event
    nluserevent = {}
    cur.execute(f"SELECT attendee, eventpnt FROM event")
    t = cur.fetchall()
    for tt in t:
        attendees = tt[0].split(",")
        while "" in attendees:
            attendees.remove("")
        for ttt in attendees:
            attendee = int(ttt)
            if not attendee in nluserevent.keys():
                nluserevent[attendee] = tt[1]
            else:
                nluserevent[attendee] += tt[1]
    
    # calculate division    
    nluserdivision = {}
    cur.execute(f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 GROUP BY divisionid, userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in nluserdivision.keys():
            nluserdivision[oo[0]] = 0
        if oo[1] in DIVISIONPNT.keys():
            nluserdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
    
    # calculate myth
    nlusermyth = {}
    cur.execute(f"SELECT userid, SUM(point) FROM mythpoint GROUP BY userid")
    o = cur.fetchall()
    for oo in o:
        if not oo[0] in nlusermyth.keys():
            nlusermyth[oo[0]] = 0
        nlusermyth[oo[0]] += oo[1]

    # calculate total point
    nlusertot = {}
    for k in nluserdistance.keys():
        nlusertot[k] = round(nluserdistance[k] * ratio)
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

    usertot = dict(sorted(usertot.items(),key=lambda x:x[1]))
    usertot_id = list(usertot.keys())[::-1]
    nlusertot = dict(sorted(nlusertot.items(),key=lambda x:x[1]))
    nlusertot_id = list(nlusertot.keys())[::-1]

    # calculate rank
    userrank = {}
    rank = 1
    lastpnt = 0
    for userid in usertot_id:
        userrank[userid] = rank
        if lastpnt != usertot[userid]:
            rank += 1
    nluserrank = {}
    nlrank = 1
    lastpnt = 0
    for userid in nlusertot_id:
        nluserrank[userid] = nlrank
        if lastpnt != nlusertot[userid]:
            nlrank += 1

    ret = []
    withpoint = []
    # drivers with points (WITH LIMIT)
    for userid in usertot_id:
        cur.execute(f"SELECT name, discordid, avatar, roles FROM user WHERE userid = {userid} AND userid >= 0")
        p = cur.fetchall()
        if len(p) == 0:
            continue

        # check if have driver role
        roles = p[0][3].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for i in roles:
            if int(i) in config.perms.driver:
                ok = True
        if not ok:
            continue

        withpoint.append(userid)

        distance = 0
        eventpnt = 0
        divisionpnt = 0
        mythpnt = 0
        if userid in userdistance.keys():
            distance = userdistance[userid]
        if userid in userevent.keys():
            eventpnt = userevent[userid]
        if userid in userdivision.keys():
            divisionpnt = userdivision[userid]
        if userid in usermyth.keys():
            mythpnt = usermyth[userid]

        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"userid": str(userid), "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], \
                "distance": str(distance), "event": str(eventpnt), "division": str(divisionpnt), \
                    "myth": str(mythpnt), "total": str(usertot[userid]), "rank": str(userrank[userid]), \
                        "total_no_limit": str(nlusertot[userid]), "rank_no_limit": str(nluserrank[userid])})

    # drivers with points (WITHOUT LIMIT)
    for userid in nlusertot_id:
        if userid in withpoint:
            continue

        cur.execute(f"SELECT name, discordid, avatar, roles FROM user WHERE userid = {userid} AND userid >= 0")
        p = cur.fetchall()
        if len(p) == 0:
            continue

        # check if have driver role
        roles = p[0][3].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for i in roles:
            if int(i) in config.perms.driver:
                ok = True
        if not ok:
            continue

        withpoint.append(userid)

        distance = 0
        eventpnt = 0
        divisionpnt = 0
        mythpnt = 0

        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"userid": str(userid), "name": p[0][0], "discordid": str(p[0][1]), "avatar": p[0][2], \
                "distance": "0", "event": "0", "division": "0", "myth": "0", "total": "0", "rank": str(rank), \
                        "total_no_limit": str(nlusertot[userid]), "rank_no_limit": str(nluserrank[userid])})

    # drivers without ponts (EVEN WITHOUT LIMIT)
    cur.execute(f"SELECT userid, name, discordid, avatar, roles FROM user WHERE userid >= 0")
    p = cur.fetchall()
    for pp in p:
        if pp[0] in withpoint:
            continue

        # check if have driver role
        roles = pp[4].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for i in roles:
            if int(i) in config.perms.driver:
                ok = True
        if not ok:
            continue
        
        userid = pp[0]
        name = pp[1]
        discordid = pp[2]
        avatar = pp[3]
        if str(userid) in limituser or len(limituser) == 0:
            ret.append({"userid": str(userid), "rank": str(rank), "name": name, "discordid": str(discordid), "avatar": avatar, \
                "distance": "0", "event": "0", "division": "0", "myth": "0", "total": "0", "rank": str(rank), "total_no_limit": "0", "rank_no_limit": str(nlrank)})

    debug_end = time.time()
    print(f"Leaderboard load took {int((debug_end - debug_start)*1000)}ms")

    if (page - 1) * pagelimit >= len(ret):
        return {"error": False, "response": {"list": [], "page": str(page), "tot": str(len(ret))}}

    return {"error": False, "response": {"list": ret[(page - 1) * pagelimit : page * pagelimit], "page": str(page), "tot": str(len(ret))}}

@app.get(f"/{config.vtc_abbr}/dlogs")
async def getDlogs(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, order: Optional[str] = "desc", speedlimit: Optional[int] = 0, quserid: Optional[int] = -1, \
        starttime: Optional[int] = -1, endtime: Optional[int] = -1, game: Optional[int] = 0, pagelimit: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /dlogs', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = "guest"
    if authorization != None:
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
    
    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 250:
        pagelimit = 250

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

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

    cur.execute(f"SELECT userid, data, timestamp, logid, profit, unit, distance FROM dlog WHERE logid >= 0 {limit} {timelimit} {speedlimit} {gamelimit} ORDER BY logid {order} LIMIT {(page - 1) * pagelimit}, {pagelimit}")
    
    t = cur.fetchall()
    ret = []
    for tt in t:
        data = json.loads(decompress(tt[1]))
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
        
        tuserid = str(tt[0])
        if userid == -1 and config.privacy:
            name = "Anonymous"
            tuserid = "-1"

        isdivision = False
        cur.execute(f"SELECT * FROM division WHERE logid = {tt[3]} AND status = 1 AND logid >= 0")
        p = cur.fetchall()
        if len(p) > 0:
            isdivision = True
        ret.append({"logid": str(tt[3]), "userid": tuserid, "name": name, "distance": str(distance), \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": str(cargo_mass), \
                        "profit": str(profit), "unit": str(unit), "isdivision": str(isdivision), "timestamp": str(tt[2])})

    cur.execute(f"SELECT COUNT(*) FROM dlog WHERE logid >= 0 {limit} {timelimit} {speedlimit} {gamelimit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot)}}

@app.get(f"/{config.vtc_abbr}/dlog")
async def getDlogInfo(logid: int, request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /dlog', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = "guest"
    if authorization != None:
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

    cur.execute(f"SELECT userid, data, timestamp, distance FROM dlog WHERE logid >= 0 AND logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "response": ml.tr(request, "delivery_log_not_found")}
    data = json.loads(decompress(t[0][1]))
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

    tuserid = str(t[0][0])
    if userid == -1 and config.privacy:
        name = "Anonymous"
        tuserid = "-1"

    return {"error": False, "response": {"logid": str(logid), "userid": tuserid, "name": name, \
        "loggeddistance": str(distance), "detail": data, "timestamp": str(t[0][2]), "telemetry": telemetry}}

@app.get(f"/{config.vtc_abbr}/dlog/export")
async def getDlogExport(request: Request, response: Response, authorization: str = Header(None), \
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
    cur.execute(f"SELECT logid, userid, topspeed, unit, profit, unit, fuel, distance, data, isdelivered, timestamp FROM dlog WHERE timestamp >= {starttime} AND timestamp <= {endtime} AND logid >= 0")
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

        data = json.loads(decompress(dd[8]))
        
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