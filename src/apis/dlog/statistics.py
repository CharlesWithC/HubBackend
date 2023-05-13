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

    rl = await ratelimit(request, 'GET /dlog/statistics/summary', 60, 30)
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
        quser = f"userid = {userid} AND "

    # cache
    for ll in list(app.state.cache_statistics.keys()):
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
            if tt[0] not in totdid:
                totdid.append(tt[0])
                totdrivers += 1
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE {quser} userid >= 0 AND join_timestamp >= {after} AND join_timestamp <= {before} AND roles LIKE '%,{rid},%'")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if tt[0] not in newdid:
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
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN 1 END), 0) AS ets2_job_1_0, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END), 0) AS ets2_job_1_1, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN 1 END), 0) AS ets2_job_0_0, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END), 0) AS ets2_job_0_1, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN 1 END), 0) AS ats_job_1_0, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END), 0) AS ats_job_1_1, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN 1 END), 0) AS ats_job_0_0, \
        IFNULL(COUNT(CASE WHEN logid >= 0 AND unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN 1 END), 0) AS ats_job_0_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN distance END), 0) AS ets2_distance_1_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN distance END), 0) AS ets2_distance_1_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN distance END), 0) AS ets2_distance_0_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN distance END), 0) AS ets2_distance_0_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN distance END), 0) AS ats_distance_1_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN distance END), 0) AS ats_distance_1_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN distance END), 0) AS ats_distance_0_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN distance END), 0) AS ats_distance_0_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN fuel END), 0) AS ets2_fuel_1_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END), 0) AS ets2_fuel_1_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN fuel END), 0) AS ets2_fuel_0_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END), 0) AS ets2_fuel_0_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN fuel END), 0) AS ats_fuel_1_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END), 0) AS ats_fuel_1_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN fuel END), 0) AS ats_fuel_0_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN fuel END), 0) AS ats_fuel_0_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp <= {before} THEN profit END), 0) AS ets2_profit_1_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN profit END), 0) AS ets2_profit_1_1, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp <= {before} THEN profit END), 0) AS ets2_profit_0_0, \
        IFNULL(SUM(CASE WHEN unit = 1 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN profit END), 0) AS ets2_profit_0_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp <= {before} THEN profit END), 0) AS ats_profit_1_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 1 AND timestamp >= {after} AND timestamp <= {before} THEN profit END), 0) AS ats_profit_1_1, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp <= {before} THEN profit END), 0) AS ats_profit_0_0, \
        IFNULL(SUM(CASE WHEN unit = 2 AND isdelivered = 0 AND timestamp >= {after} AND timestamp <= {before} THEN profit END), 0) AS ats_profit_0_1 \
        FROM dlog WHERE {quser} logid >= -1) AS stats")
    t = list(await app.db.fetchone(dhrid))
    t = [nint(x) for x in t]
    keys = [desc[0] for desc in app.db.conns[dhrid][1].description]
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
    if ts not in app.state.cache_statistics.keys():
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

    rl = await ratelimit(request, 'GET /dlog/statistics/chart', 60, 30)
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
    if sum_up:
        timerange = [(0, timerange[0][0])] + timerange

    limit = ""
    if quserid is not None:
        limit = f"userid = {quserid} AND"

    basedriver = 0
    if sum_up:
        await app.db.execute(dhrid, f"SELECT userid, join_timestamp, roles FROM user WHERE userid >= 0 AND join_timestamp < {timerange[1][0]}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if not checkPerm(app, str2list(tt[2]), "driver"):
                continue
            basedriver += 1

    # NOTE int(sum_up) will be 1 if sum_up is True, hence it will start from timerange[1] as timerange[0] is for base counting
    # driver_changes cannot act like timerange to add a "base" for idx=0 due to later data calculation
    driver_changes = [0] * len(timerange[int(sum_up):]) # init to be 0
    await app.db.execute(dhrid, f"SELECT userid, join_timestamp, roles FROM user WHERE userid >= 0 AND join_timestamp >= {timerange[sum_up][0]} AND join_timestamp < {before}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        if not checkPerm(app, str2list(tt[2]), "driver"):
            continue
        for i in range(int(sum_up), len(timerange)):
            if tt[1] >= timerange[i][0] and tt[1] < timerange[i][1]:
                driver_changes[i-int(sum_up)] += 1
    driver_history = [basedriver] + [0] * len(driver_changes)
    for i in range(1, len(driver_changes) + 1):
        if sum_up:
            driver_history[i] = driver_history[i-1] + driver_changes[i-1]
        else:
            driver_history[i] = driver_changes[i-1]
    driver_history = driver_history[1:]

    queries = []
    for (start_time, end_time) in timerange:
        queries.append(f"IFNULL(COUNT(CASE WHEN timestamp >= {start_time} AND timestamp < {end_time} THEN 1 END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN timestamp >= {start_time} AND timestamp < {end_time} THEN distance END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN timestamp >= {start_time} AND timestamp < {end_time} THEN fuel END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 1 AND timestamp >= {start_time} AND timestamp < {end_time} THEN profit END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 2 AND timestamp >= {start_time} AND timestamp < {end_time} THEN profit END), 0)")
    querystr = "SELECT " + ",".join(queries) + f" FROM dlog WHERE {limit} logid >= 0"
    await app.db.execute(dhrid, querystr)
    t = list(await app.db.fetchone(dhrid))
    t = [nint(x) for x in t]
    (basejob, basedistance, basefuel, baseeuro, basedollar) = [0] * 5
    if sum_up:
        (basejob, basedistance, basefuel, baseeuro, basedollar) = t[0:5]
        t = t[5:]
        timerange = timerange[1:]
    for i in range(0, len(t), 5):
        job = basejob + t[i]
        distance = basedistance + t[i+1]
        fuel = basefuel + t[i+2]
        euro = baseeuro + t[i+3]
        dollar = basedollar + t[i+4]
        (start_time, end_time) = timerange[int(i/5)]
        ret.append({"start_time": start_time, "end_time": end_time, "driver": driver_history[int(i/5)], "job": job, "distance": distance, "fuel": fuel, "profit": {"euro": euro, "dollar": dollar}})

        if sum_up:
            (basejob, basedistance, basefuel, baseeuro, basedollar) = \
                (job, distance, fuel, euro, dollar)

    return ret
