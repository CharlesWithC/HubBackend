# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special", "minimum_average_speed", "maximum_average_speed", "minimum_average_fuel", "maximum_average_fuel"]
JOB_REQUIREMENT_TYPE = {"source_city_id": convertQuotation, "source_company_id": convertQuotation, "destination_city_id": convertQuotation, "destination_company_id": convertQuotation, "minimum_distance": int, "cargo_id": convertQuotation, "minimum_cargo_mass": int, "maximum_cargo_damage": float, "maximum_speed": int, "maximum_fuel": int, "minimum_profit": int, "maximum_profit": int, "maximum_offence": int, "allow_overspeed": int, "allow_auto_park": int, "allow_auto_load": int, "must_not_be_late": int, "must_be_special": int, "minimum_average_speed": int, "maximum_average_speed": int, "minimum_average_fuel": float, "maximum_average_fuel": float}
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0, "minimum_average_speed": -1, "maximum_average_speed": -1, "minimum_average_fuel": -1, "maximum_average_fuel": -1}

# PLANS

# Remember to add challenge points for /member/roles/rank and /dlog/leaderboard
# Remember to add "challenge_record" = challengeid[] for /dlog/list and /dlog

# For company challenge, challenge_record will still be bound to personal userid.
# Completed company challenges are no longer allowed to be edited.


# GET /challenges/list
# REQUEST PARAM
# - string: title (search)
# - integer: start_time
# - integer: end_time
# - integer: challenge_type
# - integer: required_role
# - integer: minimum_required_distance
# - integer: maximum_required_distance
# - integer: userid - to show challenges that user participated
# - boolean: must_have_completed (if userid is specified, show challenges that user completed, including completed company challenge)
#                       otherwise show all completed challenges
# - string: order (asc / desc)
# - string: order_by (start_time / end_time / title / required_distance / reward_points / delivery_count)
# - integer: page
# - integer: page_size (max = 100)
# RETURN
# challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, required_distance, reward_points
# if userid is specified, then add "finished_delivery_count"

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, after_challengeid: Optional[int] = None, \
        query: Optional[str] = "", \
        after: Optional[int] = None, before: Optional[int] = None, challenge_type: Optional[int] = None,
        required_role: Optional[int] = None, \
        minimum_required_distance: Optional[int] = None, maximum_required_distance: Optional[int] = None,\
        userid: Optional[int] = None, must_have_completed: Optional[bool] = False, \
        order: Optional[str] = "desc", order_by: Optional[str] = "reward_points"):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'GET /challenges/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(request, au["uid"], "challenges")
    if page_size <= 0:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    query_limit = "WHERE challengeid >= 0 "

    if query != "":
        query = convertQuotation(query).lower()
        query_limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "

    if after is not None:
        query_limit += f"AND start_time >= {after} "
    if before is not None:
        query_limit += f"AND end_time <= {before} "

    if challenge_type in [1,2,3]:
        query_limit += f"AND challenge_type = {challenge_type} "

    if required_role is not None:
        query_limit += f"AND required_roles LIKE '%,{required_role},%' "

    if minimum_required_distance is not None:
        query_limit += f"AND required_distance >= {minimum_required_distance} "
    if maximum_required_distance is not None:
        query_limit += f"AND required_distance <= {maximum_required_distance} "

    if userid is not None:
        query_limit += f"AND challengeid IN (SELECT challengeid FROM challenge_record WHERE userid = {userid}) "
    if userid is None:
        userid = au["userid"]

    # start_time / end_time / title / required_distance / reward_points / delivery_count
    if order_by not in ["challengeid", "title", "start_time", "end_time", "required_distance", "reward_points", "delivery_count", "orderid"]:
        order_by = "reward_points"
        order = "desc"

    if order not in ["asc", "desc"]:
        order = "asc"

    query_limit += f"ORDER BY is_pinned DESC, {order_by} {order}, challengeid DESC"

    ret = []

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT challengeid FROM challenge {query_limit}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_challengeid is not None:
        for tt in t:
            if tt[0] == after_challengeid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, required_distance, reward_points, description, public_details, orderid, is_pinned, timestamp FROM challenge {query_limit} LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        current_delivery_count = 0
        if tt[4] in [1,3]:
            await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]} AND userid = {userid}")
        elif tt[4] == 2:
            await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]}")
        elif tt[4] == 4:
            await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {tt[0]} AND challenge_record.userid = {userid}")
        elif tt[4] == 5:
            await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {tt[0]}")
        current_delivery_count = await app.db.fetchone(dhrid)
        current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

        required_roles = str2list(tt[6])

        completed = 0
        await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {tt[0]} ORDER BY points DESC, timestamp ASC, userid ASC")
        p = await app.db.fetchall(dhrid)
        completed = len(p)

        if must_have_completed:
            if tt[4] in [1,3,4]:
                await app.db.execute(dhrid, f"SELECT challengeid FROM challenge_completed WHERE challengeid = {tt[0]} AND userid = {userid}")
                p = await app.db.fetchall(dhrid)
                if len(p) == 0:
                    continue
            elif tt[4] in [2,5]:
                await app.db.execute(dhrid, f"SELECT challengeid FROM challenge_completed WHERE challengeid = {tt[0]}")
                p = await app.db.fetchall(dhrid)
                if len(p) == 0:
                    continue

        ret.append({"challengeid": tt[0], "title": tt[1], "description": decompress(tt[9]), \
                "start_time": tt[2], "end_time": tt[3],\
                "challenge_type": tt[4], "delivery_count": tt[5], "current_delivery_count": current_delivery_count, \
                "required_roles": required_roles, "required_distance": tt[7], "reward_points": tt[8], "public_details": TF[tt[10]], "orderid": tt[11], "is_pinned": TF[tt[12]], "timestamp": tt[13], "completed": completed})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

