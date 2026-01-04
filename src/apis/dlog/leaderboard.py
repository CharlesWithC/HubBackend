# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

from functions import *

async def get_leaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        after_userid: Optional[int] = None, after: Optional[int] = None, before: Optional[int] = None, \
        min_point: Optional[int] = None, max_point: Optional[int] = None, \
        speed_limit: Optional[int] = None, game: Optional[int] = None, \
        point_types: Optional[str] = "distance,challenge,event,division,bonus", userids: Optional[str] = ""):
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'GET /dlog/leaderboard', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, extra_time = 10, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(request, au["uid"], "leaderboard")

    if after is None:
        after = 0
    if before is None:
        before = int(time.time())

    limittype = point_types
    limituser = userids

    usecache = False
    nlusecache = False
    cachetime = None
    nlcachetime = None

    userdistance = {}
    userchallenge = {}
    userevent = {}
    userdivision = {}
    userbonus = {}

    nluserdistance = {}
    nluserchallenge = {}
    nluserevent = {}
    nluserdivision = {}
    nluserbonus = {}
    nlusertot = {}
    nlusertot_id = []
    nlrank = 1
    nluserrank = {}

    # get regular leaderboard cache
    idl = app.redis.zrangebyscore("lb:after", after - 60, after + 60)
    idr = app.redis.zrangebyscore("lb:before", before - 60, before + 60)
    ids = list(set(idl) & set(idr))
    for idx in ids:
        ret = app.redis.hgetall(f"lb:{idx}:{speed_limit}:{game}")
        if ret:
            # app.redis.expire(f"lb:{idx}:{speed_limit}:{game}", 60)
            t = deflatten_dict(ret, intify = True)
            usecache = True
            cachetime = t["cache"]
            userdistance = t["d"]
            userchallenge = t["c"]
            userevent = t["e"]
            userdivision = t["di"]
            userbonus = t["b"]
            break

    # clear regular leaderboard cache
    keys = app.redis.keys("lb:*:*")
    ids = [x.split(":")[2] for x in keys] # the first part is {abbr}, second part is "lb", third part is {dhrid}
    # delete data in lb:after/before whose key is not in ids
    with app.redis.pipeline() as pipe:
        for idx in app.redis.zrange("lb:after", 0, -1):
            if idx not in ids:
                pipe.zrem(f"{app.config.abbr}:lb:after", idx)
                pipe.zrem(f"{app.config.abbr}:lb:before", idx)
        pipe.execute()

    # get nolimit leaderboard cache
    nlb = app.redis.hgetall("nlb") # if it expired this will return None
    if nlb:
        t = deflatten_dict(nlb, intify = True)
        nlusecache = True
        nlcachetime = t["cache"]
        nlusertot = t["ut"]
        nlusertot_id = list(nlusertot.keys())[::-1]
        nlrank = t["r"]
        nluserrank = t["ur"]

    # no need to delay since cache is updated directly (not ever deleted)
    allusers = app.redis.get("alluserids")
    if not allusers:
        allusers = []
        await app.db.execute(dhrid, "SELECT userid, roles FROM user WHERE userid >= 0")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            roles = str2list(tt[1])
            ok = False
            for i in roles:
                if int(i) in app.config.perms.driver:
                    ok = True
            if not ok:
                continue
            allusers.append(tt[0])
        app.redis.set("alluserids", list2str(allusers))
        app.redis.expire("alluserids", 300)
    else:
        allusers = str2list(allusers)

    ratio = 1
    if app.config.distance_unit == "imperial":
        ratio = 0.621371

    # validate parameter
    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    # set limits
    limituser = str2list(limituser)
    if len(limituser) > 100:
        limituser = limituser[:100]
    limit = ""
    if speed_limit is not None:
        limit = f" AND topspeed <= {speed_limit}"
    gamelimit = ""
    if game == 1 or game == 2:
        gamelimit = f" AND unit = {game}"

    if not usecache:
        ##### WITH LIMIT (Parameter)
        # calculate distance
        await app.db.execute(dhrid, f"SELECT userid, SUM(distance) FROM dlog WHERE userid >= 0 AND timestamp >= {after} AND timestamp <= {before} {limit} {gamelimit} GROUP BY userid")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if tt[0] not in allusers:
                continue
            if tt[0] not in userdistance.keys():
                userdistance[tt[0]] = tt[1]
            else:
                userdistance[tt[0]] += tt[1]
            userdistance[tt[0]] = int(userdistance[tt[0]])

        # calculate challenge
        await app.db.execute(dhrid, f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid >= 0 AND timestamp >= {after} AND timestamp <= {before} GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in userchallenge.keys():
                userchallenge[oo[0]] = 0
            userchallenge[oo[0]] += int(oo[1])

        # calculate event
        await app.db.execute(dhrid, f"SELECT attendee, points FROM event WHERE departure_timestamp >= {after} AND departure_timestamp <= {before}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            attendees = str2list(tt[0])
            for attendee in attendees:
                if attendee not in allusers:
                    continue
                if attendee not in userevent.keys():
                    userevent[attendee] = int(tt[1])
                else:
                    userevent[attendee] += int(tt[1])

        # calculate division
        await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE userid >= 0 AND logid >= 0 AND timestamp >= {after} AND timestamp <= {before} ORDER BY logid ASC LIMIT 1")
        t = await app.db.fetchall(dhrid)
        firstlogid = -1
        if len(t) > 0:
            firstlogid = t[0][0]

        await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE userid >= 0 AND logid >= 0 AND timestamp >= {after} AND timestamp <= {before} ORDER BY logid DESC LIMIT 1")
        t = await app.db.fetchall(dhrid)
        lastlogid = -1
        if len(t) > 0:
            lastlogid = t[0][0]

        await app.db.execute(dhrid, f"SELECT userid, divisionid, COUNT(distance), SUM(distance) \
            FROM division \
            WHERE status = 1 AND logid >= 0 AND userid >= 0 AND logid >= {firstlogid} AND logid <= {lastlogid} \
            GROUP BY userid, divisionid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in userdivision.keys():
                userdivision[oo[0]] = 0
            if oo[1] in app.division_points.keys():
                if app.division_points[oo[1]]["mode"] == "static":
                    userdivision[oo[0]] += float(oo[2]) * app.division_points[oo[1]]["value"]
                elif app.division_points[oo[1]]["mode"] == "ratio":
                    userdivision[oo[0]] += float(oo[3]) * app.division_points[oo[1]]["value"]
        for (key, item) in userdivision.items():
            userdivision[key] = int(item)

        # calculate bonus
        await app.db.execute(dhrid, f"SELECT userid, SUM(point) FROM bonus_point WHERE userid >= 0 AND timestamp >= {after} AND timestamp <= {before} GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in userbonus.keys():
                userbonus[oo[0]] = 0
            userbonus[oo[0]] += int(oo[1])

    # calculate total point
    limittype = limittype.split(",")
    usertot = {}
    for k in userdistance.keys():
        if "distance" in limittype:
            usertot[k] = round(userdistance[k] * ratio)
    for k in userchallenge.keys():
        if k not in usertot.keys():
            usertot[k] = 0
        if "challenge" in limittype:
            usertot[k] += userchallenge[k]
    for k in userevent.keys():
        if k not in usertot.keys():
            usertot[k] = 0
        if "event" in limittype:
            usertot[k] += userevent[k]
    for k in userdivision.keys():
        if k not in usertot.keys():
            usertot[k] = 0
        if "division" in limittype:
            usertot[k] += userdivision[k]
    for k in userbonus.keys():
        if k not in usertot.keys():
            usertot[k] = 0
        if "bonus" in limittype:
            usertot[k] += userbonus[k]

    usertot = dict(sorted(usertot.items(),key=lambda x: (x[1], x[0])))
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
        if userid not in userrank.keys():
            userrank[userid] = rank
            usertot[userid] = 0

    if not nlusecache:
        ##### WITHOUT LIMIT
        # calculate distance
        await app.db.execute(dhrid, "SELECT userid, SUM(distance) FROM dlog WHERE userid >= 0 GROUP BY userid")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            if tt[0] not in allusers:
                continue
            if tt[0] not in nluserdistance.keys():
                nluserdistance[tt[0]] = tt[1]
            else:
                nluserdistance[tt[0]] += tt[1]
            nluserdistance[tt[0]] = int(nluserdistance[tt[0]])

        # calculate challenge
        await app.db.execute(dhrid, "SELECT userid, SUM(points) FROM challenge_completed WHERE userid >= 0 GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in nluserchallenge.keys():
                nluserchallenge[oo[0]] = 0
            nluserchallenge[oo[0]] += int(oo[1])

        # calculate event
        await app.db.execute(dhrid, "SELECT attendee, points FROM event")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            attendees = str2list(tt[0])
            for attendee in attendees:
                if attendee not in allusers:
                    continue
                if attendee not in nluserevent.keys():
                    nluserevent[attendee] = tt[1]
                else:
                    nluserevent[attendee] += int(tt[1])

        # calculate division
        await app.db.execute(dhrid, "SELECT userid, divisionid, COUNT(distance), SUM(distance) \
            FROM division \
            WHERE status = 1 AND logid >= 0 AND userid >= 0 \
            GROUP BY userid, divisionid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in nluserdivision.keys():
                nluserdivision[oo[0]] = 0
            if oo[1] in app.division_points.keys():
                if app.division_points[oo[1]]["mode"] == "static":
                    nluserdivision[oo[0]] += float(oo[2]) * app.division_points[oo[1]]["value"]
                elif app.division_points[oo[1]]["mode"] == "ratio":
                    nluserdivision[oo[0]] += float(oo[3]) * app.division_points[oo[1]]["value"]
        for (key, item) in nluserdivision.items():
            nluserdivision[key] = int(item)

        # calculate bonus
        await app.db.execute(dhrid, "SELECT userid, SUM(point) FROM bonus_point WHERE userid >= 0 GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in nluserbonus.keys():
                nluserbonus[oo[0]] = 0
            nluserbonus[oo[0]] += int(oo[1])

        # calculate total point
        for k in nluserdistance.keys():
            nlusertot[k] = round(nluserdistance[k] * ratio)
        for k in nluserchallenge.keys():
            if k not in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserchallenge[k]
        for k in nluserevent.keys():
            if k not in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserevent[k]
        for k in nluserdivision.keys():
            if k not in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserdivision[k]
        for k in nluserbonus.keys():
            if k not in nlusertot.keys():
                nlusertot[k] = 0
            nlusertot[k] += nluserbonus[k]

        nlusertot = dict(sorted(nlusertot.items(),key=lambda x: (x[1], x[0])))
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
            if userid not in nluserrank.keys():
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
        if userid not in allusers:
            continue

        withpoint.append(userid)

        distance = 0
        challengepnt = 0
        eventpnt = 0
        divisionpnt = 0
        bonuspnt = 0
        if userid in userdistance.keys():
            distance = userdistance[userid]
        if userid in userchallenge.keys():
            challengepnt = userchallenge[userid]
        if userid in userevent.keys():
            eventpnt = userevent[userid]
        if userid in userdivision.keys():
            divisionpnt = userdivision[userid]
        if userid in userbonus.keys():
            bonuspnt = userbonus[userid]

        if userid in limituser or len(limituser) == 0:
            ret.append({"user": {"userid": userid}, \
                "points": {"distance": distance, "challenge": challengepnt, "event": eventpnt, \
                    "division": divisionpnt, "bonus": bonuspnt, "total": usertot[userid], \
                    "rank": userrank[userid], "total_no_limit": nlusertot[userid], "rank_no_limit": nluserrank[userid]}})

    # drivers with points (WITHOUT LIMIT)
    for userid in nlusertot_id:
        if userid in withpoint:
            continue

        # check if have driver role
        if userid not in allusers:
            continue

        withpoint.append(userid)

        if userid in limituser or len(limituser) == 0:
            ret.append({"user": {"userid": userid}, \
                "points": {"distance": 0, "challenge": 0, "event": 0, "division": 0, "bonus": 0, "total": 0, \
                "rank": rank, "total_no_limit": nlusertot[userid], "rank_no_limit": nluserrank[userid]}})

    # drivers without ponts (EVEN WITHOUT LIMIT)
    for userid in allusers:
        if userid in withpoint:
            continue

        if userid in limituser or len(limituser) == 0:
            ret.append({"user": {"userid": userid},
                "points": {"distance": 0, "challenge": 0, "event": 0, "division": 0, "bonus": 0, "total": 0, \
                    "rank": rank, "total_no_limit": 0, "rank_no_limit": nlrank}})

    if not usecache:
        app.redis.hset(f"lb:{dhrid}:{speed_limit}:{game}", mapping = flatten_dict({
            "cache": int(time.time()), "d": userdistance, "c": userchallenge, "e": userevent, \
            "di": userdivision, "b": userbonus}))
        app.redis.expire(f"lb:{dhrid}:{speed_limit}:{game}", 60)
        app.redis.zadd("lb:after", {dhrid: after})
        app.redis.zadd("lb:before", {dhrid: before})

    if not nlusecache:
        app.redis.hset("nlb", mapping = flatten_dict({"cache": int(time.time()), \
            "ut": nlusertot, "r": nlrank, "ur": nluserrank}))
        app.redis.expire("nlb", 60)

    if max(page-1, 0) * page_size >= len(ret):
        return {"list": [], "total_items": len(ret), \
            "total_pages": int(math.ceil(len(ret) / page_size)), \
                "cache": cachetime, "cache_no_limit": nlcachetime}

    if after_userid is not None:
        while len(ret) > 0 and ret[0]["user"]["userid"] != after_userid:
            ret = ret[1:]

    if max_point is not None:
        while len(ret) > 0 and ret[0]["points"]["total"] > max_point:
            ret = ret[1:]

    if min_point is not None:
        while len(ret) > 0 and ret[-1]["points"]["total"] < min_point:
            ret = ret[:-1]

    selected_ret = ret[max(page-1, 0) * page_size : page * page_size]
    for data in selected_ret:
        data["user"] = await GetUserInfo(request, userid = data["user"]["userid"])

    return {"list": selected_ret, \
        "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size)), \
            "cache": cachetime, "cache_no_limit": nlcachetime}
