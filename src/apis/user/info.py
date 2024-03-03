# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def get_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, after_uid: Optional[int] = None, name: Optional[str] = '', \
        joined_after: Optional[int] = None, joined_before: Optional[int] = None, \
        order_by: Optional[str] = "uid", order: Optional[str] = "asc"):
    """Returns the information of a list of users

    Not all information is included, use `/user/profile` for detailed profile."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "view_external_user_list"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    name = convertQuotation(name).lower()

    if order_by not in ['name', 'email', 'uid', 'discordid', 'steamid', 'truckersmpid', 'join_timestamp']:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    cvt = {"name": "user.name", "email": "user.email", "uid": "user.uid", "discordid": "user.discordid", "steamid": "user.steamid", "truckersmpid": "user.truckersmpid", "join_timestamp": "user.join_timestamp"}
    order_by = cvt[order_by]

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    limit = ""
    if joined_after is not None:
        limit += f"AND user.join_timestamp >= {joined_after} "
    if joined_before is not None:
        limit += f"AND user.join_timestamp <= {joined_before} "

    await app.db.execute(dhrid, f"SELECT DISTINCT user.uid, banned.reason, banned.expire_timestamp FROM user LEFT JOIN banned ON banned.uid = user.uid OR banned.discordid = user.discordid OR banned.steamid = user.steamid OR banned.truckersmpid = user.truckersmpid OR banned.email = user.email AND banned.email LIKE '%@%' WHERE user.userid < 0 AND LOWER(user.name) LIKE '%{name}%' {limit} ORDER BY {order_by} {order}, user.uid DESC")
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

    if after_uid is not None:
        while len(ret) > 0 and ret[0]["uid"] != after_uid:
            ret = ret[1:]

    return {"list": ret[max(page-1, 0) * page_size : page * page_size], "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size))}

async def get_profile(request: Request, response: Response, authorization: str = Header(None), \
    userid: Optional[int] = None, uid: Optional[int] = None, discordid: Optional[int] = None, steamid: Optional[int] = None, truckersmpid: Optional[int] = None, email: Optional[str] = None, role_history_limit: Optional[int] = 50, ban_history_limit: Optional[int] = 50):
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
    au = None
    if userid is None and uid is None and discordid is None and steamid is None and truckersmpid is None and email is None:
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
        if au["error"] and app.config.privacy:
            response.status_code = au["code"]
            del au["code"]
            return au
        elif not au["error"]:
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
    elif email is not None:
        qu = f"email = '{convertQuotation(email)}'"
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

    userinfo = await GetUserInfo(request, uid = uid)
    (uid, discordid, steamid, truckersmpid, email) = (userinfo["uid"], userinfo["discordid"], userinfo["steamid"], userinfo["truckersmpid"], userinfo["email"])
    uid = uid if uid is not None else "NULL"
    email = f"'{email}'" if email is not None and "@" in email else "NULL"
    discordid = discordid if discordid is not None else "NULL"
    steamid = steamid if steamid is not None else "NULL"
    truckersmpid = truckersmpid if truckersmpid is not None else "NULL"

    await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE uid = {uid} OR discordid = {discordid} OR steamid = {steamid} OR truckersmpid = {truckersmpid} OR email = {email}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        userinfo["ban"] = {"reason": t[0][0], "expire": t[0][1]}
    else:
        userinfo["ban"] = None

    if (await GetUserPrivacy(request, userinfo['uid']))["role_history"] and (au is None or au["error"] or uid != au["uid"] and not checkPerm(app, au["roles"], ["administrator", "view_privacy_protected_data"])):
        userinfo["role_history"] = None
    else:
        await app.db.execute(dhrid, f"SELECT historyid, added_roles, removed_roles, timestamp FROM user_role_history WHERE uid = {userinfo['uid']} ORDER BY historyid DESC LIMIT {role_history_limit}")
        p = await app.db.fetchall(dhrid)
        userinfo["role_history"] = []
        for pp in p:
            userinfo["role_history"].append({"historyid": pp[0], "added_roles": deduplicate(str2list(pp[1])), "removed_roles": deduplicate(str2list(pp[2])), "timestamp": pp[3]})

    if (await GetUserPrivacy(request, userinfo['uid']))["ban_history"] and (au is None or au["error"] or uid != au["uid"] and not checkPerm(app, au["roles"], ["administrator", "view_privacy_protected_data"])):
        userinfo["ban_history"] = None
    else:
        connections = []
        fields = ["uid", "email", "discordid", "steamid", "truckersmpid"]
        for field in fields:
            if field == "email":
                if userinfo[field] is None or '@' not in userinfo[field]:
                    field = "NULL"
                else:
                    field = f"'{convertQuotation(userinfo[field])}'"
            else:
                field = userinfo[field]
            if field is None:
                field = "NULL"
            connections.append(field)
        await app.db.execute(dhrid, f"SELECT historyid, reason, expire_timestamp FROM ban_history WHERE uid = {connections[0]} OR email = {connections[1]} OR discordid = {connections[2]} OR steamid = {connections[3]} OR truckersmpid = {connections[4]} ORDER BY historyid DESC LIMIT {ban_history_limit}")
        p = await app.db.fetchall(dhrid)
        userinfo["ban_history"] = []
        for pp in p:
            userinfo["ban_history"].append({"historyid": pp[0], "reason": pp[1], "expire_timestamp": pp[2]})

    return userinfo

async def patch_profile(request: Request, response: Response, authorization: str = Header(None), uid: Optional[int] = None, sync_to_discord: Optional[bool] = False, sync_to_steam: Optional[bool] = False, sync_to_truckersmp: Optional[bool] = False):
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
        au = await auth(authorization, request, required_permission = ["administrator", "manage_profiles"])
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
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers={"Authorization": f"Bot {app.config.discord_bot_token}"}, dhrid = dhrid)
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
        if d["user"]['global_name'] is not None:
            name = str(d["user"]['global_name'])
        else:
            name = str(d["user"]['username'])
        name = convertQuotation(name)
        avatar = ""
        if app.config.use_server_nickname and d["nick"] is not None:
            name = convertQuotation(d["nick"])
        if d["user"]["avatar"] is not None:
            avatar = getAvatarSrc(discordid, d["user"]["avatar"])

        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await UpdateRoleConnection(request, discordid)

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
            return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"}, force_lang = au["language"])}
        try:
            d = json.loads(r.text)
            name = convertQuotation(d["response"]["players"][0]["personaname"])
            avatar = convertQuotation(d["response"]["players"][0]["avatarfull"])
        except:
            response.status_code = 503
            return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"}, force_lang = au["language"])}

        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await UpdateRoleConnection(request, discordid)

    elif sync_to_truckersmp:
        await app.db.execute(dhrid, f"SELECT truckersmpid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        truckersmpid = t[0][0]
        if truckersmpid is None:
            response.status_code = 428
            if not staffmode:
                return {"error": ml.tr(request, "connection_not_found", var = {"app": "TruckersMP"}, force_lang = au["language"])}
            else:
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "TruckersMP"}, force_lang = au["language"])}

        try:
            r = await arequests.get(app, f"https://api.truckersmp.com/v2/player/{truckersmpid}", dhrid = dhrid)
        except:
            response.status_code = 503
            return {"error": ml.tr(request, 'service_api_error', var = {'service': "TruckersMP"}, force_lang = au["language"])}
        try:
            d = json.loads(r.text)
            name = convertQuotation(d["response"]["name"])
            avatar = convertQuotation(d["response"]["avatar"])
        except:
            response.status_code = 503
            return {"error": ml.tr(request, 'service_api_error', var = {'service': "TruckersMP"}, force_lang = au["language"])}

        await app.db.execute(dhrid, f"UPDATE user SET name = '{name}', avatar = '{avatar}' WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await UpdateRoleConnection(request, discordid)

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

        await UpdateRoleConnection(request, discordid)

    return (await GetUserInfo(request, uid = uid, nocache = True))

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

async def patch_activity(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the activity of the authorized user, returns 204

    JSON: `{"activity": str}`

    [NOTE] `last_seen` is always automatically set"""
    app = request.app
    if app.config.use_custom_activity is False:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/activity', 60, 30)
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
        activity = str(data["activity"])
        if len(activity) > 256:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "activity", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await ActivityUpdate(request, uid, activity, force = True)

    return Response(status_code=204)

