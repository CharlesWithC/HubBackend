# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special", "minimum_average_speed", "maximum_average_speed", "minimum_average_fuel", "maximum_average_fuel"]
JOB_REQUIREMENT_TYPE = {"source_city_id": convert_quotation, "source_company_id": convert_quotation, "destination_city_id": convert_quotation, "destination_company_id": convert_quotation, "minimum_distance": int, "cargo_id": convert_quotation, "minimum_cargo_mass": int, "maximum_cargo_damage": float, "maximum_speed": int, "maximum_fuel": int, "minimum_profit": int, "maximum_profit": int, "maximum_offence": int, "allow_overspeed": int, "allow_auto_park": int, "allow_auto_load": int, "must_not_be_late": int, "must_be_special": int, "minimum_average_speed": int, "maximum_average_speed": int, "minimum_average_fuel": float, "maximum_average_fuel": float}
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0, "minimum_average_speed": -1, "maximum_average_speed": -1, "minimum_average_fuel": -1, "maximum_average_fuel": -1}

# PLANS

# Remember to add challenge points for /member/roles/rank and /dlog/leaderboard
# Remember to add "challenge_record" = challengeid[] for /dlog/list and /dlog

# For company challenge, challenge_record will still be bound to personal userid. 
# Completed company challenges are no longer allowed to be edited.


