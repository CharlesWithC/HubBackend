# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
from discord import Webhook, Embed
from datetime import datetime
from aiohttp import ClientSession
import json, time, requests

from app import app, config
from db import newconn
from functions import *
import multilang as ml

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special"]
JOB_REQUIREMENT_TYPE = {"source_city_id": convert_quotation, "source_company_id": convert_quotation, "destination_city_id": convert_quotation, "destination_company_id": convert_quotation, "minimum_distance": int, "cargo_id": convert_quotation, "minimum_cargo_mass": int, "maximum_cargo_damage": float, "maximum_speed": int, "maximum_fuel": int, "minimum_profit": int, "maximum_profit": int, "maximum_offence": int, "allow_overspeed": int, "allow_auto_park": int, "allow_auto_load": int, "must_not_be_late": int, "must_be_special": int}
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0}

# PLANS

# Remember to add challenge points for /member/roles/rank and /dlog/leaderboard
# Remember to add "challenge_record" = challengeid[] for /dlog/list and /dlog

# For company challenge, challenge_record will still be bound to personal userid. 
# Completed company challenges are no longer allowed to be edited.

# POST /challenge
# Note: Check if there're at most 15 active challenges
# FORM DATA:
# - string: title
# - integar: start_time
# - integar: end_time
# - integar: challenge_type (1 = personal | 2 = company)
# - integar: delivery_count
# - string: required_roles (or) (separate with ',' | default = 'any')
# - integar: required_distance
# - integar: reward_points
# - boolean: public_details
# - string(json): job_requirements
#   - integar: minimum_distance
#   - string: source_city_id
#   - string: source_company_id
#   - string: destination_city_id
#   - string: destination_company_id
#   - string: cargo_id
#   - integar: minimum_cargo_mass
#   - float: maximum_cargo_damage
#   - integar: maximum_speed
#   - integar: maximum_fuel
#   - integar: minimum_profit
#   - integar: maximum_profit
#   - integar: maximum_offence
#   - boolean: allow_overspeed
#   - boolean: allow_auto_park
#   - boolean: allow_auto_load
#   - boolean: must_not_be_late
#   - boolean: must_be_special

