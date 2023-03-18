# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import traceback
from typing import Optional

from apis.user.connections import *
from apis.user.language import *
from apis.user.manage import *
from apis.user.mfa import *
from apis.user.notification import *
from apis.user.password import *
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *


@app.get(f"/{config.abbr}/user/list")
async def get_user_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, query: Optional[str] = '', \
        order_by: Optional[str] = "uid", order: Optional[str] = "asc"):
    """Returns the information of a list of users
    
    Not all information is included, use `/user/profile` for detailed profile."""
    
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "get_pending_user_list"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250
    
    query = convertQuotation(query).lower()
    
    if not order_by in ["name", "uid", "discord_id", "join_timestamp"]:
        order_by = "discord_id"
        order = "asc"
    cvt = {"name": "user.name", "uid": "user.uid", "discord_id": "user.discordid", "join_timestamp": "user.join_timestamp"}
    order_by = cvt[order_by]

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
    
    await aiosql.execute(dhrid, f"SELECT user.uid, banned.reason, banned.expire_timestamp FROM user LEFT JOIN banned ON banned.uid = user.uid WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{query}%' ORDER BY {order_by} {order} LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        user = await GetUserInfo(dhrid, request, uid = tt[0])
        if tt[1] != None:
            user["ban"] = {"reason": tt[1], "expire": tt[2]}
        else:
            user["ban"] = None
        if "roles" in user.keys():
            del user["roles"]
        ret.append(user)

    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE userid < 0 AND LOWER(name) LIKE '%{query}%'")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.get(f'/{config.abbr}/user/profile')
async def get_user_profile(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = -1, uid: Optional[int] = -1, discordid: Optional[int] = -1, steamid: Optional[int] = -1, truckersmpid: Optional[int] = -1):
    """Returns the profile of a specific user
    
    If no request param is provided, then returns the profile of the authorized user."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /user', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    request_uid = -1
    aulanguage = ""
    if userid == -1 and uid == -1 and discordid == -1 and steamid == -1 and truckersmpid == -1:
        au = await auth(dhrid, authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            uid = au["uid"] # self-query
            request_uid = au["uid"]
            aulanguage = au["language"]
    else:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            if config.privacy:
                response.status_code = au["code"]
                del au["code"]
                return au
        else:
            request_uid = au["uid"]
            aulanguage = au["language"]

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
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}

    await aiosql.execute(dhrid, f"SELECT userid, uid FROM user WHERE {qu}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    userid = t[0][0]
    uid = t[0][1]
    
    if userid >= 0:
        await ActivityUpdate(dhrid, request_uid, f"member_{userid}")

    return (await GetUserInfo(dhrid, request, uid = uid))

@app.patch(f"/{config.abbr}/user/profile")
async def patch_user_profile(request: Request, response: Response, authorization: str = Header(None), uid: Optional[int] = -1):
    """Syncs the profile of a specific user to their current Discord profile
    
    If `uid` in request param is not provided, then syncs the profile for the authorized user.
    
    [DEPRECATED] This function will be moved or removed when the user system no longer relies on Discord."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/profile', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staffmode = False

    discordid = -1
    if uid == -1 or uid == au["uid"]:
        uid = au["uid"]
        discordid = au["discordid"]
    else:
        au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "hr", "patch_username"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await aiosql.execute(dhrid, f"SELECT discordid FROM user WHERE uid = '{uid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}
        staffmode = True
        discordid = t[0][0]

    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "discord_not_connected", force_lang = au["language"])}
    
    if config.discord_bot_token == "":
        response.status_code = 503
        return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

    try:
        r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {config.discord_bot_token}"}, dhrid = dhrid)
    except:
        traceback.print_exc()
        if not staffmode:
            return {"error": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    if r.status_code == 404:
        if not staffmode:
            return {"error": ml.tr(request, "must_join_discord", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_not_in_discord", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        if not staffmode:
            return {"error": ml.tr(request, "discord_check_fail", force_lang = au["language"])}
        else:
            return {"error": ml.tr(request, "user_discord_check_failed", force_lang = au["language"])}
    d = json.loads(r.text)
    username = convertQuotation(d["user"]["username"])
    avatar = ""
    if config.use_server_nickname and d["nick"] != None:
        username = convertQuotation(d["nick"])
    if d["user"]["avatar"] != None:
        avatar = convertQuotation(d["user"]["avatar"])
        avatar = getAvatarSrc(discordid, avatar)
        
    await aiosql.execute(dhrid, f"UPDATE user SET name = '{username}', avatar = '{avatar}' WHERE uid = '{uid}'")
    await aiosql.commit(dhrid)

    return Response(status_code=204)
    
@app.patch(f'/{config.abbr}/user/bio')
async def patch_user_bio(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the bio of the authorized user, returns 204
    
    JSON: `{"bio": str}`"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/bio', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        bio = str(data["bio"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        
    if len(bio) > 1000:
        response.status_code = 400
        return {"error": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET bio = '{b64e(bio)}' WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    return Response(status_code=204)