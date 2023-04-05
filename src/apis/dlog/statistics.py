# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from typing import Optional

from fastapi import Header, Request, Response

from functions import *

# app.state.cache_statistics = {}

async def get_summary(request: Request, response: Response, authorization: str = Header(None), \
        after: Optional[int] = None, before: Optional[int] = None, userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'GET /dlog/statistics/summary', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if after is None:
        after = 0
    if before is None:
        before = max(int(time.time()), 32503651200)

    quser = ""
    if userid is not None:
        if app.config.privacy:
            au = await auth(authorization, request, allow_application_token = True)
            if au["error"]:
                response.status_code = au["code"]
                del au["code"]
                return au
        quser = f"userid = {userid} AND"

    # cache
    l = list(app.state.cache_statistics.keys())
    for ll in l:
        if ll < int(time.time()) - 120:
            del app.state.cache_statistics[ll]
        else:
            tt = app.state.cache_statistics[ll]
            for t in tt:
                if abs(t["start_time"] - after) <= 120 and abs(t["end_time"] - before) <= 120 and t["userid"] == userid:
                    ret = t["result"]
                    ret["cache"] = ll
                    return ret

    ret = {}
    # driver
    totdid = []
    newdid = []
    totdrivers = 0
    newdrivers = 0
    for rid in app.config.perms.driver:
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE {quser} userid >= 0 AND join_timestamp <= {before} AND roles LIKE '%,{rid},%'")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if not tt[0] in totdid:
                totdid.append(tt[0])
                totdrivers += 1
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE {quser} userid >= 0 AND join_timestamp >= {after} AND join_timestamp <= {before} AND roles LIKE '%,{rid},%'")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if not tt[0] in newdid:
                newdid.append(tt[0])
                newdrivers += 1

    ret["driver"] = {"tot": totdrivers, "new": newdrivers}
    
    # job / delivered / cancelled
    item = {"job": "COUNT(*)", "distance": "SUM(distance)", "fuel": "SUM(fuel)"}
    for key in item.keys():
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND timestamp <= {before}")
        tot = await app.db.fetchone(dhrid)
        tot = nint(tot[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND timestamp >= {after} AND timestamp <= {before}")
        new = await app.db.fetchone(dhrid)
        new = nint(new[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND unit = 1 AND timestamp <= {before}")
        totets2 = await app.db.fetchone(dhrid)
        totets2 = nint(totets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
        newets2 = await app.db.fetchone(dhrid)
        newets2 = nint(newets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND unit = 2 AND timestamp <= {before}")
        totats = await app.db.fetchone(dhrid)
        totats = nint(totats[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
        newats = await app.db.fetchone(dhrid)
        newats = nint(newats[0])

        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND timestamp <= {before}")
        totdelivered = await app.db.fetchone(dhrid)
        totdelivered = nint(totdelivered[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before}")
        newdelivered = await app.db.fetchone(dhrid)
        newdelivered = nint(newdelivered[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 1 AND timestamp <= {before}")
        totdelivered_ets2 = await app.db.fetchone(dhrid)
        totdelivered_ets2 = nint(totdelivered_ets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
        newdelivered_ets2 = await app.db.fetchone(dhrid)
        newdelivered_ets2 = nint(newdelivered_ets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 2 AND timestamp <= {before}")
        totdelivered_ats = await app.db.fetchone(dhrid)
        totdelivered_ats = nint(totdelivered_ats[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
        newdelivered_ats = await app.db.fetchone(dhrid)
        newdelivered_ats = nint(newdelivered_ats[0])

        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND timestamp <= {before}")
        totcancelled = await app.db.fetchone(dhrid)
        totcancelled = nint(totcancelled[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before}")
        newcancelled = await app.db.fetchone(dhrid)
        newcancelled = nint(newcancelled[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 1 AND timestamp <= {before}")
        totcancelled_ets2 = await app.db.fetchone(dhrid)
        totcancelled_ets2 = nint(totcancelled_ets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
        newcancelled_ets2 = await app.db.fetchone(dhrid)
        newcancelled_ets2 = nint(newcancelled_ets2[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 2 AND timestamp <= {before}")
        totcancelled_ats = await app.db.fetchone(dhrid)
        totcancelled_ats = nint(totcancelled_ats[0])
        await app.db.execute(dhrid, f"SELECT {item[key]} FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
        newcancelled_ats = await app.db.fetchone(dhrid)
        newcancelled_ats = nint(newcancelled_ats[0])

        ret[key] = {"all": {"sum": {"tot": tot, "new": new}, \
            "ets2": {"tot": totets2, "new": newets2}, \
            "ats": {"tot": totats, "new": newats}}, \
            "delivered": {"sum": {"tot": totdelivered, "new": newdelivered}, \
                    "ets2": {"tot": totdelivered_ets2, "new": newdelivered_ets2}, \
                    "ats": {"tot": totdelivered_ats, "new": newdelivered_ats}}, \
                "cancelled": {"sum": {"tot": totcancelled, "new": newcancelled}, \
                    "ets2": {"tot": totcancelled_ets2, "new": newcancelled_ets2}, \
                    "ats": {"tot": totcancelled_ats, "new": newcancelled_ats}}}

    # profit
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND unit = 1 AND timestamp <= {before}")
    toteuroprofit = await app.db.fetchone(dhrid)
    toteuroprofit = nint(toteuroprofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
    neweuroprofit = await app.db.fetchone(dhrid)
    neweuroprofit = nint(neweuroprofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND unit = 2 AND timestamp <= {before}")
    totdollarprofit = await app.db.fetchone(dhrid)
    totdollarprofit = nint(totdollarprofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
    newdollarprofit = await app.db.fetchone(dhrid)
    newdollarprofit = nint(newdollarprofit[0])
    allprofit = {"tot": {"euro": toteuroprofit, "dollar": totdollarprofit}, \
        "new": {"euro": neweuroprofit, "dollar": newdollarprofit}}

    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 1 AND timestamp <= {before}")
    totdelivered_europrofit = await app.db.fetchone(dhrid)
    totdelivered_europrofit = nint(totdelivered_europrofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
    newdelivered_europrofit = await app.db.fetchone(dhrid)
    newdelivered_europrofit = nint(newdelivered_europrofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 2 AND timestamp <= {before}")
    totdelivered_dollarprofit = await app.db.fetchone(dhrid)
    totdelivered_dollarprofit = nint(totdelivered_dollarprofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 1 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
    newdelivered_dollarprofit = await app.db.fetchone(dhrid)
    newdelivered_dollarprofit = nint(newdelivered_dollarprofit[0])
    deliveredprofit = {"tot": {"euro": totdelivered_europrofit, "dollar": totdelivered_dollarprofit}, \
        "new": {"euro": newdelivered_europrofit, "dollar": newdelivered_dollarprofit}}
    
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 1 AND timestamp <= {before}")
    totcancelled_europrofit = await app.db.fetchone(dhrid)
    totcancelled_europrofit = nint(totcancelled_europrofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 1 AND timestamp >= {after} AND timestamp <= {before}")
    newcancelled_europrofit = await app.db.fetchone(dhrid)
    newcancelled_europrofit = nint(newcancelled_europrofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 2 AND timestamp <= {before}")
    totcancelled_dollarprofit = await app.db.fetchone(dhrid)
    totcancelled_dollarprofit = nint(totcancelled_dollarprofit[0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {quser} logid >= 0 AND isdelivered = 0 AND unit = 2 AND timestamp >= {after} AND timestamp <= {before}")
    newcancelled_dollarprofit = await app.db.fetchone(dhrid)
    newcancelled_dollarprofit = nint(newcancelled_dollarprofit[0])
    cancelledprofit = {"tot": {"euro": totcancelled_europrofit, "dollar": totcancelled_dollarprofit}, \
        "new": {"euro": newcancelled_europrofit, "dollar": newcancelled_dollarprofit}}
    
    ret["profit"] = {"all": allprofit, "delivered": deliveredprofit, "cancelled": cancelledprofit}

    ts = int(time.time())
    if not ts in app.state.cache_statistics.keys():
        app.state.cache_statistics[ts] = []
    app.state.cache_statistics[ts].append({"start_time": after, "end_time": before, "userid": userid, "result": ret})

    ret["cache"] = None

    return ret

async def get_chart(request: Request, response: Response, authorization: Optional[str] = Header(None), \
        ranges: Optional[int] = 30, interval: Optional[int] = 86400, before: Optional[int] = None, \
        sum_up: Optional[bool] = False, userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'GET /dlog/statistics/chart', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    quserid = userid
    if quserid is not None:
        au = await auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au

    if ranges > 100:
        ranges = 100
    elif ranges <= 0:
        ranges = 30
    
    if interval > 31536000: # a year
        interval = 31536000
    elif interval < 60:
        interval = 60
    
    if before is None:
        before = int(time.time())

    ret = []
    timerange = []
    for i in range(ranges):
        r_start_time = before - ((i+1)*interval)
        if r_start_time <= 0:
            break
        r_end_time = r_start_time + interval
        timerange.append((r_start_time, r_end_time))
    timerange = timerange[::-1]

    limit = ""
    if quserid is not None:
        limit = f"userid = {quserid} AND"

    alldriverid = []
    basedriver = 0
    basejob = 0
    basedistance = 0
    basefuel = 0
    baseeuro = 0
    basedollar = 0
    if sum_up:
        before = timerange[0][0]

        for rid in app.config.perms.driver:
            await app.db.execute(dhrid, f"SELECT userid FROM user WHERE {limit} userid >= 0 AND join_timestamp >= 0 AND join_timestamp < {before} AND roles LIKE '%,{rid},%'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                if not tt[0] in alldriverid:
                    alldriverid.append(tt[0])
                    basedriver += 1

        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= 0 AND timestamp < {before}")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0 and t[0][0] is not None:
            basejob = nint(t[0][0])

        await app.db.execute(dhrid, f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= 0 AND timestamp < {before}")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0 and t[0][0] is not None:
            basedistance = nint(t[0][0])
            basefuel = nint(t[0][1])
        await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= 0 AND timestamp < {before} AND unit = 1")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0 and t[0][0] is not None:
            baseeuro = nint(t[0][0])
        await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= 0 AND timestamp < {before} AND unit = 2")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0 and t[0][0] is not None:
            basedollar = nint(t[0][0])

    for (start_time, before) in timerange:
        driver = basedriver
        for rid in app.config.perms.driver:
            await app.db.execute(dhrid, f"SELECT userid FROM user WHERE {limit} userid >= 0 AND join_timestamp >= {start_time} AND join_timestamp < {before} AND roles LIKE '%,{rid},%'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                if not tt[0] in alldriverid:
                    alldriverid.append(tt[0])
                    driver += 1

        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= {start_time} AND timestamp < {before}")
        t = await app.db.fetchall(dhrid)
        job = basejob
        if len(t) > 0 and t[0][0] is not None:
            job += nint(t[0][0])
                    
        await app.db.execute(dhrid, f"SELECT SUM(distance), SUM(fuel) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= {start_time} AND timestamp < {before}")
        t = await app.db.fetchall(dhrid)
        distance = basedistance
        fuel = basefuel
        if len(t) > 0 and t[0][0] is not None and len(t[0]) > 1:
            distance += nint(t[0][0])
            fuel += nint(t[0][1])
        await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= {start_time} AND timestamp < {before} AND unit = 1")
        t = await app.db.fetchall(dhrid)
        euro = baseeuro
        if len(t) > 0 and t[0][0] is not None:
            euro += nint(t[0][0])
        await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE {limit} logid >= 0 AND timestamp >= {start_time} AND timestamp < {before} AND unit = 2")
        t = await app.db.fetchall(dhrid)
        dollar = basedollar
        if len(t) > 0 and t[0][0] is not None:
            dollar += nint(t[0][0])
        profit = {"euro": euro, "dollar": dollar}
        ret.append({"start_time": start_time, "end_time": before, "driver": driver, "job": job, "distance": distance, "fuel": fuel, "profit": profit})
    
        if sum_up:
            basedriver = driver
            basejob = job
            basedistance = distance
            basefuel = fuel
            baseeuro = euro
            basedollar = dollar

    return ret