# GET /challenge
# REQUEST PARAM
# - integer: challengeid
# returns requirement if public_details = true and user is not staff
#                     or if public_details = false

async def get_challenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None), userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /challenges', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    if userid is None:
        userid = au["userid"]
    isstaff = checkPerm(app, au["roles"], ["admin", "challenge"])

    await ActivityUpdate(request, au["uid"], "challenges")

    await app.db.execute(dhrid, f"SELECT challengeid, title, start_time, end_time, challenge_type, \
            delivery_count, required_roles, required_distance, reward_points, public_details, job_requirements, \
            description, orderid, is_pinned, timestamp FROM challenge WHERE challengeid = {challengeid} \
                AND challengeid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    tt = t[0]
    public_details = tt[9]
    jobreq = {}
    if public_details or isstaff:
        p = json.loads(decompress(tt[10]))
        jobreq = {}
        for i in range(0,len(p)):
            jobreq[JOB_REQUIREMENTS[i]] = JOB_REQUIREMENT_TYPE[JOB_REQUIREMENTS[i]](p[i])

    current_delivery_count = 0
    if tt[4] in [1,3]:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif tt[4] == 2:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif tt[4] == 4:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif tt[4] == 5:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await app.db.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    required_roles = str2list(tt[6])

    completed = []
    await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid} ORDER BY points DESC, timestamp ASC, userid ASC")
    p = await app.db.fetchall(dhrid)
    for pp in p:
        completed.append({"user": await GetUserInfo(request, userid = pp[0]), "points": pp[1], "timestamp": pp[2]})

    return {"challengeid": tt[0], "title": tt[1], "description": decompress(tt[11]), "start_time": tt[2], "end_time": tt[3], "challenge_type": tt[4], "delivery_count": tt[5], "current_delivery_count": current_delivery_count, "required_roles": required_roles, "required_distance": tt[7], "reward_points": tt[8], "public_details": TF[public_details], "orderid": tt[12], "is_pinned": TF[tt[13]], "timestamp": tt[14], "job_requirements": jobreq, "completed": completed}

