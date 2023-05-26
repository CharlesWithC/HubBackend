# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time

import multilang as ml
from functions.arequests import *
from functions.dataop import *
from functions.general import *
from functions.security import auth, checkPerm
from static import *


async def getHighestActiveRole(request):
    (app, dhrid) = (request.app, request.state.dhrid)
    for roleid in app.roles.keys(): # this is sorted based on the order_id
        await app.db.execute(dhrid, f"SELECT uid FROM user WHERE roles LIKE '%,{roleid},%'")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0:
            return roleid
    return list(app.roles.keys())[0]

def getAvatarSrc(discordid, avatar):
    if avatar is None:
        return ""
    if avatar.startswith("a_"):
        src = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.gif"
    else:
        src = f"https://cdn.discordapp.com/avatars/{discordid}/{avatar}.png"
    src = convertQuotation(src)
    return src

async def ActivityUpdate(request, uid, activity):
    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None or int(uid) < 0:
        return
    activity = convertQuotation(activity)
    await app.db.execute(dhrid, f"SELECT timestamp FROM user_activity WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        last_timestamp = t[0][0]
        if int(time.time()) - last_timestamp <= 3:
            return
        await app.db.execute(dhrid, f"UPDATE user_activity SET activity = '{activity}', timestamp = {int(time.time())} WHERE uid = {uid}")
    else:
        await app.db.execute(dhrid, f"INSERT INTO user_activity VALUES ({uid}, '{activity}', {int(time.time())})")
    await app.db.commit(dhrid)

# app.state.cache_userinfo = {} # user info cache (15 seconds)
# app.state_cache_activity = {} # activity cache (2 seconds)

def ClearUserCache(app):
    users = list(app.state.cache_userinfo.keys())
    for user in users:
        if int(time.time()) > app.state.cache_userinfo[user]["expire"]:
            del app.state.cache_userinfo[user]
    users = list(app.state_cache_activity.keys())
    for user in users:
        if int(time.time()) > app.state_cache_activity[user]["expire"]:
            del app.state_cache_activity[user]

async def GetUserInfo(request, userid = -1, discordid = -1, uid = -1, privacy = False, tell_deleted = False, include_sensitive = False, ignore_activity = False, nocache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    if None in [userid, discordid, uid]:
        return {"uid": None, "userid": None, "name": None, "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    miscuserid = {-999: "system", -1000: "company", -1001: "dealership", -1002: "garage_agency", -1003: "client", -1004: "service_station", -1005: "scrap_station", -1005: "blackhole"}
    if userid == -1000:
        return {"uid": None, "userid": None, "name": app.config.name, "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": app.config.logo_url, "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
    if userid in miscuserid.keys():
        return {"uid": None, "userid": None, "name": ml.tr(request, miscuserid[userid]), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    if privacy:
        return {"uid": None, "userid": None, "name": f'[{ml.tr(request, "protected")}]', "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    if userid == -1 and discordid == -1 and uid == -1:
        if not tell_deleted:
            return {"uid": None, "userid": None, "name": ml.tr(request, "unknown"), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
        else:
            return {"uid": None, "userid": None, "name": ml.tr(request, "unknown"), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None, "is_deleted": True}

    ClearUserCache(app)

    if not nocache:
        if userid != -1 and f"userid={userid}" in app.state.cache_userinfo.keys():
            if int(time.time()) < app.state.cache_userinfo[f"userid={userid}"]["expire"]:
                uid = app.state.cache_userinfo[f"userid={userid}"]["uid"]
        if discordid != -1 and f"discordid={discordid}" in app.state.cache_userinfo.keys():
            if int(time.time()) < app.state.cache_userinfo[f"discordid={discordid}"]["expire"]:
                uid = app.state.cache_userinfo[f"discordid={discordid}"]["uid"]
        if uid != -1 and f"uid={uid}" in app.state.cache_userinfo.keys():
            if int(time.time()) < app.state.cache_userinfo[f"uid={uid}"]["expire"]:
                ret = app.state.cache_userinfo[f"uid={uid}"]["data"]
                if ignore_activity:
                    ret["activity"] = None
                if not ignore_activity and (f"uid={uid}" not in app.state_cache_activity.keys() or \
                    f"uid={uid}" in app.state_cache_activity.keys() and int(time.time()) >= app.state_cache_activity[f"uid={uid}"]["expire"]):
                    activity = None
                    await app.db.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
                    ac = await app.db.fetchall(dhrid)
                    if len(ac) != 0:
                        if int(time.time()) - ac[0][1] >= 300:
                            activity = {"status": "offline", "last_seen": ac[0][1]}
                        elif int(time.time()) - ac[0][1] >= 120:
                            activity = {"status": "online", "last_seen": ac[0][1]}
                        else:
                            activity = {"status": ac[0][0], "last_seen": ac[0][1]}
                        app.state_cache_activity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
                    else:
                        app.state_cache_activity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}
                    ret["activity"] = app.state_cache_activity[f"uid={uid}"]["data"]
                return ret

    query = ""
    if userid != -1:
        query = f"userid = {userid}"
    elif discordid != -1:
        query = f"discordid = {discordid}"
    elif uid != -1:
        query = f"uid = {uid}"

    await app.db.execute(dhrid, f"SELECT uid, userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, mfa_secret, join_timestamp FROM user WHERE {query}")
    p = await app.db.fetchall(dhrid)
    if len(p) == 0:
        uid = None if uid == -1 else uid
        userid = None if userid == -1 else userid
        discordid = None if discordid == -1 else discordid
        if not tell_deleted:
            return {"uid": uid, "userid": userid, "name": ml.tr(request, "unknown"), "email": None, "discordid": nstr(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
        else:
            return {"uid": uid, "userid": userid, "name": ml.tr(request, "unknown"), "email": None, "discordid": nstr(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": None, "join_timestamp": None, "is_deleted": True}

    uid = p[0][0]

    if request is not None and "headers" in request.__dict__.keys():
        if "authorization" in request.headers.keys():
            authorization = request.headers["authorization"]
            au = await auth(authorization, request, check_member = False)
            if not au["error"]:
                roles = au["roles"]
                for i in roles:
                    if int(i) in app.config.perms.admin:
                        include_sensitive = True
                    if int(i) in app.config.perms.hr or int(i) in app.config.perms.hrm or int(i) in app.config.perms.get_sensitive_profile:
                        include_sensitive = True
                if au["uid"] == uid:
                    include_sensitive = True

    roles = str2list(p[0][6])
    mfa_secret = p[0][10]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True
    email = p[0][3]
    if not include_sensitive:
        email = None
        mfa_enabled = None

    activity = None
    await app.db.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
    ac = await app.db.fetchall(dhrid)
    if len(ac) != 0:
        if int(time.time()) - ac[0][1] >= 300:
            activity = {"status": "offline", "last_seen": ac[0][1]}
        elif int(time.time()) - ac[0][1] >= 120:
            activity = {"status": "online", "last_seen": ac[0][1]}
        else:
            activity = {"status": ac[0][0], "last_seen": ac[0][1]}
        app.state_cache_activity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
    else:
        app.state_cache_activity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}

    if p[0][1] != -1:
        app.state.cache_userinfo[f"userid={p[0][1]}"] = {"uid": uid, "expire": int(time.time()) + 2}
    if p[0][7] != -1:
        app.state.cache_userinfo[f"discordid={p[0][7]}"] = {"uid": uid, "expire": int(time.time()) + 2}

    userid = p[0][1]
    if userid == -1:
        userid = None

    app.state.cache_userinfo[f"uid={uid}"] = {"data": {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": nstr(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}, "expire": int(time.time()) + 15}

    return {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": nstr(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}

# app.state.cache_language = {} # language cache (3 seconds)

def ClearUserLanguageCache(app):
    users = list(app.state.cache_language.keys())
    for user in users:
        if int(time.time()) > app.state.cache_language[user]["expire"]:
            del app.state.cache_language[user]

async def GetUserLanguage(request, uid):
    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None:
        return app.config.language
    ClearUserLanguageCache(app)

    if uid in app.state.cache_language.keys() and int(time.time()) <= app.state.cache_language[uid]["expire"]:
        return app.state.cache_language[uid]["language"]
    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        app.state.cache_language[uid] = {"language": app.config.language, "expire": int(time.time()) + 3}
        return app.config.language
    app.state.cache_language[uid] = {"language": t[0][0], "expire": int(time.time()) + 3}
    return t[0][0]

async def UpdateRoleConnection(request, discordid):
    (app, dhrid) = (request.app, request.state.dhrid)

    if discordid is None:
        return

    userinfo = await GetUserInfo(request, discordid = discordid, nocache = True)
    userid = userinfo["userid"]
    discordid = userinfo["discordid"]
    roles = userinfo["roles"]

    await app.db.execute(dhrid, f"SELECT access_token FROM discord_access_token WHERE discordid = {discordid} AND expire_timestamp > {int(time.time())}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        access_token = t[0][0]
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        if userinfo["join_timestamp"] is None:
            # deleted account
            r = await arequests.put(app, f"https://discord.com/api/v10/users/@me/applications/{app.config.discord_client_id}/role-connection", data = json.dumps({"platform_name": "", "platform_username": "", "metadata": {"member_since": "", "is_driver": "", "dlog": "", "distance": ""}}), headers = headers, dhrid = dhrid)
            if r.status_code in [401, 403]:
                await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE access_token = '{access_token}'")
                await app.db.commit(dhrid)
            return

        is_driver = checkPerm(app, roles, "driver")
        if is_driver:
            await app.db.execute(dhrid, f"SELECT COUNT(logid) FROM dlog WHERE userid = {userid} AND logid >= 0")
            t = await app.db.fetchone(dhrid)
            if len(t) != 0:
                discord_jobs = nint(t[0])
            await app.db.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
            t = await app.db.fetchone(dhrid)
            if len(t) != 0:
                discord_distance = nint(t[0])
            r = await arequests.put(app, f"https://discord.com/api/v10/users/@me/applications/{app.config.discord_client_id}/role-connection", data = json.dumps({"platform_name": "Drivers Hub", "platform_username": userinfo["name"], "metadata": {"member_since": str(datetime.fromtimestamp(userinfo["join_timestamp"])), "is_driver": "true" if is_driver else "false", "dlog": str(discord_jobs), "distance": str(discord_distance)}}), headers = headers, dhrid = dhrid)
            if r.status_code in [401, 403]:
                await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE access_token = '{access_token}'")
                await app.db.commit(dhrid)
        else:
            r = await arequests.put(app, f"https://discord.com/api/v10/users/@me/applications/{app.config.discord_client_id}/role-connection", data = json.dumps({"platform_name": "Drivers Hub", "platform_username": userinfo["name"], "metadata": {"member_since": str(datetime.fromtimestamp(userinfo["join_timestamp"])), "is_driver": "true" if is_driver else "false"}}), headers = headers, dhrid = dhrid)
            if r.status_code in [401, 403]:
                await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE access_token = '{access_token}'")
                await app.db.commit(dhrid)

async def DeleteRoleConnection(request, discordid):
    (app, dhrid) = (request.app, request.state.dhrid)

    if discordid is None:
        return

    await app.db.execute(dhrid, f"SELECT access_token FROM discord_access_token WHERE discordid = {discordid} AND expire_timestamp > {int(time.time())}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        access_token = t[0][0]
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

        r = await arequests.put(app, f"https://discord.com/api/v10/users/@me/applications/{app.config.discord_client_id}/role-connection", data = json.dumps({"platform_name": "", "platform_username": "", "metadata": {}}), headers = headers, dhrid = dhrid)
        if r.status_code in [401, 403]:
            await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE access_token = '{access_token}'")
            await app.db.commit(dhrid)
