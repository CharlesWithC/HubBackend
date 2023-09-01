# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

from functions import *

# app.state.cache_leaderboard = {}
# app.state.cache_nleaderboard = {}
# app.state.cache_all_users = []
# app.state.cache_all_users_ts = 0

async def get_leaderboard(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        after_userid: Optional[int] = None, after: Optional[int] = None, before: Optional[int] = None, \
        min_point: Optional[int] = None, max_point: Optional[int] = None, \
        speed_limit: Optional[int] = None, game: Optional[int] = None, \
        point_types: Optional[str] = "distance,challenge,event,division,bonus", userids: Optional[str] = ""):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, extra_time = 3)

    rl = await ratelimit(request, 'GET /dlog/leaderboard', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(request, au["uid"], "leaderboard")

    if after is None:
        after = 0
    if before is None:
        before = max(int(time.time()), 32503651200)

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

    # cache
    for ll in list(app.state.cache_leaderboard.keys()):
        if ll < int(time.time()) - 120:
            del app.state.cache_leaderboard[ll]
        else:
            tt = app.state.cache_leaderboard[ll]
            for t in tt:
                if abs(t["after"] - after) <= 120 and abs(t["before"] - before) <= 120 and \
                        t["speed_limit"] == speed_limit and t["game"] == game:
                    usecache = True
                    cachetime = ll
                    userdistance = t["userdistance"]
                    userchallenge = t["userchallenge"]
                    userevent = t["userevent"]
                    userdivision = t["userdivision"]
                    userbonus = t["userbonus"]
                    break

    for ll in list(app.state.cache_nleaderboard.keys()):
        if ll < int(time.time()) - 120:
            del app.state.cache_nleaderboard[ll]
        else:
            t = app.state.cache_nleaderboard[ll]
            nlusecache = True
            nlcachetime = ll
            nluserdistance = t["nluserdistance"]
            nluserchallenge = t["nluserchallenge"]
            nluserevent = t["nluserevent"]
            nluserdivision = t["nluserdivision"]
            nluserbonus = t["nluserbonus"]
            nlusertot = t["nlusertot"]
            nlusertot_id = list(nlusertot.keys())[::-1]
            nlrank = t["nlrank"]
            nluserrank = t["nluserrank"]

    if int(time.time()) - app.state.cache_all_users_ts <= 300:
        allusers = app.state.cache_all_users
    else:
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
        app.state.cache_all_users = allusers
        app.state.cache_all_users_ts = int(time.time())

    ratio = 1
    if app.config.distance_unit == "imperial":
        ratio = 0.621371

    # validate parameter
    page = max(page, 1)
    page_size = max(min(page_size, 250), 1)

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
            userchallenge[oo[0]] += oo[1]

        # calculate event
        await app.db.execute(dhrid, f"SELECT attendee, points FROM event WHERE departure_timestamp >= {after} AND departure_timestamp <= {before}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            attendees = str2list(tt[0])
            for attendee in attendees:
                if attendee not in allusers:
                    continue
                if attendee not in userevent.keys():
                    userevent[attendee] = tt[1]
                else:
                    userevent[attendee] += tt[1]

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

        await app.db.execute(dhrid, f"SELECT dlog.userid, division.divisionid, COUNT(dlog.distance), SUM(dlog.distance) \
            FROM dlog \
            INNER JOIN division ON dlog.logid = division.logid AND division.status = 1 \
            WHERE dlog.logid >= {firstlogid} AND dlog.logid <= {lastlogid} AND dlog.logid >= 0 AND dlog.userid >= 0 \
            GROUP BY dlog.userid, division.divisionid")
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in userdivision.keys():
                userdivision[oo[0]] = 0
            if oo[1] in app.division_points.keys():
                if app.division_points[oo[1]]["mode"] == "static":
                    userdivision[oo[0]] += oo[2] * app.division_points[oo[1]]["value"]
                elif app.division_points[oo[1]]["mode"] == "ratio":
                    userdivision[oo[0]] += oo[3] * app.division_points[oo[1]]["value"]

        # calculate bonus
        await app.db.execute(dhrid, f"SELECT userid, SUM(point) FROM bonus_point WHERE userid >= 0 AND timestamp >= {after} AND timestamp <= {before} GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in userbonus.keys():
                userbonus[oo[0]] = 0
            userbonus[oo[0]] += oo[1]

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
            nluserchallenge[oo[0]] += oo[1]

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
                    nluserevent[attendee] += tt[1]

        # calculate division
        await app.db.execute(dhrid, "SELECT dlog.userid, division.divisionid, COUNT(dlog.distance), SUM(dlog.distance) \
            FROM dlog \
            INNER JOIN division ON dlog.logid = division.logid AND division.status = 1 \
            WHERE dlog.logid >= 0 AND dlog.userid >= 0 \
            GROUP BY dlog.userid, division.divisionid")
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in nluserdivision.keys():
                nluserdivision[oo[0]] = 0
            if oo[1] in app.division_points.keys():
                if app.division_points[oo[1]]["mode"] == "static":
                    nluserdivision[oo[0]] += oo[2] * app.division_points[oo[1]]["value"]
                elif app.division_points[oo[1]]["mode"] == "ratio":
                    nluserdivision[oo[0]] += oo[3] * app.division_points[oo[1]]["value"]

        # calculate bonus
        await app.db.execute(dhrid, "SELECT userid, SUM(point) FROM bonus_point WHERE userid >= 0 GROUP BY userid")
        o = await app.db.fetchall(dhrid)
        for oo in o:
            if oo[0] not in allusers:
                continue
            if oo[0] not in nluserbonus.keys():
                nluserbonus[oo[0]] = 0
            nluserbonus[oo[0]] += oo[1]

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
            ret.append({"user": await GetUserInfo(request, userid = userid), \
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
            ret.append({"user": await GetUserInfo(request, userid = userid), \
                "points": {"distance": 0, "challenge": 0, "event": 0, "division": 0, "bonus": 0, "total": 0, \
                "rank": rank, "total_no_limit": nlusertot[userid], "rank_no_limit": nluserrank[userid]}})

    # drivers without ponts (EVEN WITHOUT LIMIT)
    for userid in allusers:
        if userid in withpoint:
            continue

        if userid in limituser or len(limituser) == 0:
            ret.append({"user": await GetUserInfo(request, userid = userid),
                "points": {"distance": 0, "challenge": 0, "event": 0, "division": 0, "bonus": 0, "total": 0, \
                    "rank": rank, "total_no_limit": 0, "rank_no_limit": nlrank}})

    if not usecache:
        ts = int(time.time())
        if ts not in app.state.cache_leaderboard.keys():
            app.state.cache_leaderboard[ts] = []
        app.state.cache_leaderboard[ts].append({"after": after, "before": before, "speed_limit": speed_limit, "game": game,\
            "userdistance": userdistance, "userchallenge": userchallenge, "userevent": userevent, \
            "userdivision": userdivision, "userbonus": userbonus})

    if not nlusecache:
        ts = int(time.time())
        app.state.cache_nleaderboard[ts]={"nluserdistance": nluserdistance, "nluserchallenge": nluserchallenge, \
            "nluserevent": nluserevent, "nluserdivision": nluserdivision, "nluserbonus": nluserbonus, \
            "nlusertot": nlusertot, "nlrank": nlrank, "nluserrank": nluserrank}

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

    return {"list": ret[max(page-1, 0) * page_size : page * page_size], \
        "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size)), \
            "cache": cachetime, "cache_no_limit": nlcachetime}
