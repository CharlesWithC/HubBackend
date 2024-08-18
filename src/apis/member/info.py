# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import os
import time
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse

import multilang as ml
from functions import *


async def get_roles(request: Request):
    app = request.app
    return app.config.roles

async def get_ranks(request: Request):
    app = request.app
    return app.config.rank_types

async def get_perms(request: Request):
    app = request.app
    return app.config.perms

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        after_userid: Optional[int] = None, \
        joined_after: Optional[int] = None, joined_before: Optional[int] = None, \
        name: Optional[str] = '', include_roles: Optional[str] = '', exclude_roles: Optional[str] = '', \
        last_seen_after: Optional[int] = None, last_seen_before: Optional[int] = None, \
        order_by: Optional[str] = "highest_role", order: Optional[str] = "desc"):
    """Returns a list of members"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /member/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if app.config.privacy and au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    elif not au["error"]:
        await ActivityUpdate(request, au["uid"], "members")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    include_roles = deduplicate(str2list(include_roles))
    if len(include_roles) > 100:
        include_roles = include_roles[:100]
    exclude_roles = deduplicate(str2list(exclude_roles))
    if len(exclude_roles) > 100:
        exclude_roles = exclude_roles[:100]

    name = convertQuotation(name).lower()

    order_by_last_seen = False
    if order_by not in ['uid', 'userid', 'name', 'discordid', 'steamid', 'truckersmpid', 'highest_role', 'join_timestamp', 'last_seen']:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    if order_by == "last_seen":
        order_by_last_seen = True
    cvt = {"userid": "userid", "name": "name", "uid": "uid", "discordid": "discordid", "steamid": "steamid", "truckersmpid": "truckersmpid", "join_timestamp": "join_timestamp", "highest_role": "highest_role", "last_seen": "userid"}
    order_by = cvt[order_by]

    sort_by_highest_role = False
    hrole_order_by = "asc"
    if order_by == "highest_role":
        sort_by_highest_role = True
        order_by = "userid"

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    if sort_by_highest_role:
        hrole_order_by = order
        if order == "ASC":
            order = "DESC"
        elif order == "DESC":
            order = "ASC"

    limit = ""
    if last_seen_after is not None:
        limit += f"AND user.uid IN (SELECT user_activity.uid FROM user_activity WHERE user_activity.timestamp >= {last_seen_after}) "
    if last_seen_before is not None:
        limit += f"AND user.uid IN (SELECT user_activity.uid FROM user_activity WHERE user_activity.timestamp <= {last_seen_before} OR user_activity.timestamp IS NULL) "

    if joined_after is not None:
        limit += f"AND user.join_timestamp >= {joined_after} "
    if joined_before is not None:
        limit += f"AND user.join_timestamp <= {joined_before} "

    hrole = {}
    if order_by_last_seen:
        await app.db.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {limit} ORDER BY user_activity.timestamp {order}, user.userid ASC")
    else:
        await app.db.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{name}%' AND user.userid >= 0 {limit} ORDER BY user.{order_by} {order}, user.userid ASC")
    t = await app.db.fetchall(dhrid)
    rret = {}
    for tt in t:
        if tt[0] in hrole.keys(): # prevent duplicate result from SQL query
            continue
        roles = str2list(tt[1])
        highest_role_order_id = float('inf')
        include_ok = (len(include_roles) == 0)
        exclude_ok = True
        for role in roles:
            if role in app.roles.keys():
                if app.roles[role]["order_id"] < highest_role_order_id:
                    highest_role_order_id = app.roles[role]["order_id"]
            if role in include_roles:
                include_ok = True
            if role in exclude_roles:
                exclude_ok = False
                break
        if not include_ok or not exclude_ok:
            continue

        hrole[tt[0]] = highest_role_order_id
        rret[tt[0]] = await GetUserInfo(request, userid = tt[0])

    ret = []
    if sort_by_highest_role:
        hrole = dict(sorted(hrole.items(), key=lambda x: (x[1], x[0])))
        if hrole_order_by == "ASC":
            hrole = dict(reversed(list(hrole.items())))
    for userid in hrole.keys():
        ret.append(rret[userid])

    if after_userid is not None:
        while len(ret) > 0 and ret[0]["userid"] != after_userid:
            ret = ret[1:]

    return {"list": ret[max(page-1, 0) * page_size : page * page_size], "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size))}

async def get_banner(request: Request, response: Response,
    userid: Optional[int] = None, uid: Optional[int] = None, discordid: Optional[int] = None, steamid: Optional[int] = None, truckersmpid: Optional[int] = None):
    """Returns the banner generated by [BannerGen]"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    qu = ""
    if userid is not None:
        qu = f"userid = {userid}"
    elif uid is not None:
        qu = f"uid = {uid}"
    elif discordid is not None:
        qu = f"discordid = {discordid}"
    elif steamid is not None:
        qu = f"steamid = {steamid}"
    elif truckersmpid is not None:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    await app.db.execute(dhrid, f"SELECT name, discordid, avatar, join_timestamp, roles, userid FROM user WHERE {qu} AND userid >= 0")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0 or t[0][5] in [-1, None]:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    if userid in [-1, None]:
        return RedirectResponse(url=f"{app.config.prefix}/member/banner?userid={t[0][5]}", status_code=302)

    for param in request.query_params:
        if param != "userid":
            return RedirectResponse(url=f"{app.config.prefix}/member/banner?userid={userid}", status_code=302)

    t = t[0]
    userid = t[5]
    name = t[0]
    tname = name
    while tname.startswith(" "):
        tname = tname[1:]
    name = tname
    discordid = t[1]
    avatar = t[2]
    join_timestamp = t[3]
    roles = str2list(t[4])
    highest = None
    highest_role = ""
    for role in roles:
        if role in app.roles.keys():
            if highest is None or app.roles[role]["order_id"] < highest:
                highest = app.roles[role]["order_id"]
                highest_role = app.roles[role]["name"]
    joined = datetime.fromtimestamp(join_timestamp)
    joined = f"{joined.year}/{str(joined.month).zfill(2)}/{str(joined.day).zfill(2)}"

    if os.path.exists(f"/tmp/hub/banner/{app.config.abbr}_{userid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{app.config.abbr}_{userid}.png") <= 600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{app.config.abbr}_{userid}.png","rb").read()]), media_type="image/jpeg")
            return response

    rl = await ratelimit(request, 'GET /member/banner', 10, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    rank_name = None
    division_name = None
    total_points = 0
    await app.db.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        total_points += nint(t[0][0])
    await app.db.execute(dhrid, f"SELECT SUM(points) FROM challenge_completed WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        total_points += nint(t[0][0])
    await app.db.execute(dhrid, f"SELECT SUM(points) FROM event WHERE attendee LIKE '%,{userid},%'")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        total_points += nint(t[0][0])
    await app.db.execute(dhrid, f"SELECT dlog.userid, division.divisionid, COUNT(dlog.distance), SUM(dlog.distance) \
        FROM dlog \
        INNER JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        WHERE dlog.logid >= 0 AND dlog.userid = {userid} \
        GROUP BY dlog.userid, division.divisionid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if oo[1] in app.division_points.keys():
            if app.division_points[oo[1]]["mode"] == "static":
                total_points += oo[2] * app.division_points[oo[1]]["value"]
            elif app.division_points[oo[1]]["mode"] == "ratio":
                total_points += oo[3] * app.division_points[oo[1]]["value"]
    await app.db.execute(dhrid, f"SELECT SUM(point) FROM bonus_point WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        total_points += nint(t[0][0])
    total_points = int(total_points)

    highest_rank = -1
    for rank_type in app.config.rank_types:
        if rank_type["default"]:
            for rank in rank_type["details"]:
                if total_points >= rank["points"] and highest_rank < rank["points"]:
                    rank_name = rank["name"]
                    highest_rank = rank["points"]
                else:
                    break

    for role in roles:
        for division in app.config.divisions:
            if division["role_id"] == role:
                division_name = division["name"]
                break

    first_row = app.config.banner_info_first_row
    if app.config.banner_info_first_row == "division_first":
        if division_name is None:
            first_row = "rank"
        else:
            first_row = "division"

    if rank_name is None:
        rank_name = "N/A"
    if division_name is None:
        division_name = "N/A"

    distance = 0
    await app.db.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    distance = nint(t[0][0])
    if app.config.distance_unit == "imperial":
        distance = int(distance * 0.621371)
        distance = f"{tseparator(distance)}mi"
    else:
        distance = f"{tseparator(distance)}km"

    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 1")
    t = await app.db.fetchall(dhrid)
    europrofit = 0
    if len(t) > 0:
        europrofit = nint(t[0][0])
    await app.db.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 2")
    t = await app.db.fetchall(dhrid)
    dollarprofit = 0
    if len(t) > 0:
        dollarprofit = nint(t[0][0])
    profit = f"€{sigfig(europrofit)} + ${sigfig(dollarprofit)}"

    try:
        r = await arequests.post(app, app.banner_service_url, data=json.dumps({"company_abbr": app.config.abbr, \
            "company_name": app.config.name, "logo_url": app.config.logo_url, "hex_color": app.config.hex_color, \
            "background_opacity": app.config.banner_background_opacity, "background_url": app.config.banner_background_url, \
            "userid": userid, "joined": joined, "highest_role": highest_role, \
            "avatar": avatar, "name": name, "first_row": first_row, \
            "rank": rank_name, "division": division_name, "distance": distance, "profit": profit}), \
            headers = {"Content-Type": "application/json"}, timeout = 5)
        if r.status_code // 100 != 2:
            response.status_code = 503
            return {"error": ml.tr(request, "banner_service_unavailable")}

        response = StreamingResponse(iter([r.content]), media_type="image/jpeg")
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]
        response.headers["Cache-Control"] = "public, max-age=600, stale-if-error=86400"
        return response

    except:
        response.status_code = 503
        return {"error": ml.tr(request, "banner_service_unavailable")}
