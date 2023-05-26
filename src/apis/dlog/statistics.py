# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from typing import Optional

from fastapi import Header, Request, Response

from db import genconn
from functions import *


def rebuild(app):
    '''Delete all dlog_stats and rebuild stats from dlog detail.

    NOTE Time consuming! Drivers Hub will not start before this is done once called.
    NOTE This can only be called from cli switch --rebuild-dlog-stats'''

    conn = genconn(app)
    cur = conn.cursor()
    cur.execute("DELETE FROM dlog_stats")
    conn.commit()
    cur.execute("SELECT logid, userid, data FROM dlog WHERE logid >= 0 AND userid >= 0")
    t = cur.fetchall()

    max_log_id = 0
    memtable = {}

    for tt in t:
        max_log_id = max(max_log_id, tt[0])
        userid = tt[1]
        try:
            d = json.loads(decompress(tt[2]))
        except:
            continue

        dlog_stats = {}

        obj = d["data"]["object"]

        dlog_stats[3] = []

        truck = obj["truck"]
        if truck is not None:
            if "unique_id" in truck.keys() and "name" in truck.keys() and \
                    truck["brand"] is not None and "name" in truck["brand"].keys():
                dlog_stats[1] = [[convertQuotation(truck["unique_id"]), convertQuotation(truck["brand"]["name"]) + " " + convertQuotation(truck["name"]), 1, 0]]
            if "license_plate_country" in truck.keys() and truck["license_plate_country"] is not None and \
                    "unique_id" in truck["license_plate_country"].keys() and "name" in truck["license_plate_country"].keys():
                dlog_stats[3] = [[convertQuotation(truck["license_plate_country"]["unique_id"]), convertQuotation(truck["license_plate_country"]["name"]), 1, 0]]

        for trailer in obj["trailers"]:
            if "body_type" in trailer.keys():
                body_type = trailer["body_type"]
                dlog_stats[2]  = [[convertQuotation(body_type), convertQuotation(body_type), 1, 0]]
            if "license_plate_country" in trailer.keys() and trailer["license_plate_country"] is not None and \
                    "unique_id" in trailer["license_plate_country"].keys() and "name" in trailer["license_plate_country"].keys():
                item = [convertQuotation(trailer["license_plate_country"]["unique_id"]), convertQuotation(trailer["license_plate_country"]["name"]), 1, 0]
                duplicate = False
                for i in range(len(dlog_stats[3])):
                    if dlog_stats[3][i][0] == item[0] and dlog_stats[3][i][1] == item[1]:
                        dlog_stats[3][i][2] += 1
                        duplicate = True
                        break
                if not duplicate:
                    dlog_stats[3].append(item)

        cargo = obj["cargo"]
        if cargo is not None and "unique_id" in cargo.keys() and "name" in cargo.keys():
            dlog_stats[4] = [[convertQuotation(cargo["unique_id"]), convertQuotation(cargo["name"]), 1, 0]]

        if "market" in obj.keys():
            dlog_stats[5] = [[convertQuotation(obj["market"]), convertQuotation(obj["market"]), 1, 0]]

        source_city = obj["source_city"]
        if source_city is not None and "unique_id" in source_city.keys() and "name" in source_city.keys():
            dlog_stats[6] = [[convertQuotation(source_city["unique_id"]), convertQuotation(source_city["name"]), 1, 0]]
        source_company = obj["source_company"]
        if source_company is not None and "unique_id" in source_company.keys() and "name" in source_company.keys():
            dlog_stats[7] = [[convertQuotation(source_company["unique_id"]), convertQuotation(source_company["name"]), 1, 0]]
        destination_city = obj["destination_city"]
        if destination_city is not None and "unique_id" in destination_city.keys() and "name" in destination_city.keys():
            dlog_stats[8] = [[convertQuotation(destination_city["unique_id"]), convertQuotation(destination_city["name"]), 1, 0]]
        destination_company = obj["destination_company"]
        if destination_company is not None and "unique_id" in destination_company.keys() and "name" in destination_company.keys():
            dlog_stats[9] = [[convertQuotation(destination_company["unique_id"]), convertQuotation(destination_company["name"]), 1, 0]]

        for i in range(10, 17):
            dlog_stats[i] = []

        for event in d["data"]["object"]["events"]:
            etype = event["type"]
            if etype == "fine":
                item = [event["meta"]["offence"], event["meta"]["offence"], 1, int(event["meta"]["amount"])]
                item[3] = item[3] if item[3] <= 51200 else 0
                duplicate = False
                for i in range(len(dlog_stats[10])):
                    if dlog_stats[10][i][0] == item[0] and dlog_stats[10][i][1] == item[1]:
                        dlog_stats[10][i][2] += 1
                        dlog_stats[10][i][3] += item[3]
                        duplicate = True
                        break
                if not duplicate:
                    dlog_stats[10].append(item)

            elif etype in ["collision", "speeding", "teleport"]:
                K = {"collision": 15, "speeding": 11, "teleport": 16}
                item = [etype, etype, 1, 0]
                duplicate = False
                for i in range(len(dlog_stats[K[etype]])):
                    if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                        dlog_stats[K[etype]][i][2] += 1
                        duplicate = True
                        break
                if not duplicate:
                    dlog_stats[K[etype]].append(item)

            elif etype in ["tollgate"]:
                K = {"tollgate": 12}
                item = [etype, etype, 1, int(event["meta"]["cost"])]
                item[3] = item[3] if item[3] <= 51200 else 0
                duplicate = False
                for i in range(len(dlog_stats[K[etype]])):
                    if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                        dlog_stats[K[etype]][i][2] += 1
                        dlog_stats[K[etype]][i][3] += item[3]
                        duplicate = True
                        break
                if not duplicate:
                    dlog_stats[K[etype]].append(item)

            elif etype in ["ferry", "train"]:
                K = {"ferry": 13, "train": 14}
                item = [f'{convertQuotation(event["meta"]["source_id"])}/{convertQuotation(event["meta"]["target_id"])}', f'{convertQuotation(event["meta"]["source_name"])}/{convertQuotation(event["meta"]["target_name"])}', 1, int(event["meta"]["cost"])]
                item[3] = item[3] if item[3] <= 51200 else 0
                duplicate = False
                for i in range(len(dlog_stats[K[etype]])):
                    if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                        dlog_stats[K[etype]][i][2] += 1
                        dlog_stats[K[etype]][i][3] += item[3]
                        duplicate = True
                        break
                if not duplicate:
                    dlog_stats[K[etype]].append(item)

        for stat_userid in [userid, -1]:
            for itype in dlog_stats.keys():
                for dd in dlog_stats[itype]:
                    if (itype, stat_userid, dd[0]) not in memtable.keys():
                        memtable[(itype, stat_userid, dd[0])] = [dd[1], dd[2], dd[3]]
                    else:
                        memtable[(itype, stat_userid, dd[0])][0] = dd[1]
                        memtable[(itype, stat_userid, dd[0])][1] += dd[2]
                        memtable[(itype, stat_userid, dd[0])][2] += dd[3]

    for (item_type, stat_userid, item_key) in memtable.keys():
        if item_key == "None":
            continue
        [item_name, count, sum] = memtable[(item_type, stat_userid, item_key)]
        cur.execute(f"INSERT INTO dlog_stats VALUES ({item_type}, {stat_userid}, '{item_key}', '{item_name}', {count}, {sum})")
    cur.execute(f"UPDATE settings SET sval = '{max_log_id}' WHERE skey = 'dlog_stats_up_to'")

    conn.commit()
    cur.close()
    conn.close()

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
    au = await auth(authorization, request, allow_application_token = True)
    if app.config.privacy and userid is not None and au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    elif userid is not None:
        quser = f"AND userid = {userid}"

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
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid >= 0 {quser} AND join_timestamp <= {before} AND roles LIKE '%,{rid},%'")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if tt[0] not in totdid:
                totdid.append(tt[0])
                totdrivers += 1
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid >= 0 {quser} AND join_timestamp >= {after} AND join_timestamp <= {before} AND roles LIKE '%,{rid},%'")
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
        FROM dlog WHERE userid >= 0 {quser}) AS stats")
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

    quser = ""
    au = await auth(authorization, request, allow_application_token = True)
    if app.config.privacy and userid is not None and au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    elif userid is not None:
        quser = f"AND userid = {userid}"

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
        queries.append(f"IFNULL(COUNT(CASE WHEN unit = 1 AND logid >= 0 AND timestamp >= {start_time} AND timestamp < {end_time} THEN 1 END), 0)")
        queries.append(f"IFNULL(COUNT(CASE WHEN unit = 2 AND logid >= 0 AND timestamp >= {start_time} AND timestamp < {end_time} THEN 1 END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 1 AND timestamp >= {start_time} AND timestamp < {end_time} THEN distance END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 2 AND timestamp >= {start_time} AND timestamp < {end_time} THEN distance END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 1 AND timestamp >= {start_time} AND timestamp < {end_time} THEN fuel END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 2 AND timestamp >= {start_time} AND timestamp < {end_time} THEN fuel END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 1 AND timestamp >= {start_time} AND timestamp < {end_time} THEN profit END), 0)")
        queries.append(f"IFNULL(SUM(CASE WHEN unit = 2 AND timestamp >= {start_time} AND timestamp < {end_time} THEN profit END), 0)")
    querystr = "SELECT " + ",".join(queries) + f" FROM dlog WHERE userid >= 0 {quser}"
    await app.db.execute(dhrid, querystr)
    t = list(await app.db.fetchone(dhrid))
    base = [0] * 8
    if sum_up:
        base = t[0:8]
        t = t[8:]
        timerange = timerange[1:]
    for i in range(0, len(t), 8):
        p = t[i:i+8]
        (start_time, end_time) = timerange[int(i/8)]
        row = {"start_time": start_time, "end_time": end_time, "driver": driver_history[int(i/8)],
                    "job": {"ets2": base[0] + p[0], "ats": base[1] + p[1], "sum": base[0] + base[1] + p[0] + p[1]},
                    "distance": {"ets2": base[2] + p[2], "ats": base[3] + p[3], "sum": base[2] + base[3] + p[2] + p[3]},
                    "fuel": {"ets2": base[4] + p[4], "ats": base[5] + p[5], "sum": base[4] + base[5] + p[4] + p[5]},
                    "profit": {"euro": base[6] + p[6], "dollar": base[7] + p[7]}}
        ret.append(dictF2I(row))

        if sum_up:
            base = [base[j] + p[j] for j in range(8)]

    return ret

async def get_details(request: Request, response: Response, authorization: Optional[str] = Header(None), userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'GET /dlog/statistics/details', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    quser = ""
    au = await auth(authorization, request, allow_application_token = True)
    if app.config.privacy and userid is not None and au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    elif userid is not None:
        quser = f"userid = {userid}"

    ret = {}
    K = {1: "truck", 2: "trailer", 3: "plate_country", 4: "cargo", 5: "cargo_market", 6: "source_city", 7: "source_company", 8: "destination_city", 9: "destination_company", 10: "fine", 11: "speeding", 12: "tollgate", 13: "ferry", 14: "train", 15: "collision", 16: "teleport"}

    await app.db.execute(dhrid, f"SELECT item_type, item_key, item_name, count, sum FROM dlog_stats WHERE {quser} ORDER BY item_type ASC, count DESC, sum DESC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        if K[tt[0]] not in ret.keys():
            ret[K[tt[0]]] = []
        if tt[0] in [1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 15, 16]:
            ret[K[tt[0]]].append({"unique_id": tt[1], "name": tt[2], "count": tt[3]})
        else:
            ret[K[tt[0]]].append({"unique_id": tt[1], "name": tt[2], "count": tt[3], "sum": tt[4]})

    return ret