# POST /challenge
# Note: Check if there're at most 15 active challenges
# JSON DATA:
# - string: title
# - integer: start_time
# - integer: end_time
# - integer: challenge_type (1 = personal (one-time) | 2 = company | 3 = personal (recurring) | 4 = personal (distance-based) | 5 = company (distance-based))
# - integer: delivery_count
# - string: required_roles (or) (separate with ',' | default = 'any')
# - integer: required_distance
# - integer: reward_points
# - boolean: public_details
# - string(json): job_requirements
#   - integer: minimum_distance
#   - string: source_city_id
#   - string: source_company_id
#   - string: destination_city_id
#   - string: destination_company_id
#   - string: cargo_id
#   - integer: minimum_cargo_mass
#   - float: maximum_cargo_damage
#   - integer: maximum_speed
#   - integer: maximum_fuel
#   - integer: minimum_profit
#   - integer: maximum_profit
#   - integer: maximum_offence
#   - boolean: allow_overspeed
#   - boolean: allow_auto_park
#   - boolean: allow_auto_load
#   - boolean: must_not_be_late
#   - boolean: must_be_special
#   - integer: minimum_average_speed
#   - integer: maximum_average_speed
#   - float: minimum_average_fuel (L/100km)
#   - float: maximum_average_fuel (L/100km)