# GET /challenge/list
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
@app.get(f"/{config.abbr}/challenge/list")
async def getChallengeList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, title: Optional[str] = "", \
        start_time: Optional[int] = -1, end_time: Optional[int] = -1, challenge_type: Optional[int] = 0,
        required_role: Optional[int] = -1, minimum_required_distance: Optional[int] = -1, maximum_required_distance: Optional[int] = -1,\
        userid: Optional[int] = -1, must_have_completed: Optional[bool] = False, \
        order: Optional[str] = "desc", order_by: Optional[str] = "reward_points"):

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /challenge/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(dhrid, au["discordid"], f"challenges")
    
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 1
    elif page_size >= 100:
        page_size = 100
    
    query_limit = "WHERE challengeid >= 0 "

    if title != "":
        title = convert_quotation(title).lower()
        query_limit += f"AND LOWER(title) LIKE '%{title[:200]}%' "

    if start_time != -1 and end_time != -1:
        query_limit += f"AND start_time >= {start_time} AND end_time <= {end_time} "
    else:
        query_limit += f"AND end_time >= {end_time - 86400} "
    
    if challenge_type in [1,2,3]:
        query_limit += f"AND challenge_type = {challenge_type} "
    
    if required_role != -1:
        query_limit += f"AND required_roles LIKE '%,{required_role},%' "

    if minimum_required_distance != -1:
        query_limit += f"AND required_distance >= {minimum_required_distance} "
    if maximum_required_distance != -1:
        query_limit += f"AND required_distance <= {maximum_required_distance} "
    
    if userid != -1:
        query_limit += f"AND challengeid IN (SELECT challengeid FROM challenge_record WHERE userid = {userid}) "
    if userid == -1:
        userid = au["userid"]
    
    # start_time / end_time / title / required_distance / reward_points / delivery_count
    if not order_by in ["challengeid", "title", "start_time", "end_time", "required_distance", "reward_points", "delivery_count"]:
        order_by = "reward_points"
        order = "desc"
    
    if not order.lower() in ["asc", "desc"]:
        order = "asc"
    
    query_limit += f"ORDER BY {order_by} {order.upper()}"

    ret = []

    await aiosql.execute(dhrid, f"SELECT challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, \
            required_distance, reward_points, description, public_details FROM challenge {query_limit} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        current_delivery_count = 0
        if tt[4] in [1,3]:
            await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]} AND userid = {userid}")
        elif tt[4] == 2:
            await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]}")
        elif tt[4] == 4:
            await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {tt[0]} AND challenge_record.userid = {userid}")
        elif tt[4] == 5:
            await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {tt[0]}")
        current_delivery_count = await aiosql.fetchone(dhrid)
        current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

        required_roles = tt[6].split(",")[1:-1]
        required_roles = [int(x) for x in required_roles if x != ""]
        
        completed = 0
        await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {tt[0]} ORDER BY points DESC, timestamp ASC, userid ASC")
        p = await aiosql.fetchall(dhrid)
        completed = len(p)

        if must_have_completed:
            if tt[4] in [1,3,4]:
                await aiosql.execute(dhrid, f"SELECT challengeid FROM challenge_completed WHERE challengeid = {tt[0]} AND userid = {userid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) == 0:
                    continue
            elif tt[4] in [2,5]:
                await aiosql.execute(dhrid, f"SELECT challengeid FROM challenge_completed WHERE challengeid = {tt[0]}")
                p = await aiosql.fetchall(dhrid)
                if len(p) == 0:
                    continue

        ret.append({"challengeid": tt[0], "title": tt[1], "description": decompress(tt[9]), \
                "start_time": tt[2], "end_time": tt[3],\
                "challenge_type": tt[4], "delivery_count": tt[5], "current_delivery_count": current_delivery_count, \
                "required_roles": required_roles, "required_distance": tt[7], "reward_points": tt[8], "public_details": TF[tt[10]], "completed": completed})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge {query_limit}")
    t = await aiosql.fetchall(dhrid)
    
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

# GET /challenge
# REQUEST PARAM
# - integer: challengeid
# returns requirement if public_details = true and user is not staff
#                     or if public_details = false
@app.get(f"/{config.abbr}/challenge/{{challengeid}}")
async def getChallenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None), userid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /challenge', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    if userid == -1:
        userid = au["userid"]
    isstaff = False
    staffau = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if not staffau["error"]:
        isstaff = True

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await ActivityUpdate(dhrid, au["discordid"], f"challenges")

    await aiosql.execute(dhrid, f"SELECT challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, \
            required_distance, reward_points, public_details, job_requirements, description FROM challenge WHERE challengeid = {challengeid} \
                AND challengeid >= 0")
    t = await aiosql.fetchall(dhrid)
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
            jobreq[JOB_REQUIREMENTS[i]] = str(p[i])

    current_delivery_count = 0
    if tt[4] in [1,3]:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif tt[4] == 2:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif tt[4] == 4:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif tt[4] == 5:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await aiosql.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    required_roles = tt[6].split(",")[1:-1]
    required_roles = [int(x) for x in required_roles if x != ""]
    
    completed = []
    await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid} ORDER BY points DESC, timestamp ASC, userid ASC")
    p = await aiosql.fetchall(dhrid)
    for pp in p:
        completed.append({"user": await GetUserInfo(dhrid, request, userid = pp[0]), "points": str(pp[1]), "timestamp": pp[2]})

    return {"challengeid": tt[0], "title": tt[1], "description": decompress(tt[11]), "start_time": tt[2], "end_time": tt[3], "challenge_type": tt[4], "delivery_count": tt[5], "current_delivery_count": current_delivery_count, "required_roles": required_roles, "required_distance": tt[7], "reward_points": tt[8], "public_details": TF[public_details], "job_requirements": jobreq, "completed": completed}

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