@app.post(f"/{config.abbr}/challenge")
async def postChallenge(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /challenge', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT COUNT(*) FROM challenge WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())}")
    tot = cur.fetchone()[0]
    tot = 0 if tot is None else int(tot)
    if tot >= 15:
        response.status_code = 503
        return {"error": True, "descriptor": ml.tr(request, "maximum_15_active_challenge")}

    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        description = compress(form["description"])
        start_time = int(form["start_time"])
        end_time = int(form["end_time"])
        challenge_type = int(form["challenge_type"])
        delivery_count = int(form["delivery_count"])
        required_roles = form["required_roles"]
        required_distance = int(form["required_distance"])
        reward_points = int(form["reward_points"])
        public_details = 0
        if form["public_details"] == "true":
            public_details = 1
        job_requirements = json.loads(form["job_requirements"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    
    if start_time >= end_time:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_time_range")}

    if not challenge_type in [1, 2]:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_challenge_type")}
    
    roles = required_roles.split(",")
    rolereq = []
    for role in roles:
        if role == "":
            continue
        try:
            rolereq.append(str(int(role)))
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "invalid_required_roles")}
    rolereq = rolereq[:20]
    required_roles = "," + ",".join(rolereq) + ","

    if delivery_count <= 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_delivery_count")}

    if required_distance < 0:
        required_distance = 0

    if reward_points < 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_reward_points")}

    jobreq = []
    for req in JOB_REQUIREMENTS:
        if req in job_requirements:
            jobreq.append(JOB_REQUIREMENT_TYPE[req](job_requirements[req]))
        else:
            jobreq.append(JOB_REQUIREMENT_DEFAULT[req])
    jobreq = compress(json.dumps(jobreq, separators=(',', ':')))

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtchallengeid'")
    t = cur.fetchall()
    nxtchallengeid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {nxtchallengeid+1} WHERE skey = 'nxtchallengeid'")
    cur.execute(f"INSERT INTO challenge VALUES ({nxtchallengeid}, {adminid}, '{title}', '{description}', \
                {start_time}, {end_time}, {challenge_type}, \
                {delivery_count}, '{required_roles}', {required_distance}, {reward_points}, {public_details}, '{jobreq}')")
    conn.commit()

    await AuditLog(adminid, f"Created challenge `#{nxtchallengeid}`")

    return {"error": False, "response": {"challengeid": nxtchallengeid}}

# PATCH /challenge
# REQUEST PARAM
# - integar: challengeid
# FORM DATA
# *Same as POST /challenge
@app.patch(f"/{config.abbr}/challenge")
async def patchChallenge(request: Request, response: Response, authorization: str = Header(None), challengeid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'PATCH /challenge', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}

    cur.execute(f"SELECT delivery_count, challenge_type FROM challenge WHERE challengeid = {challengeid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}
    org_delivery_count = t[0][0]
    challenge_type = t[0][1]

    form = await request.form()
    try:
        title = convert_quotation(form["title"])
        description = compress(form["description"])
        start_time = int(form["start_time"])
        end_time = int(form["end_time"])
        delivery_count = int(form["delivery_count"])
        required_roles = form["required_roles"]
        required_distance = int(form["required_distance"])
        reward_points = int(form["reward_points"])
        public_details = 0
        if form["public_details"] == "true":
            public_details = 1
        job_requirements = json.loads(form["job_requirements"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}
    
    if start_time >= end_time:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_time_range")}
    
    if not challenge_type in [1, 2]:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_challenge_type")}
    
    roles = required_roles.split(",")
    rolereq = []
    for role in roles:
        if role == "":
            continue
        try:
            rolereq.append(str(int(role)))
        except:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "invalid_required_roles")}
    rolereq = rolereq[:20]
    required_roles = "," + ",".join(rolereq) + ","

    if delivery_count <= 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_delivery_count")}

    if required_distance < 0:
        required_distance = 0

    if reward_points < 0:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "invalid_reward_points")}

    jobreq = []
    for req in JOB_REQUIREMENTS:
        if req in job_requirements:
            jobreq.append(JOB_REQUIREMENT_TYPE[req](job_requirements[req]))
        else:
            jobreq.append(JOB_REQUIREMENT_DEFAULT[req])
    jobreq = compress(json.dumps(jobreq, separators=(',', ':')))

    cur.execute(f"UPDATE challenge SET title = '{title}', description = '{description}', \
            start_time = '{start_time}', end_time = '{end_time}', \
            delivery_count = {delivery_count}, required_roles = '{required_roles}', \
            required_distance = {required_distance}, reward_points = {reward_points}, public_details = {public_details}, \
            job_requirements = '{jobreq}' WHERE challengeid = {challengeid}")
    conn.commit()

    if challenge_type == 1:
        cur.execute(f"UPDATE challenge_completed SET points = {reward_points} WHERE challengeid = {challengeid}")
        
        if org_delivery_count < delivery_count:
            cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {org_delivery_count} AND COUNT(*) < {delivery_count}")
            t = cur.fetchall()
            for tt in t:
                userid = tt[0]
                cur.execute(f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = cur.fetchall()
                if len(p) > 0:
                    cur.execute(f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                    discordid = getUserInfo(userid = userid)["discordid"]
                    notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) is no longer completed due to increased delivery count: You lost {p[0][0]} points.")
        elif org_delivery_count > delivery_count:
            cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} \
                GROUP BY userid HAVING COUNT(*) >= {org_delivery_count} AND COUNT(*) < {delivery_count}")
            t = cur.fetchall()
            for tt in t:
                userid = tt[0]
                cur.execute(f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                p = cur.fetchall()
                if len(p) == 0:
                    cur.execute(f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                    discordid = getUserInfo(userid = userid)["discordid"]
                    notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received {reward_points} points.")
        conn.commit()

    elif challenge_type == 2:
        curtime = 0
        cur.execute(f"SELECT timestamp FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
        t = cur.fetchall()
        previously_completed = {}
        if len(t) != 0:
            curtime = t[0][0]
            cur.execute(f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
            p = cur.fetchall()
            for pp in p:
                previously_completed[pp[0]] = pp[1]
            cur.execute(f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
        else:
            curtime = int(time.time())
        cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp LIMIT {delivery_count}")
        t = cur.fetchall()
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
                cur.execute(f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                if uid in previously_completed.keys():
                    gap = reward - previously_completed[uid]
                    discordid = getUserInfo(userid = uid)["discordid"]
                    if gap > 0:
                        notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You received `{gap}` more points. You got {reward} points from the challenge.")
                    elif gap < 0:
                        notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost `{-gap}` points. You got {reward} points from the challenge.")
                    del previously_completed[uid]
            conn.commit()
        for uid in previously_completed.keys():
            reward = previously_completed[uid]
            discordid = getUserInfo(userid = uid)["discordid"]
            notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost {reward} points.")

    await AuditLog(adminid, f"Updated challenge `#{challengeid}`")

    return {"error": False}

# DELETE /challenge
# REQUEST PARAM
# - integar: challengeid
@app.delete(f"/{config.abbr}/challenge")
async def deleteChallenge(request: Request, response: Response, authorization: str = Header(None), challengeid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'DELETE /challenge', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}

    cur.execute(f"SELECT * FROM challenge WHERE challengeid = {challengeid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}
    
    cur.execute(f"DELETE FROM challenge WHERE challengeid = {challengeid}")
    cur.execute(f"DELETE FROM challenge_record WHERE challengeid = {challengeid}")
    cur.execute(f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")
    conn.commit()

    await AuditLog(adminid, f"Deleted challenge `#{challengeid}`")

    return {"error": False}

# PUT /challenge/delivery
# REQUEST PARAM
# - integar: challengeid
# - integar: logid
# => manually accept a delivery as challenge
@app.put(f"/{config.abbr}/challenge/delivery")
async def putChallengeDelivery(request: Request, response: Response, authorization: str = Header(None), challengeid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'PUT /challenge/delivery', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    form = await request.form()
    try:
        logid = int(form["logid"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": "Form field missing or data cannot be parsed"}

    conn = newconn()
    cur = conn.cursor()

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}

    cur.execute(f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    cur.execute(f"SELECT * FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = cur.fetchall()
    if len(t) != 0:
        response.status_code = 409
        return {"error": True, "descriptor": ml.tr(request, "challenge_delivery_already_accepted")}
    
    cur.execute(f"SELECT userid, timestamp FROM dlog WHERE logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "delivery_log_not_found")}
    userid = t[0][0]
    timestamp = t[0][1]
    cur.execute(f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {timestamp})")    
    conn.commit()
    discordid = getUserInfo(userid = userid)["discordid"]
    notification(discordid, f"Delivery `#{logid}` added to challenge `{title}` (Challenge ID: `{challengeid}`)")

    current_delivery_count = 0
    if challenge_type == 1:
        cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
        current_delivery_count = cur.fetchone()[0]
        current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
    elif challenge_type == 2:
        cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
        current_delivery_count = cur.fetchone()[0]
        current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
    
    if current_delivery_count >= delivery_count:
        if challenge_type == 1:
            cur.execute(f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
            t = cur.fetchall()
            if len(t) == 0:
                cur.execute(f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                conn.commit()
                discordid = getUserInfo(userid = userid)["discordid"]
                notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{tseparator(reward_points)}` points.")
        elif challenge_type == 2:
            cur.execute(f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
            t = cur.fetchall()
            if len(t) == 0:
                curtime = int(time.time())
                cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp LIMIT {delivery_count}")
                t = cur.fetchall()
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
                    cur.execute(f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    discordid = getUserInfo(userid = uid)["discordid"]
                    notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{tseparator(reward)}` points.")
                conn.commit()

    await AuditLog(adminid, f"Added delivery `#{logid}` to challenge `#{challengeid}`")
    
    return {"error": False}

# DELETE /challenge/delivery
# REQUEST PARAM
# - integar: challengeid
# - integar: logid
# => denies a delivery as challenge
@app.delete(f"/{config.abbr}/challenge/delivery")
async def deleteChallengeDelivery(request: Request, response: Response, authorization: str = Header(None), \
        challengeid: Optional[int] = -1, logid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'DELETE /challenge/delivery', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}

    cur.execute(f"SELECT delivery_count, challenge_type, reward_points, title FROM challenge WHERE challengeid = {challengeid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}
    delivery_count = t[0][0]
    challenge_type = t[0][1]
    reward_points = t[0][2]
    title = t[0][3]

    cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_delivery_not_found")}
    userid = t[0][0]
    
    cur.execute(f"DELETE FROM challenge_record WHERE challengeid = {challengeid} AND logid = {logid}")
    conn.commit()
    discordid = getUserInfo(userid = userid)["discordid"]
    notification(discordid, f"Delivery `#{logid}` removed from challenge `{title}` (Challenge ID: `{challengeid}`)")

    cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
    current_delivery_count = cur.fetchone()[0]
    current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
    if current_delivery_count < delivery_count:
        if challenge_type == 1:
            cur.execute(f"SELECT points FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
            p = cur.fetchall()
            if len(p) > 0:
                cur.execute(f"DELETE FROM challenge_completed WHERE userid = {userid} AND challengeid = {challengeid}")
                discordid = getUserInfo(userid = userid)["discordid"]
                notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) is no longer completed due to increased delivery count: You lost {p[0][0]} points.")
            
        elif challenge_type == 2:
            curtime = 0
            cur.execute(f"SELECT timestamp FROM challenge_completed WHERE challengeid = {challengeid} LIMIT 1")
            t = cur.fetchall()
            previously_completed = {}
            if len(t) != 0:
                curtime = t[0][0]
                cur.execute(f"SELECT userid, points FROM challenge_completed WHERE challengeid = {challengeid}")
                p = cur.fetchall()
                for pp in p:
                    previously_completed[pp[0]] = pp[1]
                cur.execute(f"DELETE FROM challenge_completed WHERE challengeid = {challengeid}")

                cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp LIMIT {delivery_count}")
                t = cur.fetchall()
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
                    cur.execute(f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                    if uid in previously_completed.keys():
                        gap = reward - previously_completed[uid]
                        discordid = getUserInfo(userid = uid)["discordid"]
                        if gap > 0:
                            notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You received `{gap}` more points. You got {reward} points from the challenge.")
                        elif gap < 0:
                            notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost `{-gap}` points. You got {reward} points from the challenge.")
                        del previously_completed[uid]
                conn.commit()
            for uid in previously_completed.keys():
                reward = previously_completed[uid]
                discordid = getUserInfo(userid = uid)["discordid"]
                notification(discordid, f"Challenge `{title}` (Challenge ID: `{challengeid}`) updated: You lost {reward} points.")

    await AuditLog(adminid, f"Removed delivery `#{logid}` from challenge `#{challengeid}`")

    return {"error": False}

# GET /challenge/list
# REQUEST PARAM
# - string: title (search)
# - integar: start_time
# - integar: end_time
# - integar: challenge_type
# - integar: required_role
# - integar: minimum_required_distance
# - integar: maximum_required_distance
# - integar: userid - to show challenges that user participated
# - boolean: must_have_completed (if userid is specified, show challenges that user completed, including completed company challenge)
#                       otherwise show all completed challenges
# - string: order (asc / desc)
# - string: order_by (start_time / end_time / title / required_distance / reward_points / delivery_count)
# - integar: page
# - integar: page_size (max = 100)
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

    rl = ratelimit(request.client.host, 'GET /challenge/list', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    activityUpdate(au["discordid"], f"Viewing Challenges")
    
    if page <= 0:
        page = 1
    if page_size <= 0:
        page_size = 1
    elif page_size >= 100:
        page_size = 100
    
    query_limit = "WHERE challengeid >= 0 "

    if title != "":
        title = convert_quotation(title).lower()
        query_limit += f"AND LOWER(title) LIKE '%{title}%' "

    if start_time != -1 and end_time != -1:
        query_limit += f"AND start_time >= {start_time} AND end_time <= {end_time} "
    else:
        query_limit += f"AND end_time >= {end_time - 86400} "
    
    if challenge_type in [1,2]:
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
    
    if must_have_completed:
        query_limit += f"AND challengeid IN (SELECT challengeid FROM challenge_completed) "
    
    # start_time / end_time / title / required_distance / reward_points / delivery_count
    if not order_by in ["challengeid", "title", "start_time", "end_time", "required_distance", "reward_points", "delivery_count"]:
        order_by = "reward_points"
        order = "desc"
    
    if not order.lower() in ["asc", "desc"]:
        order = "asc"
    
    query_limit += f"ORDER BY {order_by} {order.upper()}"

    ret = []

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, \
            required_distance, reward_points, description FROM challenge {query_limit} LIMIT {(page - 1) * page_size}, {page_size}")
    t = cur.fetchall()
    for tt in t:
        current_delivery_count = 0
        if tt[4] == 1:
            cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]} AND userid = {userid}")
            current_delivery_count = cur.fetchone()[0]
            current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
        elif tt[4] == 2:
            cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {tt[0]}")
            current_delivery_count = cur.fetchone()[0]
            current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)

        ret.append({"challengeid": str(tt[0]), "title": tt[1], "description": decompress(tt[9]), \
                "start_time": str(tt[2]), "end_time": str(tt[3]),\
                "challenge_type": str(tt[4]), "delivery_count": str(tt[5]), "current_delivery_count": str(current_delivery_count), \
                "required_roles": tt[6].split(",")[1:-1], "required_distance": str(tt[7]), "reward_points": str(tt[8])})
    
    cur.execute(f"SELECT COUNT(*) FROM challenge {query_limit}")
    t = cur.fetchall()
    
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}
    
# GET /challenge
# REQUEST PARAM
# - integar: challengeid
# returns requirement if public_details = true and user is not staff
#                     or if public_details = false
@app.get(f"/{config.abbr}/challenge")
async def getChallenge(request: Request, response: Response, authorization: str = Header(None), \
        challengeid: Optional[int] = -1, userid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'GET /challenge', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    if userid == -1:
        userid = au["userid"]
    isstaff = False
    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "challenge"])
    if not au["error"]:
        isstaff = True

    if int(challengeid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT challengeid, title, start_time, end_time, challenge_type, delivery_count, required_roles, \
            required_distance, reward_points, public_details, job_requirements, description FROM challenge WHERE challengeid = {challengeid} \
                AND challengeid >= 0")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "challenge_not_found")}
    tt = t[0]
    public_details = tt[9]
    jobreq = "private"
    if public_details or isstaff:
        p = json.loads(decompress(tt[10]))
        jobreq = {}
        for i in range(0,len(p)):
            jobreq[JOB_REQUIREMENTS[i]] = str(p[i])

    current_delivery_count = 0
    if tt[4] == 1:
        cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
        current_delivery_count = cur.fetchone()[0]
        current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
    elif tt[4] == 2:
        cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
        current_delivery_count = cur.fetchone()[0]
        current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
            
    return {"error": False, "response": {"challengeid": str(tt[0]), "title": tt[1], "description": decompress(tt[11]), \
            "start_time": str(tt[2]), "end_time": str(tt[3]), \
            "challenge_type": str(tt[4]), "delivery_count": str(tt[5]), "current_delivery_count": str(current_delivery_count), \
            "required_roles": tt[6].split(",")[1:-1], "required_distance": str(tt[7]), "reward_points": str(tt[8]), \
            "job_requirements": jobreq}}