async def post_challenge(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /challenges', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())}")
    tot = await app.db.fetchone(dhrid)
    tot = tot[0]
    tot = 0 if tot is None else int(tot)
    if tot >= 15:
        response.status_code = 503
        return {"error": ml.tr(request, "maximum_15_active_challenge", force_lang = au["language"])}

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        description = compress(data["description"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        start_time = int(data["start_time"])
        if abs(start_time) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "start_time", "limit": "2,147,483,647"}, force_lang = au["language"])}
        end_time = int(data["end_time"])
        if abs(end_time) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "end_time", "limit": "2,147,483,647"}, force_lang = au["language"])}
        challenge_type = int(data["challenge_type"])
        if abs(challenge_type) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "challenge_type", "limit": "2,147,483,647"}, force_lang = au["language"])}
        delivery_count = int(data["delivery_count"])
        if abs(delivery_count) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "delivery_count", "limit": "2,147,483,647"}, force_lang = au["language"])}
        required_roles = data["required_roles"]
        required_distance = int(data["required_distance"])
        if abs(required_distance) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "required_distance", "limit": "2,147,483,647"}, force_lang = au["language"])}
        reward_points = int(data["reward_points"])
        if abs(reward_points) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "reward_points", "limit": "2,147,483,647"}, force_lang = au["language"])}
        public_details = int(bool(data["public_details"]))
        job_requirements = data["job_requirements"]
        if type(required_roles) != list or type(job_requirements) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        if "orderid" not in data.keys():
            data["orderid"] = 0
        if "is_pinned" not in data.keys():
            data["is_pinned"] = False
        orderid = int(data["orderid"])
        if abs(orderid) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if start_time >= end_time:
        response.status_code = 400
        return {"error": ml.tr(request, "start_time_must_be_earlier_than_end_time", force_lang = au["language"])}

    if challenge_type not in [1, 2, 3, 4, 5]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_challenge_type", force_lang = au["language"])}

    roles = required_roles
    rolereq = []
    for role in roles:
        if role == "":
            continue
        try:
            rolereq.append(int(role))
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_required_roles", force_lang = au["language"])}
    rolereq = rolereq[:20]
    required_roles = "," + list2str(rolereq) + ","

    if delivery_count <= 0:
        response.status_code = 400
        if challenge_type in [1, 2, 3]:
            return {"error": ml.tr(request, "invalid_delivery_count", force_lang = au["language"])}
        elif challenge_type in [4, 5]:
            return {"error": ml.tr(request, "invalid_distance_sum", force_lang = au["language"])}

    if required_distance < 0:
        required_distance = 0

    if reward_points < 0:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_reward_points", force_lang = au["language"])}

    jobreq = []
    for req in JOB_REQUIREMENTS:
        if req in job_requirements:
            jobreq.append(JOB_REQUIREMENT_TYPE[req](job_requirements[req]))
        else:
            jobreq.append(JOB_REQUIREMENT_DEFAULT[req])
    jobreq = compress(json.dumps(jobreq, separators=(',', ':')))

    await app.db.execute(dhrid, f"INSERT INTO challenge(userid, title, description, start_time, end_time, challenge_type, orderid, is_pinned, delivery_count, required_roles, required_distance, reward_points, public_details, job_requirements, timestamp) VALUES ({au['userid']}, '{title}', '{description}', {start_time}, {end_time}, {challenge_type}, {orderid}, {is_pinned}, {delivery_count}, '{required_roles}', {required_distance}, {reward_points}, {public_details}, '{jobreq}', {int(time.time())})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    challengeid = (await app.db.fetchone(dhrid))[0]

    await AuditLog(request, au["uid"], ml.ctr(request, "created_challenge", var = {"id": challengeid}))

    await notification_to_everyone(request, "new_challenge", ml.spl("new_challenge_with_title", var = {"title": title}),     discord_embed = {"title": title, "description": decompress(description), "fields": [{"name": ml.spl("start"), "value": f"<t:{start_time}:R>", "inline": True}, {"name": ml.spl("end"), "value": f"<t:{end_time}:R>", "inline": True}, {"name": ml.spl("reward_points"), "value": f"{reward_points}", "inline": True}], "footer": {"text": ml.spl("new_challenge"), "icon_url": app.config.logo_url}})

    return {"challengeid": challengeid}

# PATCH /challenge
# REQUEST PARAM
# - integer: challengeid
# JSON DATA
# *Same as POST /challenge

async def patch_challenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'PATCH /challenges', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, start_time, end_time, challenge_type, orderid, is_pinned, delivery_count, required_roles, required_distance, reward_points, public_details, job_requirements FROM challenge WHERE challengeid = {challengeid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    (title, description, start_time, end_time, challenge_type, orderid, is_pinned, delivery_count, required_roles, required_distance, reward_points, public_details, jobreq) = t[0]
    org_delivery_count = delivery_count
    title = convertQuotation(title)

    data = await request.json()
    try:
        if "title" in data.keys():
            title = convertQuotation(data["title"])
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}

        if "description" in data.keys():
            description = compress(data["description"])
            if len(data["description"]) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}

        if "start_time" in data.keys():
            start_time = int(data["start_time"])
            if abs(start_time) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "start_time", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "end_time" in data.keys():
            end_time = int(data["end_time"])
            if abs(end_time) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "end_time", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if start_time >= end_time:
            response.status_code = 400
            return {"error": ml.tr(request, "start_time_must_be_earlier_than_end_time", force_lang = au["language"])}

        if "delivery_count" in data.keys():
            delivery_count = int(data["delivery_count"])
            if abs(delivery_count) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "delivery_count", "limit": "2,147,483,647"}, force_lang = au["language"])}
            if delivery_count <= 0:
                response.status_code = 400
                if challenge_type in [1, 2, 3]:
                    return {"error": ml.tr(request, "invalid_delivery_count", force_lang = au["language"])}
                elif challenge_type in [4, 5]:
                    return {"error": ml.tr(request, "invalid_distance_sum", force_lang = au["language"])}

        if "required_roles" in data.keys():
            required_roles = data["required_roles"]
            if type(required_roles) != list:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            roles = required_roles
            rolereq = []
            for role in roles:
                if role == "":
                    continue
                try:
                    rolereq.append(int(role))
                except:
                    response.status_code = 400
                    return {"error": ml.tr(request, "invalid_required_roles", force_lang = au["language"])}
            rolereq = rolereq[:20]
            required_roles = "," + list2str(rolereq) + ","

        if "required_distance" in data.keys():
            required_distance = int(data["required_distance"])
            if required_distance < 0:
                required_distance = 0
            if abs(required_distance) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "required_distance", "limit": "2,147,483,647"}, force_lang = au["language"])}

        if "reward_points" in data.keys():
            reward_points = int(data["reward_points"])
            if abs(reward_points) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "reward_points", "limit": "2,147,483,647"}, force_lang = au["language"])}
            if reward_points < 0:
                response.status_code = 400
                return {"error": ml.tr(request, "invalid_reward_points", force_lang = au["language"])}

        if "public_details" in data.keys():
            public_details = int(bool(data["public_details"]))

        if "job_requirements" in data.keys():
            job_requirements = data["job_requirements"]
            if type(job_requirements) != dict:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            jobreq = []
            for req in JOB_REQUIREMENTS:
                if req in job_requirements:
                    jobreq.append(JOB_REQUIREMENT_TYPE[req](job_requirements[req]))
                else:
                    jobreq.append(JOB_REQUIREMENT_DEFAULT[req])
            jobreq = compress(json.dumps(jobreq, separators=(',', ':')))

        if "orderid" in data.keys():
            orderid = int(data["orderid"])
            if abs(orderid) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}

        if "is_pinned" in data.keys():
            is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE challenge SET title = '{title}', description = '{description}', \
            start_time = '{start_time}', end_time = '{end_time}', \
            orderid = {orderid}, is_pinned = {is_pinned}, \
            delivery_count = {delivery_count}, required_roles = '{required_roles}', \
            required_distance = {required_distance}, reward_points = {reward_points}, public_details = {public_details}, \
            job_requirements = '{jobreq}' WHERE challengeid = {challengeid}")
    await app.db.commit(dhrid)

    if challenge_type == 1:
        original_points = {}
        await app.db.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        await app.db.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await app.db.commit(dhrid)

        if org_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {org_delivery_count} AND COUNT(*) < {delivery_count}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                if len(p) > 0:
                    await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                    uid = (await GetUserInfo(request, userid = userid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_uncompleted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        elif org_delivery_count > delivery_count:
            await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {delivery_count} AND COUNT(*) < {org_delivery_count}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                if len(p) == 0:
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                    uid = (await GetUserInfo(request, userid = userid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_completed_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        else:
            for userid in original_points.keys():
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                if original_points[userid] < reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points - original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))
                elif original_points[userid] > reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(- reward_points + original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 4:
        original_points = {}
        await app.db.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        await app.db.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await app.db.commit(dhrid)

        if org_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT challenge_record.userid FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid \
                HAVING SUM(dlog.distance) >= {org_delivery_count} AND SUM(dlog.distance) < {delivery_count}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                if len(p) > 0:
                    await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                    uid = (await GetUserInfo(request, userid = userid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_uncompleted_increased_distance_sum", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        elif org_delivery_count > delivery_count:
            await app.db.execute(dhrid, f"SELECT challenge_record.userid FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid \
                HAVING SUM(dlog.distance) >= {delivery_count} AND SUM(dlog.distance) < {org_delivery_count}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                if len(p) == 0:
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                    uid = (await GetUserInfo(request, userid = userid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_completed_decreased_distance_sum", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        else:
            for userid in original_points.keys():
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                if original_points[userid] < reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points - original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))
                elif original_points[userid] > reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(- reward_points + original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 3:
        original_points = {}
        await app.db.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        completed_count = {}
        await app.db.execute(dhrid, f"SELECT userid, COUNT(*) FROM challenge_completed WHERE challengeid = {challengeid} GROUP BY userid")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            completed_count[tt[0]] = tt[1]

        await app.db.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await app.db.commit(dhrid)

        if org_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]

                await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                current_delivery_count = await app.db.fetchone(dhrid)
                current_delivery_count = current_delivery_count[0]
                current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)

                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                p = await app.db.fetchall(dhrid)
                if current_delivery_count < len(p) * delivery_count:
                    delete_cnt = len(p) - int(current_delivery_count / delivery_count)
                    left_cnt = int(current_delivery_count / delivery_count)
                    if delete_cnt > 0:
                        await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid} ORDER BY timestamp DESC LIMIT {delete_cnt}")
                        uid = (await GetUserInfo(request, userid = userid))["uid"]
                        if delete_cnt > 1:
                            await notification(request, "challenge", uid, ml.tr(request, "n_personal_recurring_challenge_uncompelted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "count": delete_cnt, "points": tseparator(p[0][0] * delete_cnt), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(request, uid)))
                        else:
                            await notification(request, "challenge", uid, ml.tr(request, "one_personal_recurring_challenge_uncompelted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0]), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)

        elif org_delivery_count > delivery_count:
            await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                userid = tt[0]

                await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                current_delivery_count = await app.db.fetchone(dhrid)
                current_delivery_count = current_delivery_count[0]
                current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)

                await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                p = await app.db.fetchall(dhrid)
                if current_delivery_count >= (len(p)+1) * delivery_count:
                    add_cnt = int(current_delivery_count / delivery_count) - len(p)
                    left_cnt = int(current_delivery_count / delivery_count)
                    if add_cnt > 0:
                        for _ in range(add_cnt):
                            await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                        uid = (await GetUserInfo(request, userid = userid))["uid"]
                        if add_cnt > 1:
                            await notification(request, "challenge", uid, ml.tr(request, "n_personal_recurring_challenge_compelted_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "count": add_cnt, "points": tseparator(reward_points * add_cnt), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(request, uid)))
                        else:
                            await notification(request, "challenge", uid, ml.tr(request, "one_personal_recurring_challenge_compelted_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)

        else:
            for userid in original_points.keys():
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                if original_points[userid] < reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator((reward_points - original_points[userid]) * completed_count[userid]), "total_points": tseparator(reward_points * completed_count[userid])}, force_lang = await GetUserLanguage(request, uid)))
                elif original_points[userid] > reward_points:
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator((- reward_points + original_points[userid]) * completed_count[userid]), "total_points": tseparator(reward_points * completed_count[userid])}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 2:
        curtime = int(time.time())

        await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
        t = await app.db.fetchall(dhrid)
        previously_completed = {}
        if len(t) != 0:
            await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await app.db.fetchall(dhrid)
            for pp in p:
                previously_completed[pp[0]] = (pp[1], pp[2])
            await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await app.db.commit(dhrid)

        await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
        t = await app.db.fetchall(dhrid)
        if len(t) == delivery_count:
            usercnt = {}
            for tt in t:
                tuserid = tt[0]
                if tuserid not in usercnt.keys():
                    usercnt[tuserid] = 1
                else:
                    usercnt[tuserid] += 1
            for tuserid in usercnt.keys():
                s = usercnt[tuserid]
                reward = round(reward_points * s / delivery_count)
                if tuserid in previously_completed.keys():
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {previously_completed[tuserid][1]})")
                    gap = reward - previously_completed[tuserid][0]
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    if gap > 0:
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                    elif gap < 0:
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                    del previously_completed[tuserid]
                else:
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        for tuserid in previously_completed.keys():
            reward = previously_completed[tuserid][0]
            uid = (await GetUserInfo(request, userid = tuserid))["uid"]
            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 5:
        curtime = int(time.time())

        await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
        t = await app.db.fetchall(dhrid)
        previously_completed = {}
        if len(t) != 0:
            await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await app.db.fetchall(dhrid)
            for pp in p:
                previously_completed[pp[0]] = (pp[1], pp[2])
            await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await app.db.commit(dhrid)

        current_delivery_count = 0
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
        current_delivery_count = await app.db.fetchone(dhrid)
        current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

        if current_delivery_count >= delivery_count:
            await app.db.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid")
            t = await app.db.fetchall(dhrid)
            usercnt = {}
            totalcnt = 0
            for tt in t:
                totalcnt += tt[1]
                tuserid = tt[0]
                if tuserid not in usercnt.keys():
                    usercnt[tuserid] = tt[1] - max(totalcnt - delivery_count, 0)
                else:
                    usercnt[tuserid] += tt[1] - max(totalcnt - delivery_count, 0)
                if totalcnt >= delivery_count:
                    break
            for tuserid in usercnt.keys():
                s = usercnt[tuserid]
                reward = round(reward_points * s / delivery_count)
                if tuserid in previously_completed.keys():
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {previously_completed[tuserid][1]})")
                    gap = reward - previously_completed[tuserid][0]
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    if gap > 0:
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                    elif gap < 0:
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                    del previously_completed[tuserid]
                else:
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.commit(dhrid)
        for tuserid in previously_completed.keys():
            reward = previously_completed[tuserid][0]
            uid = (await GetUserInfo(request, userid = tuserid))["uid"]
            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

    await AuditLog(request, au["uid"], ml.ctr(request, "updated_challenge", var = {"id": challengeid}))

    return Response(status_code=204)

# DELETE /challenge
# REQUEST PARAM
# - integer: challengeid

async def delete_challenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /challenges', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT * FROM challenge WHERE challengeid = {challengeid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM challenge WHERE challengeid = {challengeid}")
    await app.db.execute(dhrid, f"DELETE FROM challenge_record WHERE challengeid = {challengeid}")
    await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_challenge", var = {"id": challengeid}))

    return Response(status_code=204)

# PUT /challenges/delivery
# REQUEST PARAM
# - integer: challengeid
# - integer: logid
# => manually accept a delivery as challenge

async def put_delivery(request: Request, response: Response, challengeid: int, logid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'PUT /challenges/delivery', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    await app.db.execute(dhrid, f"SELECT * FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "challenge_delivery_already_accepted", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid, timestamp FROM dlog WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    userid = t[0][0]
    timestamp = t[0][1]
    await app.db.execute(dhrid, f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {timestamp})")
    await app.db.commit(dhrid)
    uid = (await GetUserInfo(request, userid = userid))["uid"]
    await notification(request, "challenge", uid, ml.tr(request, "delivery_added_to_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(request, uid)))

    current_delivery_count = 0
    if challenge_type in [1,3]:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif challenge_type == 2:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif challenge_type == 4:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif challenge_type == 5:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await app.db.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    if current_delivery_count >= delivery_count:
        if challenge_type in [1, 4]:
            await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                await app.db.commit(dhrid)
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "personal_onetime_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))

        elif challenge_type == 3:
            await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
            t = await app.db.fetchall(dhrid)
            if current_delivery_count >= (len(t) + 1) * delivery_count:
                await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                await app.db.commit(dhrid)
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "recurring_challenge_completed_status_added", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator((len(t)+1) * reward_points)}, force_lang = await GetUserLanguage(request, uid)))

        elif challenge_type == 2:
            await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                curtime = int(time.time())
                await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                t = await app.db.fetchall(dhrid)
                usercnt = {}
                for tt in t:
                    tuserid = tt[0]
                    if tuserid not in usercnt.keys():
                        usercnt[tuserid] = 1
                    else:
                        usercnt[tuserid] += 1
                for tuserid in usercnt.keys():
                    s = usercnt[tuserid]
                    reward = round(reward_points * s / delivery_count)
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                await app.db.commit(dhrid)

        elif challenge_type == 5:
            await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                curtime = int(time.time())
                await app.db.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                    INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                    WHERE challenge_record.challengeid = {challengeid} \
                    GROUP BY dlog.userid, challenge_record.userid")
                t = await app.db.fetchall(dhrid)
                usercnt = {}
                totalcnt = 0
                for tt in t:
                    totalcnt += tt[1]
                    tuserid = tt[0]
                    if tuserid not in usercnt.keys():
                        usercnt[tuserid] = tt[1] - max(totalcnt - delivery_count, 0)
                    else:
                        usercnt[tuserid] += tt[1] - max(totalcnt - delivery_count, 0)
                    if totalcnt >= delivery_count:
                        break
                for tuserid in usercnt.keys():
                    s = usercnt[tuserid]
                    reward = round(reward_points * s / delivery_count)
                    await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                    await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "added_delivery_to_challenge", var = {"id": challengeid, "logid": logid}))

    return Response(status_code=204)

# DELETE /challenges/delivery
# REQUEST PARAM
# - integer: challengeid
# - integer: logid
# => denies a delivery as challenge

async def delete_delivery(request: Request, response: Response, challengeid: int, logid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'DELETE /challenges/delivery', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_delivery_not_found", force_lang = au["language"])}
    userid = t[0][0]

    await app.db.execute(dhrid, f"DELETE FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    await app.db.commit(dhrid)
    uid = (await GetUserInfo(request, userid = userid))["uid"]
    await notification(request, "challenge", uid, ml.tr(request, "delivery_removed_from_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(request, uid)))

    current_delivery_count = 0
    if challenge_type in [1,3]:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif challenge_type == 2:
        await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif challenge_type == 4:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif challenge_type == 5:
        await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await app.db.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    if challenge_type in [1, 4]:
        if current_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
            p = await app.db.fetchall(dhrid)
            if len(p) > 0:
                await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                await app.db.commit(dhrid)
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 3:
        await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
        p = await app.db.fetchall(dhrid)
        if current_delivery_count < len(p) * delivery_count:
            await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid} ORDER BY timestamp DESC LIMIT 1")
            await app.db.commit(dhrid)
            uid = (await GetUserInfo(request, userid = userid))["uid"]
            if len(p) <= 1:
                await notification(request, "challenge", uid, ml.tr(request, "one_personal_recurring_challenge_uncompleted", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(request, uid)))
            elif len(p) > 1:
                await notification(request, "challenge", uid, ml.tr(request, "one_personal_recurring_challenge_uncompleted_still_have_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0]), "total_points": tseparator(p[0][0] * (len(p) - 1))}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 2:
        if current_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await app.db.fetchall(dhrid)
            if len(p) > 0:
                userid = p[0][0]
                points = p[0][1]
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await app.db.commit(dhrid)

        else:
            curtime = int(time.time())

            await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await app.db.fetchall(dhrid)
            previously_completed = {}
            if len(t) != 0:
                await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                for pp in p:
                    previously_completed[pp[0]] = (pp[1], pp[2])
                await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
                await app.db.commit(dhrid)

                await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                t = await app.db.fetchall(dhrid)
                usercnt = {}
                for tt in t:
                    tuserid = tt[0]
                    if tuserid not in usercnt.keys():
                        usercnt[tuserid] = 1
                    else:
                        usercnt[tuserid] += 1
                for tuserid in usercnt.keys():
                    s = usercnt[tuserid]
                    reward = round(reward_points * s / delivery_count)
                    if tuserid in previously_completed.keys():
                        await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {previously_completed[tuserid][1]})")
                        gap = reward - previously_completed[tuserid][0]
                        uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                        if gap > 0:
                            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                        elif gap < 0:
                            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                        del previously_completed[tuserid]
                    else:
                        await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                        uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                await app.db.commit(dhrid)
            for tuserid in previously_completed.keys():
                reward = previously_completed[tuserid][0]
                uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

    elif challenge_type == 5:
        if current_delivery_count < delivery_count:
            await app.db.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await app.db.fetchall(dhrid)
            if len(p) > 0:
                userid = p[0][0]
                points = p[0][1]
                uid = (await GetUserInfo(request, userid = userid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
            await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await app.db.commit(dhrid)

        else:
            curtime = int(time.time())

            await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await app.db.fetchall(dhrid)
            previously_completed = {}
            if len(t) != 0:
                await app.db.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
                p = await app.db.fetchall(dhrid)
                for pp in p:
                    previously_completed[pp[0]] = (pp[1], pp[2])
                await app.db.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
                await app.db.commit(dhrid)

                await app.db.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                    INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                    WHERE challenge_record.challengeid = {challengeid} \
                    GROUP BY dlog.userid, challenge_record.userid")
                t = await app.db.fetchall(dhrid)
                usercnt = {}
                totalcnt = 0
                for tt in t:
                    totalcnt += tt[1]
                    tuserid = tt[0]
                    if tuserid not in usercnt.keys():
                        usercnt[tuserid] = tt[1] - max(totalcnt - delivery_count, 0)
                    else:
                        usercnt[tuserid] += tt[1] - max(totalcnt - delivery_count, 0)
                    if totalcnt >= delivery_count:
                        break
                for tuserid in usercnt.keys():
                    s = usercnt[tuserid]
                    reward = round(reward_points * s / delivery_count)
                    if tuserid in previously_completed.keys():
                        await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {previously_completed[tuserid][1]})")
                        gap = reward - previously_completed[tuserid][0]
                        uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                        if gap > 0:
                            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                        elif gap < 0:
                            await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                        del previously_completed[tuserid]
                    else:
                        await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")
                        uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                        await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                await app.db.commit(dhrid)
            for tuserid in previously_completed.keys():
                reward = previously_completed[tuserid][0]
                uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

    await AuditLog(request, au["uid"], ml.ctr(request, "removed_delivery_from_challenge", var = {"id": challengeid, "logid": logid}))

    return Response(status_code=204)