async def patch_note(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Updates the note of a user, returns 204

    JSON: `{"note": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/{uid}/note', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    to_uid = uid

    au = await auth(authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    from_uid = au["uid"]

    data = await request.json()
    try:
        note = str(data["note"])
        if len(note) > 1000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM user_note WHERE from_uid = {from_uid} AND to_uid = {to_uid}")
    if note != "":
        await app.db.execute(dhrid, f"INSERT INTO user_note VALUES ({from_uid}, {to_uid}, '{convertQuotation(note)}', {int(time.time())})")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_tracker_switch(request: Request, response: Response, uid: Optional[int] = None, authorization: str = Header(None)):
    """Updates tracker_in_use column of user table in database, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /user/tracker/switch', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    aulanguage = au["language"]

    if uid is not None and uid != au["uid"]:
        # updating tracker for another user
        au = await auth(authorization, request, allow_application_token = True, required_permission=["administrator", "update_roles"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        await app.db.execute(dhrid, f"SELECT userid, uid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = aulanguage)}
    else:
        uid = au["uid"]

    data = await request.json()
    try:
        tracker_in_use = data["tracker"].lower()
        if tracker_in_use == "tracksim":
            tracker_in_use = 2
        elif tracker_in_use == "trucky":
            tracker_in_use = 3
        elif tracker_in_use == "custom":
            tracker_in_use = 4
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_value", var = {"key": "tracker"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET tracker_in_use = {tracker_in_use} WHERE uid = {uid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)
