# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import os
import time
import traceback
from datetime import datetime
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import RedirectResponse, StreamingResponse
from apis.member.manage import *
from apis.member.userop import *

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *


# Basic Info Section
@app.get(f"/{config.abbr}/member/roles")
async def get_member_roles():
    return config.roles

@app.get(f"/{config.abbr}/member/ranks")
async def get_member_ranks():
    return config.ranks

@app.get(f"/{config.abbr}/member/perms")
async def get_member_perms():
    return PERMS_STR

# Member Info Section
@app.get(f'/{config.abbr}/member/list')
async def get_member_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, \
        query: Optional[str] = '', roles: Optional[str] = '', last_seen_after: Optional[int] = -1,\
        order_by: Optional[str] = "highest_role", order: Optional[str] = "desc"):
    """Returns a list of members"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /member/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    if config.privacy:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await ActivityUpdate(dhrid, au["uid"], f"members")
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    lroles = roles.split(",")
    lroles = [int(x) for x in lroles if isint(x)]
    if len(lroles) > 100:
        lroles = lroles[:100]

    query = convert_quotation(query).lower()
    
    order_by_last_seen = False
    if not order_by in ["user_id", "name", "uid", "discord_id", "highest_role", "join_timestamp", "last_seen"]:
        order_by = "user_id"
        order = "asc"
    if order_by == "last_seen":
        order_by_last_seen = True
    cvt = {"user_id": "userid", "name": "name", "uid": "uid", "discord_id": "discordid", "join_timestamp": "join_timestamp", "highest_role": "highest_role", "last_seen": "userid"}
    order_by = cvt[order_by]

    sort_by_highest_role = False
    hrole_order_by = "asc"
    if order_by == "highest_role":
        sort_by_highest_role = True
        order_by = "userid"

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()

    if sort_by_highest_role:
        hrole_order_by = order
        if order == "ASC":
            order = "DESC"
        elif order == "DESC":
            order = "ASC"

    activity_limit = ""
    if last_seen_after >= 0:
        activity_limit = f"AND user.uid IN (SELECT user_activity.uid FROM user_activity WHERE user_activity.timestamp >= {last_seen_after}) "

    hrole = {}
    if order_by_last_seen:
        await aiosql.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{query}%' AND user.userid >= 0 {activity_limit} ORDER BY user_activity.timestamp {order}, user.userid ASC")
    else:
        await aiosql.execute(dhrid, f"SELECT user.userid, user.roles FROM user LEFT JOIN user_activity ON user.uid = user_activity.uid WHERE LOWER(user.name) LIKE '%{query}%' AND user.userid >= 0 {activity_limit} ORDER BY {order_by} {order}")
    t = await aiosql.fetchall(dhrid)
    rret = {}
    for tt in t:
        if tt[0] in hrole.keys(): # prevent duplicate result from SQL query
            continue
        roles = tt[1].split(",")
        roles = [int(x) for x in roles if isint(x)]
        highestrole = 99999
        ok = False
        if len(lroles) == 0:
            ok = True
        for role in roles:
            if role < highestrole:
                highestrole = role
            if role in lroles:
                ok = True
        if not ok:
            continue
        hrole[tt[0]] = highestrole
        rret[tt[0]] = await GetUserInfo(dhrid, request, userid = tt[0])

    ret = []
    if sort_by_highest_role:
        hrole = dict(sorted(hrole.items(), key=lambda x:x[1]))
        if hrole_order_by == "ASC":
            hrole = dict(reversed(list(hrole.items())))
    for userid in hrole.keys():
        ret.append(rret[userid])
        
    return {"list": ret[(page - 1) * page_size : page * page_size], "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size))}

@app.get(f'/{config.abbr}/member/banner')
async def get_member_banner(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, uid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    """Returns the banner generated by [BannerGen]"""

    if not "banner" in config.enabled_plugins:
        response.status_code = 404
        return {"error": "Not Found"}
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    qu = ""
    if userid != -1:
        qu = f"userid = {userid}"
    elif uid != -1:
        qu = f"uid = {uid}"
    elif discordid != -1:
        qu = f"discordid = {discordid}"
    elif steamid != -1:
        qu = f"steamid = {steamid}"
    elif truckersmpid != -1:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    await aiosql.execute(dhrid, f"SELECT name, discordid, avatar, join_timestamp, roles, userid FROM user WHERE {qu} AND userid >= 0")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    if userid == -1:
        return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={t[0][5]}", status_code=302)

    for param in request.query_params:
        if param != "userid":
            return RedirectResponse(url=f"/{config.abbr}/member/banner?userid={userid}", status_code=302)
            
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
    roles = t[4].split(",")
    roles = [int(x) for x in roles if isint(x)]
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    highest_role = ""
    if highest in ROLES.keys():
        highest_role = ROLES[highest]
    joined = datetime.fromtimestamp(join_timestamp)
    joined = f"{joined.year}/{str(joined.month).zfill(2)}/{str(joined.day).zfill(2)}"

    if os.path.exists(f"/tmp/hub/banner/{config.abbr}_{discordid}.png"):
        if time.time() - os.path.getmtime(f"/tmp/hub/banner/{config.abbr}_{discordid}.png") <= 3600:
            response = StreamingResponse(iter([open(f"/tmp/hub/banner/{config.abbr}_{discordid}.png","rb").read()]), media_type="image/jpeg")
            return response

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /member/banner', 10, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    division = ""
    for i in roles:
        for divi in divisions:
            if str(divi["role_id"]) == str(i):
                division = divi["name"]
                break
    if division == "":
        division = "N/A"

    distance = 0
    await aiosql.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        distance = 0 if t[0][0] is None else int(t[0][0])
        if config.distance_unit == "imperial":
            distance = int(distance * 0.621371)
            distance = f"{distance}mi"
        else:
            distance = f"{distance}km"
    
    await aiosql.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 1")
    t = await aiosql.fetchall(dhrid)
    europrofit = 0
    if len(t) > 0:
        europrofit = 0 if t[0][0] is None else nint(t[0][0])
    await aiosql.execute(dhrid, f"SELECT SUM(profit) FROM dlog WHERE userid = {userid} AND unit = 2")
    t = await aiosql.fetchall(dhrid)
    dollarprofit = 0
    if len(t) > 0:
        dollarprofit = 0 if t[0][0] is None else nint(t[0][0])
    profit = f"€{sigfig(europrofit)} + ${sigfig(dollarprofit)}"

    try:
        r = await arequests.post("http://127.0.0.1:8700/banner", data={"company_abbr": config.abbr, \
            "company_name": config.name, "logo_url": config.logo_url, "hex_color": config.hex_color,
            "discordid": discordid, "joined": joined, "highest_role": highest_role, \
                "avatar": avatar, "name": name, "division": division, "distance": distance, "profit": profit}, timeout = 5)
        if r.status_code // 100 != 2:
            response.status_code = r.status_code
            return {"error": r.text}
            
        response = StreamingResponse(iter([r.content]), media_type="image/jpeg")
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]
        response.headers["Cache-Control"] = "public, max-age=7200, stale-if-error=604800"
        return response
        
    except:
        response.status_code = 503
        return {"error": "Service Unavailable"}