@app.post(f"/{config.abbr}/challenge")
async def postChallenge(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /challenge', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())}")
    tot = await aiosql.fetchone(dhrid)
    tot = tot[0]
    tot = 0 if tot is None else int(tot)
    if tot >= 15:
        response.status_code = 503
        return {"error": ml.tr(request, "maximum_15_active_challenge", force_lang = au["language"])}

    data = await request.json()
    try:
        title = convert_quotation(data["title"])
        description = compress(data["description"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        start_time = int(data["start_time"])
        end_time = int(data["end_time"])
        challenge_type = int(data["challenge_type"])
        delivery_count = int(data["delivery_count"])
        if delivery_count > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "delivery_count", "limit": "2,147,483,647"}, force_lang = au["language"])}
        required_roles = data["required_roles"]
        required_distance = int(data["required_distance"])
        reward_points = int(data["reward_points"])
        if reward_points > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "reward_points", "limit": "2,147,483,647"}, force_lang = au["language"])}
        public_details = 0
        if data["public_details"] == "true":
            public_details = 1
        job_requirements = data["job_requirements"]
        if type(required_roles) != list or type(job_requirements) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    if start_time >= end_time:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_time_range", force_lang = au["language"])}

    if not challenge_type in [1, 2, 3, 4, 5]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_challenge_type", force_lang = au["language"])}
    
    roles = required_roles
    rolereq = []
    for role in roles:
        if role == "":
            continue
        try:
            rolereq.append(str(int(role)))
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_required_roles", force_lang = au["language"])}
    rolereq = rolereq[:20]
    required_roles = "," + ",".join(rolereq) + ","

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

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtchallengeid' FOR UPDATE")
    t = await aiosql.fetchall(dhrid)
    nxtchallengeid = int(t[0][0])
    await aiosql.execute(dhrid, f"UPDATE settings SET sval = {nxtchallengeid+1} WHERE skey = 'nxtchallengeid'")
    await aiosql.execute(dhrid, f"INSERT INTO challenge VALUES ({nxtchallengeid}, {adminid}, '{title}', '{description}', \
                {start_time}, {end_time}, {challenge_type}, \
                {delivery_count}, '{required_roles}', {required_distance}, {reward_points}, {public_details}, '{jobreq}')")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Created challenge `#{nxtchallengeid}`")

    return {"challengeid": nxtchallengeid}

