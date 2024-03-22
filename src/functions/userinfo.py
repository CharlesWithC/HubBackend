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

async def ActivityUpdate(request, uid, activity, force = False):
    # force is True when user manually sets activity

    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None or int(uid) < 0:
        return
    if not app.config.use_custom_activity or force:
        activity = convertQuotation(activity)
        await app.db.execute(dhrid, f"SELECT timestamp FROM user_activity WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            last_timestamp = t[0][0]
            if int(time.time()) - last_timestamp <= 3 and not force:
                return
            await app.db.execute(dhrid, f"UPDATE user_activity SET activity = '{activity}', timestamp = {int(time.time())} WHERE uid = {uid}")
        else:
            await app.db.execute(dhrid, f"INSERT INTO user_activity VALUES ({uid}, '{activity}', {int(time.time())})")
        app.redis.hset(f"uactivity:{uid}", mapping = {"status": activity, "last_seen": int(time.time())})
        app.redis.expire(f"uactivity:{uid}", 60)
        await app.db.commit(dhrid)
    else: # when use_custom_activity is on, only update user last seen
        await app.db.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            if int(time.time()) - t[0][1] <= 3:
                return
            await app.db.execute(dhrid, f"UPDATE user_activity SET timestamp = {int(time.time())} WHERE uid = {uid}")
            app.redis.hset(f"uactivity:{uid}", mapping = {"activity": t[0][0], "last_seen": int(time.time())})
            app.redis.expire(f"uactivity:{uid}", 60)
        else:
            await app.db.execute(dhrid, f"INSERT INTO user_activity VALUES ({uid}, 'online', {int(time.time())})")
            app.redis.hset(f"uactivity:{uid}", mapping = {"status": "online", "last_seen": int(time.time())})
            app.redis.expire(f"uactivity:{uid}", 60)
        await app.db.commit(dhrid)

async def GetUserLanguage(request, uid, nocache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None:
        return app.config.language

    if not nocache:
        language = app.redis.get(f"ulang:{uid}")
        if language:
            app.redis.expire(f"ulang:{uid}", 60)
            return language

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        app.redis.set(f"ulang:{uid}", app.config.language)
        app.redis.expire(f"ulang:{uid}", 60)
        return app.config.language
    else:
        app.redis.set(f"ulang:{uid}", t[0][0])
        app.redis.expire(f"ulang:{uid}", 60)
        return t[0][0]

async def GetUserTimezone(request, uid, nocache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None:
        return "UTC"

    if not nocache:
        timezone = app.redis.get(f"utz:{uid}")
        if timezone:
            app.redis.expire(f"utz:{uid}", 60)
            return timezone

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'timezone'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        app.redis.set(f"utz:{uid}", "UTC")
        app.redis.expire(f"utz:{uid}", 60)
        return "UTC"
    else:
        app.redis.set(f"utz:{uid}", t[0][0])
        app.redis.expire(f"utz:{uid}", 60)
        return t[0][0]

async def GetUserPrivacy(request, uid, nocache = False):
    # False => Not Protected | True => Protected
    (app, dhrid) = (request.app, request.state.dhrid)
    if uid is None:
        return {"role_history": False, "ban_history": False, "email": True, "account_connections": False, "activity": False, "public_profile": False}

    if not nocache:
        privacy = app.redis.get(f"uprivacy:{uid}")
        if privacy:
            d = privacy.split(",")
            app.redis.expire(f"uprivacy:{uid}", 60)
            return {"role_history": TF[d[0]], "ban_history": TF[d[1]], "email": TF[d[2]], "account_connections": TF[d[3]], "activity": TF[d[4]], "public_profile": TF[d[5]]}

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'privacy'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        app.redis.set(f"uprivacy:{uid}", "0,0,1,0,0,0")
        app.redis.expire(f"uprivacy:{uid}", 60)
        return {"role_history": False, "ban_history": False, "email": True, "account_connections": False, "activity": False, "public_profile": False}
    else:
        d_default = [False, False, True, False, False, False]
        d = intify(t[0][0].split(","))
        if len(d) < len(d_default):
            for i in range(len(d), len(d_default)):
                d.append(d_default[i])
        app.redis.set(f"uprivacy:{uid}", ",".join([str(int(x)) for x in d]))
        app.redis.expire(f"uprivacy:{uid}", 60)
        return {"role_history": TF[d[0]], "ban_history": TF[d[1]], "email": TF[d[2]], "account_connections": TF[d[3]], "activity": TF[d[4]], "public_profile": TF[d[5]]}

async def GetUserNote(request, from_uid, to_uid, nocache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    if from_uid is None or to_uid is None:
        return ""

    if not nocache:
        note = app.redis.get(f"unote:{from_uid}/{to_uid}")
        if note:
            return note

    await app.db.execute(dhrid, f"SELECT note FROM user_note WHERE from_uid = {from_uid} AND to_uid = {to_uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        app.redis.set(f"unote:{from_uid}/{to_uid}", "")
        app.redis.expire(f"unote:{from_uid}/{to_uid}", 60)
        return ""
    else:
        app.redis.set(f"unote:{from_uid}/{to_uid}", t[0][0])
        app.redis.expire(f"unote:{from_uid}/{to_uid}", 60)
        return t[0][0]

# to update user info cache, run GetUserInfo with nocache = True
async def GetUserInfo(request, userid = -1, discordid = -1, uid = -1, privacy = False, tell_deleted = False, include_sensitive = False, include_global_note = False, ignore_activity = False, nocache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    if None in [userid, discordid, uid]:
        return {"uid": None, "userid": None, "name": None, "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    miscuserid = {-997: "Trucky", -998: ml.ctr(request, "discord_api"), -999: "system", -1000: "company", -1001: "dealership", -1002: "garage_agency", -1003: "client", -1004: "service_station", -1005: "scrap_station", -1005: "blackhole"}
    if userid == -1000 or uid == -1000:
        return {"uid": None, "userid": None, "name": app.config.name, "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": app.config.logo_url, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
    if userid in miscuserid.keys():
        return {"uid": None, "userid": None, "name": ml.tr(request, miscuserid[userid]), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
    if uid in miscuserid.keys():
        return {"uid": None, "userid": None, "name": ml.tr(request, miscuserid[uid]), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    if privacy:
        return {"uid": None, "userid": None, "name": f'[{ml.tr(request, "protected")}]', "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}

    if userid == -1 and discordid == -1 and uid == -1:
        if not tell_deleted:
            return {"uid": None, "userid": None, "name": ml.tr(request, "unknown"), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
        else:
            return {"uid": None, "userid": None, "name": ml.tr(request, "unknown"), "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None, "is_deleted": True}

    is_member = False
    request_uid = None
    if request is not None and "_headers" in request.__dict__.keys():
        if "authorization" in request.headers.keys():
            authorization = request.headers["authorization"]
            au = await auth(authorization, request, allow_application_token = True, check_member = False)
            if not au["error"]:
                request_uid = au["uid"]
                roles = au["roles"]
                for i in roles:
                    if int(i) in app.config.perms.administrator or int(i) in app.config.perms.view_sensitive_profile:
                        include_sensitive = True
                        include_global_note = True
                    if int(i) in app.config.perms.view_global_note:
                        include_global_note = True
                if au["userid"] >= 0:
                    is_member = True
                if au["uid"] == uid:
                    include_sensitive = True
                    is_member = True

    if not nocache:
        if userid != -1: # attempt to link userid to uid
            res = app.redis.get(f"umap:userid={userid}")
            if res:
                uid = int(res)
        if discordid != -1: # attempt to link discordid to uid
            res = app.redis.get(f"umap:discordid={discordid}")
            if res:
                uid = int(res)
        if uid != -1:
            ret = app.redis.hgetall(f"uinfo:{uid}")
            if ret:
                ret["uid"] = int(ret["uid"])
                ret["userid"] = int(ret["userid"])
                ret["mfa"] = bool(ret["mfa"])
                ret["roles"] = str2list(ret["roles"])
                ret["join_timestamp"] = int(ret["join_timestamp"])

                if ret["userid"] == -1:
                    ret["userid"] = None
                for x in ["email", "discordid", "steamid", "truckersmpid"]:
                    if ret[x] == "":
                        ret[x] = None
                    elif x == "truckersmpid":
                        ret[x] = int(ret[x])

                app.redis.expire(f"uinfo:{uid}", 60) # refresh cache
                if ret["userid"]:
                    app.redis.set(f"umap:userid={ret['userid']}", uid)
                    app.redis.expire(f"umap:userid={ret['userid']}", 60)
                if ret["discordid"]:
                    app.redis.set(f"umap:discordid={ret['discordid']}", uid)
                    app.redis.expire(f"umap:discordid={ret['discordid']}", 60)

                privacy = await GetUserPrivacy(request, uid)

                if ignore_activity:
                    ret["activity"] = None
                else:
                    activity = app.redis.hgetall(f"uactivity:{uid}")
                    if activity:
                        if "error" in activity.keys(): # error: no data
                            ret["activity"] = None
                        else:
                            ret["activity"] = {"status": activity["status"], "last_seen": int(activity["last_seen"])}
                    else:
                        await app.db.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
                        ac = await app.db.fetchall(dhrid)
                        if len(ac) != 0:
                            if int(time.time()) - ac[0][1] >= 300:
                                ret["activity"] = {"status": "offline", "last_seen": ac[0][1]}
                            elif int(time.time()) - ac[0][1] >= 120:
                                ret["activity"] = {"status": "online", "last_seen": ac[0][1]}
                            else:
                                ret["activity"] = {"status": ac[0][0], "last_seen": ac[0][1]}
                            app.redis.hset(f"uactivity:{uid}", mapping = ret["activity"])
                        else:
                            app.redis.hset(f"uactivity:{uid}", mapping = {"error": "no data"})
                        app.redis.expire(f"uactivity:{uid}", 60)

                if request_uid is not None:
                    ret["note"] = await GetUserNote(request, request_uid, uid)
                if not include_sensitive:
                    ret["mfa"] = None
                if not include_global_note:
                    ret["global_note"] = None
                if privacy["public_profile"] and not is_member:
                    ret["name"] = None
                    ret["avatar"] = None
                    ret["bio"] = None
                    ret["roles"] = None
                    ret["join_timestamp"] = None
                    privacy["email"] = True
                    privacy["account_connections"] = True
                    privacy["activity"] = True
                if privacy["email"] and not include_sensitive:
                    ret["email"] = None
                if privacy["account_connections"] and not include_sensitive:
                    ret["discordid"] = None
                    ret["steamid"] = None
                    ret["truckersmpid"] = None
                if privacy["activity"] and not include_sensitive:
                    ret["activity"] = {"status": "offline", "last_seen": 0}
                return ret

    privacy = await GetUserPrivacy(request, uid)

    query = ""
    if userid != -1:
        query = f"userid = {userid}"
    elif discordid != -1:
        query = f"discordid = {discordid}"
    elif uid != -1:
        query = f"uid = {uid}"

    await app.db.execute(dhrid, f"SELECT uid, userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, mfa_secret, join_timestamp, tracker_in_use FROM user WHERE {query}")
    p = await app.db.fetchall(dhrid)
    if len(p) == 0:
        uid = None if uid == -1 else uid
        userid = None if userid == -1 else userid
        discordid = None if discordid == -1 else discordid
        if not tell_deleted:
            return {"uid": uid, "userid": userid, "name": ml.tr(request, "unknown"), "email": None, "discordid": nstr(discordid), "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None}
        else:
            return {"uid": uid, "userid": userid, "name": ml.tr(request, "unknown"), "email": None, "discordid": nstr(discordid), "steamid": None, "truckersmpid": None, "tracker": None, "avatar": None, "bio": None, "note": "", "global_note": None, "roles": [], "activity": None, "mfa": None, "join_timestamp": None, "is_deleted": True}

    uid = p[0][0]

    roles = str2list(p[0][6])
    mfa_secret = p[0][10]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True

    global_note = await GetUserNote(request, -1000, uid)

    activity = None
    if not ignore_activity:
        activity = app.redis.hgetall(f"uactivity:{uid}")
        if activity:
            if "error" in activity.keys(): # error: no data
                activity = None
            else:
                activity = {"status": activity["status"], "last_seen": int(activity["last_seen"])}
        else:
            await app.db.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
            ac = await app.db.fetchall(dhrid)
            if len(ac) != 0:
                if int(time.time()) - ac[0][1] >= 300:
                    activity = {"status": "offline", "last_seen": ac[0][1]}
                elif int(time.time()) - ac[0][1] >= 120:
                    activity = {"status": "online", "last_seen": ac[0][1]}
                else:
                    activity = {"status": ac[0][0], "last_seen": ac[0][1]}
                app.redis.hset(f"uactivity:{uid}", mapping = activity)
            else:
                app.redis.hset(f"uactivity:{uid}", mapping = {"error": "no data"})
            app.redis.expire(f"uactivity:{uid}", 60)

    if p[0][1] not in [-1, None]:
        app.redis.set(f"umap:userid={p[0][1]}", uid)
        app.redis.expire(f"umap:userid={p[0][1]}", 60)
    if p[0][7] not in [-1, None]:
        app.redis.set(f"umap:discordid={p[0][7]}", uid)
        app.redis.expire(f"umap:discordid={p[0][7]}", 60)

    userid = p[0][1]
    if userid == -1:
        userid = None

    tracker = "unknown"
    if p[0][12] == 2:
        tracker = "tracksim"
    elif p[0][12] == 3:
        tracker = "trucky"
    elif p[0][12] == 4:
        tracker = "custom"

    ret = {"uid": uid, "userid": userid, "name": p[0][2], "email": p[0][3], "discordid": nstr(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "tracker": tracker, "avatar": p[0][4], "bio": b64d(p[0][5]), "note": "", "global_note": global_note, "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}

    app.redis.hset(f"uinfo:{uid}", mapping = {"uid": uid, "userid": userid if userid is not None else -1, "name": p[0][2], "email": p[0][3] if p[0][3] is not None else "", "discordid": p[0][7] if p[0][7] is not None else "", "steamid": p[0][8] if p[0][8] is not None else "", "truckersmpid": p[0][9] if p[0][9] is not None else "", "tracker": tracker, "avatar": p[0][4], "bio": b64d(p[0][5]), "note": "", "global_note": global_note, "roles": list2str(roles), "activity": "", "mfa": int(mfa_enabled), "join_timestamp": p[0][11]})
    app.redis.expire(f"uinfo:{uid}", 60)

    if request_uid is not None:
        ret["note"] = await GetUserNote(request, request_uid, uid)

    if privacy["public_profile"] and not is_member:
        ret["name"] = None
        ret["avatar"] = None
        ret["bio"] = None
        ret["roles"] = None
        ret["join_timestamp"] = None
        privacy["email"] = True
        privacy["account_connections"] = True
        privacy["activity"] = True
    if not include_sensitive:
        ret["mfa"] = None
    if not include_global_note:
        ret["global_note"] = None
    if privacy["email"] and not include_sensitive:
        ret["email"] = None
    if privacy["account_connections"] and not include_sensitive:
        ret["discordid"] = None
        ret["steamid"] = None
        ret["truckersmpid"] = None
    if privacy["activity"] and not include_sensitive:
        ret["activity"] = {"status": "offline", "last_seen": 0}

    return ret

async def UpdateRoleConnection(request, discordid):
    (app, dhrid) = (request.app, request.state.dhrid)

    if discordid is None:
        return

    userinfo = await GetUserInfo(request, discordid = discordid)
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

async def GetPoints(request, userid, point_types = ["distance", "challenge", "division", "event", "bonus"]):
    (app, dhrid) = (request.app, request.state.dhrid)

    # handle bonus point on different rank
    ratio = 1
    if app.config.distance_unit == "imperial":
        ratio = 0.621371

    # calculate distance
    userdistance = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(distance) FROM dlog WHERE userid = {userid} GROUP BY userid")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        if tt[0] not in userdistance.keys():
            userdistance[tt[0]] = nint(tt[1])
        else:
            userdistance[tt[0]] += nint(tt[1])
        userdistance[tt[0]] = round(userdistance[tt[0]])

    # calculate challenge
    userchallenge = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid = {userid} GROUP BY userid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if oo[0] not in userchallenge.keys():
            userchallenge[oo[0]] = 0
        userchallenge[oo[0]] += oo[1]

    # calculate event
    userevent = {}
    await app.db.execute(dhrid, f"SELECT attendee, points FROM event WHERE attendee LIKE '%,{userid},%'")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        attendees = str2list(tt[0])
        for attendee in attendees:
            if attendee not in userevent.keys():
                userevent[attendee] = tt[1]
            else:
                userevent[attendee] += tt[1]

    # calculate division
    userdivision = {}
    await app.db.execute(dhrid, f"SELECT dlog.userid, division.divisionid, COUNT(dlog.distance), SUM(dlog.distance) \
        FROM dlog \
        INNER JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        WHERE dlog.logid >= 0 AND dlog.userid = {userid} \
        GROUP BY dlog.userid, division.divisionid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if oo[0] not in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in app.division_points.keys():
            if app.division_points[oo[1]]["mode"] == "static":
                userdivision[oo[0]] += oo[2] * app.division_points[oo[1]]["value"]
            elif app.division_points[oo[1]]["mode"] == "ratio":
                userdivision[oo[0]] += oo[3] * app.division_points[oo[1]]["value"]
    for (key, item) in userdivision.items():
        userdivision[key] = int(item)

    # calculate bonus
    userbonus = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(point) FROM bonus_point WHERE userid = {userid} GROUP BY userid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if oo[0] not in userbonus.keys():
            userbonus[oo[0]] = 0
        userbonus[oo[0]] += oo[1]

    distancepnt = 0
    challengepnt = 0
    eventpnt = 0
    divisionpnt = 0
    bonuspnt = 0
    if userid in userdistance.keys() and "distance" in point_types:
        distancepnt = userdistance[userid]
    if userid in userchallenge.keys() and "challenge" in point_types:
        challengepnt = userchallenge[userid]
    if userid in userevent.keys() and "event" in point_types:
        eventpnt = userevent[userid]
    if userid in userdivision.keys() and "division" in point_types:
        divisionpnt = userdivision[userid]
    if userid in userbonus.keys() and "bonus" in point_types:
        bonuspnt = userbonus[userid]

    totalpnt = round(distancepnt * ratio) + round(challengepnt) + round(eventpnt) + round(divisionpnt) + round(bonuspnt)

    return totalpnt
