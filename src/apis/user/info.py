# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import traceback
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, query: Optional[str] = '', \
        order_by: Optional[str] = "uid", order: Optional[str] = "asc"):
    """Returns the information of a list of users
    
    Not all information is included, use `/user/profile` for detailed profile."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hr", "hrm", "get_pending_user_list"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

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
    
    await app.db.execute(dhrid, f"SELECT user.uid, banned.reason, banned.expire_timestamp FROM user LEFT JOIN banned ON banned.uid = user.uid WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{query}%' ORDER BY {order_by} {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        user = await GetUserInfo(request, uid = tt[0])
        if tt[1] is not None:
            user["ban"] = {"reason": tt[1], "expire": tt[2]}
        else:
            user["ban"] = None
        if "roles" in user.keys():
            del user["roles"]
        ret.append(user)

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM user WHERE userid < 0 AND LOWER(name) LIKE '%{query}%'")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_profile(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = None, uid: Optional[int] = None, discordid: Optional[int] = None, steamid: Optional[int] = None, truckersmpid: Optional[int] = None):
    """Returns the profile of a specific user
    
    If no request param is provided, then returns the profile of the authorized user."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/profile', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    
    request_uid = -1
    aulanguage = ""
    if userid is None and uid is None and discordid is None and steamid is None and truckersmpid is None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            uid = au["uid"] # self-query
            request_uid = au["uid"]
            aulanguage = au["language"]
    else:
        au = await auth(authorization, request, allow_application_token = True)
        if au["error"]:
            if app.config.privacy:
                response.status_code = au["code"]
                del au["code"]
                return au
        else:
            request_uid = au["uid"]
            aulanguage = au["language"]

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
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}

    await app.db.execute(dhrid, f"SELECT userid, uid FROM user WHERE {qu}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    userid = t[0][0]
    uid = t[0][1]
    
    if userid >= 0:
        await ActivityUpdate(request, request_uid, f"member_{userid}")

    return (await GetUserInfo(request, uid = uid))

async def patch_profile(request: Request, response: Response, authorization: str = Header(None), uid: Optional[int] = None, sync_to_discord: Optional[bool] = False, sync_to_steam: Optional[bool] = False):
    """Updates the profile of a specific user

    If `sync_to_discord` is `true`, then syncs to their Discord profile.
    
    If `uid` in request param is not provided, then syncs the profile for the authorized user."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/profile', 60, 15)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staffmode = False

    discordid = -1
    if uid is None or uid == au["uid"]:
        uid = au["uid"]
        discordid = au["discordid"]
    else:
        au = await auth(authorization, request, required_permission = ["admin", "hrm", "hr", "manage_profile"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await app.db.execute(dhrid, f"SELECT discordid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}
        staffmode = True
        discordid = t[0][0]

    if sync_to_discord:
        if discordid is None:
            response.status_code = 428
            if not staffmode:
                return {"error": ml.tr(request, "connection_not_found", var = {"app": "Discord"}, force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "Discord"}, force_lang = au["language"])}
        
        if app.config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers={"Authorization": f"Bot {app.config.discord_bot_token}"}, dhrid = dhrid)
        except:
            response.status_code = 503
            if not staffmode:
                return {"error": ml.tr(request, "user_in_guild_check_failed", force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "current_user_in_guild_check_faileded", force_lang = au["language"])}
        if r.status_code == 404:
            response.status_code = 428
            if not staffmode:
                return {"error": ml.tr(request, "current_user_didnt_join_discord", force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "user_didnt_join_discord", force_lang = au["language"])}
        if r.status_code // 100 != 2:
            response.status_code = r.status_code
            if not staffmode:
                return {"error": ml.tr(request, "user_in_guild_check_failed", force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "current_user_in_guild_check_faileded", force_lang = au["language"])}
        d = json.loads(r.text)
        name = convertQuotation(d["user"]["username"])
        avatar = ""
        if app.config.use_server_nickname and d["nick"] is not None:
            name = convertQuotation(d["nick"])
        if d["user"]["avatar"] is not None:
            avatar = getAvatarSrc(discordid, d["user"]["avatar"])
            
        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)
    
    elif sync_to_steam:
        await app.db.execute(dhrid, f"SELECT steamid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        steamid = t[0][0]
        if steamid is None:
            response.status_code = 428
            if not staffmode:
                return {"error": ml.tr(request, "connection_not_found", var = {"app": "Steam"}, force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"}, force_lang = au["language"])}

        if app.config.steam_api_key == "":
            response.status_code = 503
            return {"error": ml.tr(request, "steam_api_key_not_configured", force_lang = au["language"])}

        try:
            r = await arequests.get(app, f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={app.config.steam_api_key}&steamids={steamid}", dhrid = dhrid)
        except:
            response.status_code = 503
            return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}
        try:
            d = json.loads(r.text)
            name = convertQuotation(d["response"]["players"][0]["personaname"])
            avatar = convertQuotation(d["response"]["players"][0]["avatarfull"])
        except:
            response.status_code = 503
            return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}

        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)

    else:
        if not staffmode and not app.config.allow_custom_profile:
            response.status_code = 403
            return {"error": ml.tr(request, "custom_profile_disabled", force_lang = au["language"])}
        
        data = await request.json()
        try:
            name = convertQuotation(data["name"])
            if len(name) > 32:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "name", "limit": "32"}, force_lang = au["language"])}
            avatar = convertQuotation(data["avatar"])
            if len(name) > 256:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "avatar", "limit": "256"}, force_lang = au["language"])}
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            
        avatar_domain = getDomainFromUrl(avatar)
        if not avatar_domain:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_avatar_url", force_lang = au["language"])}
        
        ok = False
        for domain in app.config.avatar_domain_whitelist:
            if avatar_domain == domain or avatar_domain.endswith("." + domain): # domain / subdomain
                ok = True
        if not ok:
            response.status_code = 400
            return {"error": ml.tr(request, "avatar_domain_not_whitelisted", force_lang = au["language"])}
        
        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)

    return Response(status_code=204)
    
async def patch_bio(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the bio of the authorized user, returns 204
    
    JSON: `{"bio": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/bio', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        bio = str(data["bio"])
        if len(bio) > 1000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET bio = '{b64e(bio)}' WHERE uid = {uid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)