# PATCH /challenge
# REQUEST PARAM
# - integer: challengeid
# JSON DATA
# *Same as POST /challenge
@app.patch(f"/{config.abbr}/challenge/{{challengeid}}")
async def patchChallenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /challenge', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT delivery_count, challenge_type FROM challenge WHERE challengeid = {challengeid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    org_delivery_count = t[0][0]
    challenge_type = t[0][1]

    data = await request.json()
    try:
        title = convert_quotation(data["title"])
        description = compress(data["description"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        start_time = int(data["start_time"])
        end_time = int(data["end_time"])
        delivery_count = int(data["delivery_count"])
        if delivery_count > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "delivery_count", "limit": "2,147,483,647"}, force_lang = au["language"])}
        required_roles = data["required_roles"]
        required_distance = int(data["required_distance"])
        reward_points = int(data["reward_points"])
        if reward_points > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "reward_points", "limit": "2,147,483,647"}, force_lang = au["language"])}
        public_details = 0
        if data["public_details"] == "true":
            public_details = 1
        job_requirements = data["job_requirements"]
        if type(required_roles) != list or type(job_requirements) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    if start_time >= end_time:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_time_range", force_lang = au["language"])}
    
    roles = required_roles
    rolereq = []
    for role in roles:
        if role == "":
            continue
        try:
            rolereq.append(str(int(role)))
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_required_roles", force_lang = au["language"])}
    rolereq = rolereq[:20]
    required_roles = "," + ",".join(rolereq) + ","

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

    await aiosql.execute(dhrid, f"UPDATE challenge SET title = '{title}', description = '{description}', \
            start_time = '{start_time}', end_time = '{end_time}', \
            delivery_count = {delivery_count}, required_roles = '{required_roles}', \
            required_distance = {required_distance}, reward_points = {reward_points}, public_details = {public_details}, \
            job_requirements = '{jobreq}' WHERE challengeid = {challengeid}")
    await aiosql.commit(dhrid)

    if challenge_type == 1:
        original_points = {}
        await aiosql.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await aiosql.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        await aiosql.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await aiosql.commit(dhrid)
        
        if org_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {org_delivery_count} AND COUNT(*) < {delivery_count}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) > 0:
                    await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_uncompleted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        elif org_delivery_count > delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {delivery_count} AND COUNT(*) < {org_delivery_count}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) == 0:
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_completed_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        else:
            for userid in original_points.keys():
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                if original_points[userid] < reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points - original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                elif original_points[userid] > reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(- reward_points + original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 4:
        original_points = {}
        await aiosql.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await aiosql.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        await aiosql.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await aiosql.commit(dhrid)
        
        if org_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT challenge_record.userid FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid \
                HAVING SUM(dlog.distance) >= {org_delivery_count} AND SUM(dlog.distance) < {delivery_count}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) > 0:
                    await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_uncompleted_increased_distance_sum", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        elif org_delivery_count > delivery_count:
            await aiosql.execute(dhrid, f"SELECT challenge_record.userid FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid \
                HAVING SUM(dlog.distance) >= {delivery_count} AND SUM(dlog.distance) < {org_delivery_count}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]
                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) == 0:
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_completed_decreased_distance_sum", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        else:
            for userid in original_points.keys():
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                if original_points[userid] < reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points - original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                elif original_points[userid] > reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(- reward_points + original_points[userid]), "total_points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 3:
        original_points = {}
        await aiosql.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid} AND points != {reward_points}")
        t = await aiosql.fetchall(dhrid)
        for tt in t:
            original_points[tt[0]] = tt[1]
        completed_count = {}
        await aiosql.execute(dhrid, f"SELECT userid, COUNT(*) FROM challenge_completed WHERE challengeid = {challengeid} GROUP BY userid")
        t = await aiosql.fetchall(dhrid)
        for tt in t:
            completed_count[tt[0]] = tt[1]
        
        await aiosql.execute(dhrid, f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        await aiosql.commit(dhrid)
        
        if org_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]

                await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                current_delivery_count = await aiosql.fetchone(dhrid)
                current_delivery_count = current_delivery_count[0]
                current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)

                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                p = await aiosql.fetchall(dhrid)
                if current_delivery_count < len(p) * delivery_count:
                    delete_cnt = len(p) - int(current_delivery_count / delivery_count)
                    left_cnt = int(current_delivery_count / delivery_count)
                    if delete_cnt > 0:
                        await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid} ORDER BY timestamp DESC LIMIT {delete_cnt}")
                        discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                        if delete_cnt > 1:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "n_personal_recurring_challenge_uncompelted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "count": delete_cnt, "points": tseparator(p[0][0] * delete_cnt), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        else:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "one_personal_recurring_challenge_uncompelted_increased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0]), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
            
        elif org_delivery_count > delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                userid = tt[0]

                await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                current_delivery_count = await aiosql.fetchone(dhrid)
                current_delivery_count = current_delivery_count[0]
                current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)

                await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                p = await aiosql.fetchall(dhrid)
                if current_delivery_count >= (len(p)+1) * delivery_count:
                    add_cnt = int(current_delivery_count / delivery_count) - len(p)
                    left_cnt = int(current_delivery_count / delivery_count)
                    if add_cnt > 0:
                        for _ in range(add_cnt):
                            await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                        discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                        if add_cnt > 1:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "n_personal_recurring_challenge_compelted_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "count": add_cnt, "points": tseparator(reward_points * add_cnt), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        else:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "one_personal_recurring_challenge_compelted_decreased_delivery_count", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator(left_cnt * reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)

        else:
            for userid in original_points.keys():
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                if original_points[userid] < reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator((reward_points - original_points[userid]) * completed_count[userid]), "total_points": tseparator(reward_points * completed_count[userid])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                elif original_points[userid] > reward_points:
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator((- reward_points + original_points[userid]) * completed_count[userid]), "total_points": tseparator(reward_points * completed_count[userid])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 2:
        curtime = int(time.time())

        await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
        t = await aiosql.fetchall(dhrid)
        previously_completed = {}
        if len(t) != 0:
            await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await aiosql.fetchall(dhrid)
            for pp in p:
                previously_completed[pp[0]] = (pp[1], pp[2])
            await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await aiosql.commit(dhrid)

        await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == delivery_count:
            usercnt = {}
            for tt in t:
                uid = tt[0]
                if not uid in usercnt.keys():
                    usercnt[uid] = 1
                else:
                    usercnt[uid] += 1
            for uid in usercnt.keys():
                s = usercnt[uid]
                reward = round(reward_points * s / delivery_count)
                if uid in previously_completed.keys():
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {previously_completed[uid][1]})")
                    gap = reward - previously_completed[uid][0]
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    if gap > 0:
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                    elif gap < 0:
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                    del previously_completed[uid]
                else:
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        for uid in previously_completed.keys():
            reward = previously_completed[uid][0]
            discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 5:
        curtime = int(time.time())

        await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
        t = await aiosql.fetchall(dhrid)
        previously_completed = {}
        if len(t) != 0:
            await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await aiosql.fetchall(dhrid)
            for pp in p:
                previously_completed[pp[0]] = (pp[1], pp[2])
            await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await aiosql.commit(dhrid)

        current_delivery_count = 0
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
        current_delivery_count = await aiosql.fetchone(dhrid)
        current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])
        
        if current_delivery_count >= delivery_count:
            await aiosql.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                WHERE challenge_record.challengeid = {challengeid} \
                GROUP BY dlog.userid, challenge_record.userid")
            t = await aiosql.fetchall(dhrid)
            usercnt = {}
            totalcnt = 0
            for tt in t:
                totalcnt += tt[1]
                uid = tt[0]
                if not uid in usercnt.keys():
                    usercnt[uid] = tt[1] - max(totalcnt - delivery_count, 0)
                else:
                    usercnt[uid] += tt[1] - max(totalcnt - delivery_count, 0)
                if totalcnt >= delivery_count:
                    break
            for uid in usercnt.keys():
                s = usercnt[uid]
                reward = round(reward_points * s / delivery_count)
                if uid in previously_completed.keys():
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {previously_completed[uid][1]})")
                    gap = reward - previously_completed[uid][0]
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    if gap > 0:
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                    elif gap < 0:
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                    del previously_completed[uid]
                else:
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.commit(dhrid)
        for uid in previously_completed.keys():
            reward = previously_completed[uid][0]
            discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    await AuditLog(dhrid, adminid, f"Updated challenge `#{challengeid}`")

    return Response(status_code=204)

