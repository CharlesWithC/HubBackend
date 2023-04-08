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
        if ll < int(time.time()) - 15:
            del app.state.cache_statistics[ll]
        else:
            tt = app.state.cache_statistics[ll]
            for t in tt:
                if abs(t["start_time"] - after) <= 15 and abs(t["end_time"] - before) <= 15 and t["userid"] == userid:
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
    # This query returns
    # ets2 tot delivered job, ets2 new delivered job, ets2 tot cancelled job, ets2 new cancelled job
    # ats tot delivered job, ats new delivered job, ats tot cancelled job, ats new cancelled job
    # and distance, fuel (same order) as well
    await app.db.execute(dhrid, f"SELECT \
        ets2_job_1_0 + ets2_job_0_0 + ats_job_1_0 + ats_job_0_0 AS job_all_sum_tot, \
        ets2_job_1_1 + ets2_job_0_1 + ats_job_1_1 + ats_job_0_1 AS job_all_sum_new, \
        ets2_job_1_0 + ets2_job_0_0 AS job_all_ets2_tot, \
        ets2_job_1_1 + ets2_job_0_1 AS job_all_ets2_new, \
        ats_job_1_0 + ats_job_0_0 AS job_all_ats_tot, \
        ats_job_1_1 + ats_job_0_1 AS job_all_ats_new, \
        ets2_job_1_0 + ats_job_1_0 AS job_delivered_sum_tot, \
        ets2_job_1_1 + ats_job_1_1 AS job_delivered_sum_new, \
        ets2_job_1_0 AS job_delivered_ets2_tot, \
        ets2_job_1_1 AS job_delivered_ets2_new, \
        ats_job_1_0 AS job_delivered_ats_tot, \
        ats_job_1_1 AS job_delivered_ats_new, \
        ets2_job_0_0 + ats_job_0_0 AS job_cancelled_sum_tot, \
        ets2_job_0_1 + ats_job_0_1 AS job_cancelled_sum_new, \
        ets2_job_0_0 AS job_cancelled_ets2_tot, \
        ets2_job_0_1 AS job_cancelled_ets2_new, \
        ats_job_0_0 AS job_cancelled_ats_tot, \
        ats_job_0_1 AS job_cancelled_ats_new, \
        ets2_distance_1_0 + ets2_distance_0_0 + ats_distance_1_0 + ats_distance_0_0 AS distance_all_sum_tot, \
        ets2_distance_1_1 + ets2_distance_0_1 + ats_distance_1_1 + ats_distance_0_1 AS distance_all_sum_new, \
        ets2_distance_1_0 + ets2_distance_0_0 AS distance_all_ets2_tot, \
        ets2_distance_1_1 + ets2_distance_0_1 AS distance_all_ets2_new, \
        ats_distance_1_0 + ats_distance_0_0 AS distance_all_ats_tot, \
        ats_distance_1_1 + ats_distance_0_1 AS distance_all_ats_new, \
        ets2_distance_1_0 + ats_distance_1_0 AS distance_delivered_sum_tot, \
        ets2_distance_1_1 + ats_distance_1_1 AS distance_delivered_sum_new, \
        ets2_distance_1_0 AS distance_delivered_ets2_tot, \
        ets2_distance_1_1 AS distance_delivered_ets2_new, \
        ats_distance_1_0 AS distance_delivered_ats_tot, \
        ats_distance_1_1 AS distance_delivered_ats_new, \
        ets2_distance_0_0 + ats_distance_0_0 AS distance_cancelled_sum_tot, \
        ets2_distance_0_1 + ats_distance_0_1 AS distance_cancelled_sum_new, \
        ets2_distance_0_0 AS distance_cancelled_ets2_tot, \
        ets2_distance_0_1 AS distance_cancelled_ets2_new, \
        ats_distance_0_0 AS distance_cancelled_ats_tot, \
        ats_distance_0_1 AS distance_cancelled_ats_new, \
        ets2_fuel_1_0 + ets2_fuel_0_0 + ats_fuel_1_0 + ats_fuel_0_0 AS fuel_all_sum_tot, \
        ets2_fuel_1_1 + ets2_fuel_0_1 + ats_fuel_1_1 + ats_fuel_0_1 AS fuel_all_sum_new, \
        ets2_fuel_1_0 + ets2_fuel_0_0 AS fuel_all_ets2_tot, \
        ets2_fuel_1_1 + ets2_fuel_0_1 AS fuel_all_ets2_new, \
        ats_fuel_1_0 + ats_fuel_0_0 AS fuel_all_ats_tot, \
        ats_fuel_1_1 + ats_fuel_0_1 AS fuel_all_ats_new, \
        ets2_fuel_1_0 + ats_fuel_1_0 AS fuel_delivered_sum_tot, \
        ets2_fuel_1_1 + ats_fuel_1_1 AS fuel_delivered_sum_new, \
        ets2_fuel_1_0 AS fuel_delivered_ets2_tot, \
        ets2_fuel_1_1 AS fuel_delivered_ets2_new, \
        ats_fuel_1_0 AS fuel_delivered_ats_tot, \
        ats_fuel_1_1 AS fuel_delivered_ats_new, \
        ets2_fuel_0_0 + ats_fuel_0_0 AS fuel_cancelled_sum_tot, \
        ets2_fuel_0_1 + ats_fuel_0_1 AS fuel_cancelled_sum_new, \
        ets2_fuel_0_0 AS fuel_cancelled_ets2_tot, \
        ets2_fuel_0_1 AS fuel_cancelled_ets2_new, \
        ats_fuel_0_0 AS fuel_cancelled_ats_tot, \
        ats_fuel_0_1 AS fuel_cancelled_ats_new, \
        ets2_profit_1_0 + ets2_profit_0_0 AS profit_all_tot_euro, \
        ets2_profit_1_1 + ets2_profit_0_1 AS profit_all_new_euro, \
        ats_profit_1_0 + ats_profit_0_0 AS profit_all_tot_dollar, \
        ats_profit_1_1 + ats_profit_0_1 AS profit_all_new_dollar, \
        ets2_profit_1_0 AS profit_delivered_tot_euro, \
        ets2_profit_1_1 AS profit_delivered_new_euro, \
        ats_profit_1_0 AS profit_delivered_tot_dollar, \
        ats_profit_1_1 AS profit_delivered_new_dollar, \
        ets2_profit_0_0 AS profit_cancelled_tot_euro, \
        ets2_profit_0_1 AS profit_cancelled_new_euro, \
        ats_profit_0_0 AS profit_cancelled_tot_dollar, \
        ats_profit_0_1 AS profit_cancelled_new_dollar \
        FROM ( SELECT \
        COUNT(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN 1 END) AS ets2_job_1_0, \
        COUNT(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END) AS ets2_job_1_1, \
        COUNT(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN 1 END) AS ets2_job_0_0, \
        COUNT(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END) AS ets2_job_0_1, \
        COUNT(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN 1 END) AS ats_job_1_0, \
        COUNT(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END) AS ats_job_1_1, \
        COUNT(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN 1 END) AS ats_job_0_0, \
        COUNT(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END) AS ats_job_0_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN distance END) AS ets2_distance_1_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN distance END) AS ets2_distance_1_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN distance END) AS ets2_distance_0_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN distance END) AS ets2_distance_0_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN distance END) AS ats_distance_1_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN distance END) AS ats_distance_1_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN distance END) AS ats_distance_0_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN distance END) AS ats_distance_0_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN fuel END) AS ets2_fuel_1_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END) AS ets2_fuel_1_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN fuel END) AS ets2_fuel_0_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END) AS ets2_fuel_0_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN fuel END) AS ats_fuel_1_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END) AS ats_fuel_1_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN fuel END) AS ats_fuel_0_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END) AS ats_fuel_0_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN profit END) AS ets2_profit_1_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN profit END) AS ets2_profit_1_1, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN profit END) AS ets2_profit_0_0, \
        SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN profit END) AS ets2_profit_0_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN profit END) AS ats_profit_1_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN profit END) AS ats_profit_1_1, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN profit END) AS ats_profit_0_0, \
        SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN profit END) AS ats_profit_0_1 \
        FROM dlog WHERE {quser} logid >= 0 ) AS stats")
    t = await app.db.fetchall(dhrid)
    keys = [desc[0] for desc in app.db.conns[dhrid][1].description]
    t = list(t[0])
    for i in range(len(t)):
        if t[i] is None:
            t[i] = 0
        else:
            t[i] = int(t[i])
    d = dict(zip(keys, t))

    for key, value in d.items():
        parts = key.split("_")
        current_dict = ret
        for part in parts[:-1]:
            current_dict = current_dict.setdefault(part, {})
        current_dict[parts[-1]] = value

    top_level_dict = {}
    for key, value in ret.items():
        parts = key.split("_")
        top_level_key = parts[0]
        if top_level_key not in top_level_dict:
            top_level_dict[top_level_key] = {}
        current_dict = top_level_dict[top_level_key]
        for part in parts[1:-1]:
            current_dict = current_dict.setdefault(part, {})
        current_dict[parts[-1]] = value

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