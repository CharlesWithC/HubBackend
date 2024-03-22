# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "logid", order: Optional[str] = "desc", \
        speed_limit: Optional[int] = None, userid: Optional[int] = None, \
        after_logid: Optional[int] = None, after: Optional[int] = None, before: Optional[int] = None, \
        game: Optional[int] = None, status: Optional[int] = None,\
        challenge: Optional[str] = "any", division: Optional[str] = "any"):
    '''`challenge` and `division` can only be include/only/none/any/{id}'''
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'GET /dlog/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, extra_time = 3)

    quserid = userid

    userid = -1
    if authorization is not None:
        au = await auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        userid = au["userid"]
        await ActivityUpdate(request, au["uid"], "dlogs")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if order_by not in ["logid", "userid", "max_speed", "profit", "fuel", "distance", "views", "timestamp"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}
    if order_by == "max_speed":
        order_by = "topspeed"
    if order_by == "views":
        order_by = "view_count"

    limit = ""
    if quserid is not None:
        limit += f"AND dlog.userid = {quserid} "
    if challenge == "include":
        limit = limit
    elif challenge == "only":
        limit += "AND dlog.logid IN (SELECT challenge_record.logid FROM challenge_record) "
    elif challenge == "none":
        limit += "AND dlog.logid NOT IN (SELECT challenge_record.logid FROM challenge_record) "
    elif challenge != "any":
        try:
            challengeid = int(challenge)
            limit += f"AND dlog.logid IN (SELECT challenge_record.logid FROM challenge_record WHERE challenge_record.challengeid = {challengeid}) "
        except:
            response.status_code = 422
            return {"error": "Unprocessable Entity"}
    if division == "include":
        limit = limit
    elif division == "only":
        limit += "AND dlog.logid IN (SELECT division.logid FROM division WHERE division.status = 1) "
    elif division == "none":
        limit += "AND dlog.logid NOT IN (SELECT division.logid FROM division WHERE division.status = 1) "
    elif division != "any":
        try:
            divisionid = int(division)
            limit += f"AND dlog.logid IN (SELECT division.logid FROM division WHERE division.status = 1 AND division.divisionid = {divisionid}) "
        except:
            response.status_code = 422
            return {"error": "Unprocessable Entity"}

    timelimit = ""
    if after is not None:
        timelimit += f"AND dlog.timestamp >= {after} "
    if before is not None:
        timelimit += f"AND dlog.timestamp <= {before} "
    if after_logid is not None:
        if order == "asc":
            timelimit += f"AND dlog.logid >= {after_logid} "
        elif order == "desc":
            timelimit += f"AND dlog.logid <= {after_logid} "

    if speed_limit is not None:
        speed_limit = f" AND dlog.topspeed <= {speed_limit}"
    else:
        speed_limit = ""

    status_limit = ""
    if status == 1:
        status_limit = " AND dlog.isdelivered = 1"
    elif status == 2:
        status_limit = " AND dlog.isdelivered = 0"

    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND dlog.unit = {game}"

    await app.db.execute(dhrid, f"SELECT dlog.userid, dlog.data, dlog.timestamp, dlog.logid, dlog.profit, dlog.unit, dlog.distance, dlog.isdelivered, division.divisionid, dlog.topspeed, dlog.fuel, dlog.view_count FROM dlog \
        LEFT JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        WHERE dlog.logid >= 0 {limit} {timelimit} {speed_limit} {gamelimit} {status_limit} ORDER BY dlog.{order_by} {order}, dlog.logid DESC LIMIT {max(page-1, 0) * page_size}, {page_size}")
    ret = []
    t = await app.db.fetchall(dhrid)
    for ti in range(len(t)):
        tt = t[ti]

        logid = tt[3]

        division_id = tt[8]
        division_name = None
        division = {}
        if division_id is not None:
            if division_id in app.division_name.keys():
                division_name = app.division_name[division_id]
            division = {"divisionid": division_id, "name": division_name}

        await app.db.execute(dhrid, f"SELECT dlog.logid, challenge_info.challengeid, challenge.title FROM dlog \
            LEFT JOIN (SELECT challengeid, logid FROM challenge_record) challenge_info ON challenge_info.logid = dlog.logid \
            LEFT JOIN challenge ON challenge.challengeid = challenge_info.challengeid \
            WHERE dlog.logid = {logid}")
        p = await app.db.fetchall(dhrid)
        challengeids = []
        challengenames = []
        for pp in p:
            if len(pp) <= 2 or pp[1] is None or pp[2] is None:
                continue
            challengeids.append(pp[1])
            challengenames.append(pp[2])

        challenge = []
        for i in range(len(challengeids)):
            challenge.append({"challengeid": challengeids[i], "name": challengenames[i]})

        data = {}
        if tt[1] != "":
            data = json.loads(decompress(tt[1]))
        source_city = None
        source_company = None
        destination_city = None
        destination_company = None
        if "data" in data.keys() and data["data"]["object"]["source_city"] is not None:
            source_city = data["data"]["object"]["source_city"]["name"]
        if "data" in data.keys() and data["data"]["object"]["source_company"] is not None:
            source_company = data["data"]["object"]["source_company"]["name"]
        if "data" in data.keys() and data["data"]["object"]["destination_city"] is not None:
            destination_city = data["data"]["object"]["destination_city"]["name"]
        if "data" in data.keys() and data["data"]["object"]["destination_company"] is not None:
            destination_company = data["data"]["object"]["destination_company"]["name"]
        cargo = None
        cargo_mass = 0
        if "data" in data.keys() and data["data"]["object"]["cargo"] is not None:
            cargo = data["data"]["object"]["cargo"]["name"]
            cargo_mass = data["data"]["object"]["cargo"]["mass"]
        distance = tt[6]
        if distance < 0:
            distance = 0

        profit = tt[4]
        unit = tt[5]

        userinfo = await GetUserInfo(request, userid = tt[0])
        if userid == -1 and app.config.privacy:
            userinfo = await GetUserInfo(request, privacy = True)

        status = 1
        if tt[7] == 0:
            status = 2

        ret.append({"logid": logid, "user": userinfo, "distance": distance, \
            "max_speed": tt[9], "fuel": tt[10], \
            "source_city": source_city, "source_company": source_company, \
                "destination_city": destination_city, "destination_company": destination_company, \
                    "cargo": cargo, "cargo_mass": cargo_mass, "profit": profit, "unit": unit, \
                        "division": division, "challenge": challenge, \
                            "status": status, "views": tt[11], "timestamp": tt[2]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM dlog WHERE logid >= 0 {limit} {timelimit} {speed_limit} {gamelimit} {status_limit}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_dlog(request: Request, response: Response, logid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /dlog', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    userid = -1
    uid = -1
    if authorization is not None:
        au = await auth(authorization, request, allow_application_token = True, check_member = False)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        userid = au["userid"]
        uid = au["uid"]

    if logid is None:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found")}

    await app.db.execute(dhrid, f"SELECT userid, data, timestamp, distance, view_count, trackerid, tracker_type FROM dlog WHERE logid >= 0 AND logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found")}
    await ActivityUpdate(request, uid, f"dlog_{logid}")
    data = {}
    if t[0][1] != "":
        data = json.loads(decompress(t[0][1]))
    if "data" in data.keys():
        del data["data"]["object"]["driver"]
    distance = t[0][3]
    view_count = t[0][4] + 1

    tracker = "unknown"
    trackerid = t[0][5]
    tracker_type = t[0][6]
    if tracker_type == 1:
        tracker = "navio"
    elif tracker_type == 2:
        tracker = "tracksim"
    elif tracker_type == 3:
        tracker = "trucky"
    elif tracker_type == 4:
        tracker = "custom"

    await app.db.execute(dhrid, f"SELECT data FROM telemetry WHERE logid = {logid}")
    p = await app.db.fetchall(dhrid)
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

    division = None
    await app.db.execute(dhrid, f"SELECT divisionid FROM division WHERE logid = {logid} AND status = 1 AND logid >= 0")
    p = await app.db.fetchall(dhrid)
    if len(p) != 0:
        division = p[0][0]

    challenge_record = []
    await app.db.execute(dhrid, f"SELECT challengeid FROM challenge_record WHERE logid = {logid}")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        challenge_record.append(oo[0])

    await app.db.execute(dhrid, f"UPDATE dlog SET view_count = view_count + 1 WHERE logid = {logid}")
    await app.db.commit(dhrid)

    userinfo = None
    if userid == -1 and app.config.privacy:
        userinfo = await GetUserInfo(request, privacy = True)
    else:
        userinfo = await GetUserInfo(request, userid = t[0][0], tell_deleted = True)
        if "is_deleted" in userinfo:
            userinfo = await GetUserInfo(request, -1)

    return {"logid": logid, "user": userinfo, "tracker": tracker, "trackerid": trackerid, \
        "distance": distance, "division": division, "challenge_record": challenge_record, \
            "timestamp": t[0][2], "views": view_count, \
            "detail": data, "telemetry": telemetry}

async def delete_dlog(request: Request, response: Response, logid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /dlog', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, required_permission = ["administrator", "delete_dlogs"], allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if logid is None:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found")}

    await app.db.execute(dhrid, f"SELECT userid FROM dlog WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found")}
    userid = t[0][0]

    await app.db.execute(dhrid, f"DELETE FROM dlog WHERE logid = {logid}")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_delivery", var = {"logid": logid}))

    uid = (await GetUserInfo(request, userid = userid))["uid"]
    await notification(request, "dlog", uid, ml.tr(request, "job_deleted", var = {"logid": logid}, force_lang = await GetUserLanguage(request, uid)))

    return Response(status_code=204)