# DELETE /challenge
# REQUEST PARAM
# - integer: challengeid
@app.delete(f"/{config.abbr}/challenge/{{challengeid}}")
async def deleteChallenge(request: Request, response: Response, challengeid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /challenge', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM challenge WHERE challengeid = {challengeid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM challenge WHERE challengeid = {challengeid}")
    await aiosql.execute(dhrid, f"DELETE FROM challenge_record WHERE challengeid = {challengeid}")
    await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Deleted challenge `#{challengeid}`")

    return Response(status_code=204)

# PUT /challenge/delivery
# REQUEST PARAM
# - integer: challengeid
# - integer: logid
# => manually accept a delivery as challenge
@app.put(f"/{config.abbr}/challenge/{{challengeid}}/delivery/{{logid}}")
async def putChallengeDelivery(request: Request, response: Response, challengeid: int, logid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(dhrid, request, request.client.host, 'PUT /challenge/delivery', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    await aiosql.execute(dhrid, f"SELECT * FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "challenge_delivery_already_accepted", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid, timestamp FROM dlog WHERE logid = {logid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    userid = t[0][0]
    timestamp = t[0][1]
    await aiosql.execute(dhrid, f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {timestamp})")    
    await aiosql.commit(dhrid)
    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
    await notification(dhrid, "challenge", discordid, ml.tr(request, "delivery_added_to_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    current_delivery_count = 0
    if challenge_type in [1,3]:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif challenge_type == 2:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif challenge_type == 4:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif challenge_type == 5:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await aiosql.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    if current_delivery_count >= delivery_count:
        if challenge_type in [1, 4]:
            await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
            t = await aiosql.fetchall(dhrid)
            if len(t) == 0:
                await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                await aiosql.commit(dhrid)
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "personal_onetime_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
        
        elif challenge_type == 3:
            await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
            t = await aiosql.fetchall(dhrid)
            if current_delivery_count >= (len(t) + 1) * delivery_count:
                await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                await aiosql.commit(dhrid)
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "recurring_challenge_completed_status_added", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator((len(t)+1) * reward_points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

        elif challenge_type == 2:
            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await aiosql.fetchall(dhrid)
            if len(t) == 0:
                curtime = int(time.time())
                await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                t = await aiosql.fetchall(dhrid)
                usercnt = {}
                for tt in t:
                    uid = tt[0]
                    if not uid in usercnt.keys():
                        usercnt[uid] = 1
                    else:
                        usercnt[uid] += 1
                for uid in usercnt.keys():
                    s = usercnt[uid]
                    reward = round(reward_points * s / delivery_count)
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                await aiosql.commit(dhrid)

        elif challenge_type == 5:
            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await aiosql.fetchall(dhrid)
            if len(t) == 0:
                curtime = int(time.time())
                await aiosql.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                    INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                    WHERE challenge_record.challengeid = {challengeid} \
                    GROUP BY dlog.userid, challenge_record.userid")
                t = await aiosql.fetchall(dhrid)
                usercnt = {}
                totalcnt = 0
                for tt in t:
                    totalcnt += tt[1]
                    uid = tt[0]
                    if not uid in usercnt.keys():
                        usercnt[uid] = tt[1] - max(totalcnt - delivery_count, 0)
                    else:
                        usercnt[uid] += tt[1] - max(totalcnt - delivery_count, 0)
                    if totalcnt >= delivery_count:
                        break
                for uid in usercnt.keys():
                    s = usercnt[uid]
                    reward = round(reward_points * s / delivery_count)
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                    await notification(dhrid, "challenge", discordid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Added delivery `#{logid}` to challenge `#{challengeid}`")
    
    return Response(status_code=204)

# DELETE /challenge/delivery
# REQUEST PARAM
# - integer: challengeid
# - integer: logid
# => denies a delivery as challenge
@app.delete(f"/{config.abbr}/challenge/{{challengeid}}/delivery/{{logid}}")
async def deleteChallengeDelivery(request: Request, response: Response, challengeid: int, logid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /challenge/delivery', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_not_found", force_lang = au["language"])}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "challenge_delivery_not_found", force_lang = au["language"])}
    userid = t[0][0]
    
    await aiosql.execute(dhrid, f"DELETE FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    await aiosql.commit(dhrid)
    discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
    await notification(dhrid, "challenge", discordid, ml.tr(request, "delivery_removed_from_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    current_delivery_count = 0
    if challenge_type in [1,3]:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    elif challenge_type == 2:
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
    elif challenge_type == 4:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
    elif challenge_type == 5:
        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
            WHERE challenge_record.challengeid = {challengeid}")
    current_delivery_count = await aiosql.fetchone(dhrid)
    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

    if challenge_type in [1, 4]:
        if current_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
            p = await aiosql.fetchall(dhrid)
            if len(p) > 0:
                await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                await aiosql.commit(dhrid)
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
      
    elif challenge_type == 3:
        await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
        p = await aiosql.fetchall(dhrid)
        if current_delivery_count < len(p) * delivery_count:
            await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid} ORDER BY timestamp DESC LIMIT 1")
            await aiosql.commit(dhrid)
            discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
            if len(p) <= 1:
                await notification(dhrid, "challenge", discordid, ml.tr(request, "one_personal_recurring_challenge_uncompleted", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0])}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            elif len(p) > 1:
                await notification(dhrid, "challenge", discordid, ml.tr(request, "one_personal_recurring_challenge_uncompleted_still_have_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(p[0][0]), "total_points": tseparator(p[0][0] * (len(p) - 1))}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 2:
        if current_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await aiosql.fetchall(dhrid)
            if len(p) > 0:
                userid = p[0][0]
                points = p[0][1]
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await aiosql.commit(dhrid)
        
        else:
            curtime = int(time.time())
            
            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await aiosql.fetchall(dhrid)
            previously_completed = {}
            if len(t) != 0:
                await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                for pp in p:
                    previously_completed[pp[0]] = (pp[1], pp[2])
                await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
                await aiosql.commit(dhrid)

                await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                t = await aiosql.fetchall(dhrid)
                usercnt = {}
                for tt in t:
                    uid = tt[0]
                    if not uid in usercnt.keys():
                        usercnt[uid] = 1
                    else:
                        usercnt[uid] += 1
                for uid in usercnt.keys():
                    s = usercnt[uid]
                    reward = round(reward_points * s / delivery_count)
                    if uid in previously_completed.keys():
                        await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {previously_completed[uid][1]})")
                        gap = reward - previously_completed[uid][0]
                        discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                        if gap > 0:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        elif gap < 0:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        del previously_completed[uid]
                    else:
                        await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                        discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                await aiosql.commit(dhrid)
            for uid in previously_completed.keys():
                reward = previously_completed[uid][0]
                discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    elif challenge_type == 5:
        if current_delivery_count < delivery_count:
            await aiosql.execute(dhrid, f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
            p = await aiosql.fetchall(dhrid)
            if len(p) > 0:
                userid = p[0][0]
                points = p[0][1]
                discordid = (await GetUserInfo(dhrid, request, userid = userid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_uncompleted_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
            await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
            await aiosql.commit(dhrid)
        
        else:
            curtime = int(time.time())
            
            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = await aiosql.fetchall(dhrid)
            previously_completed = {}
            if len(t) != 0:
                await aiosql.execute(dhrid, f"SELECT userid, points, timestamp FROM challenge_completed WHERE challengeid = {challengeid}")
                p = await aiosql.fetchall(dhrid)
                for pp in p:
                    previously_completed[pp[0]] = (pp[1], pp[2])
                await aiosql.execute(dhrid, f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
                await aiosql.commit(dhrid)

                await aiosql.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                    INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                    WHERE challenge_record.challengeid = {challengeid} \
                    GROUP BY dlog.userid, challenge_record.userid")
                t = await aiosql.fetchall(dhrid)
                usercnt = {}
                totalcnt = 0
                for tt in t:
                    totalcnt += tt[1]
                    uid = tt[0]
                    if not uid in usercnt.keys():
                        usercnt[uid] = tt[1] - max(totalcnt - delivery_count, 0)
                    else:
                        usercnt[uid] += tt[1] - max(totalcnt - delivery_count, 0)
                    if totalcnt >= delivery_count:
                        break
                for uid in usercnt.keys():
                    s = usercnt[uid]
                    reward = round(reward_points * s / delivery_count)
                    if uid in previously_completed.keys():
                        await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {previously_completed[uid][1]})")
                        gap = reward - previously_completed[uid][0]
                        discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                        if gap > 0:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        elif gap < 0:
                            await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_more_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(-gap), "total_points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                        del previously_completed[uid]
                    else:
                        await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                        discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                        await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_received_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))
                await aiosql.commit(dhrid)
            for uid in previously_completed.keys():
                reward = previously_completed[uid][0]
                discordid = (await GetUserInfo(dhrid, request, userid = uid))["discordid"]
                await notification(dhrid, "challenge", discordid, ml.tr(request, "challenge_updated_lost_points", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, discordid, "en")))

    await AuditLog(dhrid, adminid, f"Removed delivery `#{logid}` from challenge `#{challengeid}`")

    return Response(status_code=204)