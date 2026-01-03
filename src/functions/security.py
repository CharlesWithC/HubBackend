# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import ipaddress
import time

from fastapi.responses import JSONResponse

import multilang as ml
from functions.dataop import *
from functions.general import *
from functions.iptype import *
from static import *

# redis auth:{authorization_token} <= app.state.cache_session(_extended)
# redis ratelimit:{identifier} <= app.state.cache_ratelimit = {}

def checkPerm(app, roles, perms):
    '''`perms` is "or"-based, aka matching any `perms` will return `True`.'''
    if type(perms) == str:
        perms = [perms]
    for role in roles:
        for perm in perms:
            if perm in app.config.__dict__["perms"].__dict__.keys() and role in app.config.__dict__["perms"].__dict__[perm]:
                return True
    return False

async def ratelimit(request, endpoint, limittime, limitcnt, cGlobalOnly = False):
    app = request.app
    cur_time = time.time()

    # identifier is precise and will be stored in database
    # cidentifier is a worker-level identifier stored in memory to prevent excessive amount of traffic
    # cidentifier will only handle global ratelimit
    cidentifier = f"ip/{request.client.host}"
    if "authorization" in request.headers.keys():
        authorization = request.headers["authorization"]
        if len(authorization.split(" ")) < 2:
            return (True, JSONResponse(content = {"error": ml.tr(request, "invalid_authorization_token")}, status_code = 401))
        authorization_key = f"{authorization[0].upper()}-{authorization.split(' ')[1].replace('-','')}"
        uid = app.redis.hget(f"auth:{authorization_key}", "uid")
        if uid:
            cidentifier = f"uid/{uid}"
    rlkey = f"ratelimit:{cidentifier}"

    # whitelist ip (only active when request is not authed)
    if cidentifier.startswith("ip") and request.client.host in app.config.whitelist_ips:
        return (False, {})

    # check in-memory global ratelimit (300req/min)
    # since ratelimit runs before auth, when the first request is finished,
    # identifier will change from ip to uid, thus global limit will only be handled here
    reqcnt = app.redis.zcard(rlkey)
    zr = app.redis.zrange(rlkey, 0, 0, withscores=True)
    firstreq = cur_time if not zr else zr[0][1]

    lastsec = app.redis.zcount(rlkey, cur_time - 1, '+inf')
    if lastsec >= 20:
        # more than 20 req on the same route within 1 second => 1-second-ban
        resp_headers = {}
        resp_headers["Retry-After"] = str(1)
        resp_headers["X-RateLimit-Limit"] = str(15)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(round(cur_time + 1, 3))
        resp_headers["X-RateLimit-Reset-After"] = str(1)
        resp_content = {"error": ml.tr(request, "rate_limit"), \
            "retry_after": round(cur_time + 1, 3), "global": False}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    elif lastsec >= 10:
        await asyncio.sleep(0.1)
        # sleep 0.1 sec when more than 10 req on the same route is received to protect database

    app.redis.zadd(rlkey, {f"g{cur_time}": cur_time})
    app.redis.expire(rlkey, 600)

    if reqcnt >= 300 and firstreq + 600 >= cur_time:
        # more than 300req within 1 min AND it's less than 10min from 1st req
        # global ratelimit active
        if reqcnt >= 305:
            app.redis.zpopmin(rlkey)
        resp_headers = {}
        resp_headers["Retry-After"] = str(round(firstreq + 600 - cur_time, 3))
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(round(firstreq + 600, 3))
        resp_headers["X-RateLimit-Reset-After"] = str(round(firstreq + 600 - cur_time, 3))
        resp_headers["X-RateLimit-Global"] = "true"
        resp_content = {"error": ml.tr(request, "rate_limit"), \
            "retry_after": round(firstreq + 600 - cur_time, 3), "global": True}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    else:
        app.redis.zremrangebyscore(rlkey, "-inf", f"{cur_time - 60}")

    # only check cached global ratelimit, used by middleware
    if cGlobalOnly:
        return (False, {})

    # precise identifier for route ratelimit
    identifier = f"ip/{request.client.host}"
    if "authorization" in request.headers.keys():
        authorization = request.headers["authorization"]
        au = await auth(authorization, request, check_member=False)
        if not au["error"]:
            identifier = f"uid/{au['uid']}"
    rlkey = f"ratelimit:{identifier}:{endpoint}"

    # whitelist ip (only active when request is not authed)
    if identifier.startswith("ip") and request.client.host in app.config.whitelist_ips:
        return (False, {})

    # check route ratelimit
    reqcnt = app.redis.zcard(rlkey)
    zr = app.redis.zrange(rlkey, 0, 0, withscores=True)
    firstreq = cur_time if not zr else zr[0][1]

    app.redis.zadd(rlkey, {f"r{cur_time}": cur_time})
    app.redis.expire(rlkey, limittime)

    if reqcnt >= limitcnt and firstreq + limittime >= cur_time:
        # more than limitcnt within limittime AND it's less than limittime from 1st req
        # route ratelimit active
        if reqcnt >= limitcnt + 5:
            app.redis.zpopmin(rlkey)
        resp_headers = {}
        resp_headers["Retry-After"] = str(round(firstreq + limittime - cur_time, 3))
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(round(firstreq + limittime, 3))
        resp_headers["X-RateLimit-Reset-After"] = str(round(firstreq + limittime - cur_time, 3))
        resp_content = {"error": ml.tr(request, "rate_limit"), \
            "retry_after": round(firstreq + limittime - cur_time, 3), "global": False}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    else:
        app.redis.zremrangebyscore(rlkey, "-inf", f"{cur_time - limittime}")

        resp_headers = {}
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(limitcnt - reqcnt - 1)
        resp_headers["X-RateLimit-Reset"] = str(round(firstreq + limittime, 3))
        resp_headers["X-RateLimit-Reset-After"] = str(round(firstreq + limittime - cur_time, 3))
        return (False, resp_headers)

async def auth(authorization, request, allow_application_token = False, check_member = True, required_permission = [], only_validate_token = False, only_use_cache = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    # authorization header basic check
    if authorization is None or authorization == "" or len(authorization.split(" ")) < 2:
        return {"error": ml.tr(request, "invalid_authorization_token"), "code": 401}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        return {"error": ml.tr(request, "unknown_authorization_token_type"), "code": 401}

    tokentype = authorization.split(" ")[0].lower().title()
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": ml.tr(request, "invalid_authorization_token"), "code": 401}
    authorization = f"{tokentype} {stoken}"
    authorization_key = f"{tokentype[0]}-{stoken.replace('-','')}" # for redis

    if only_validate_token and app.redis.exists(f"auth:{authorization_key}"):
        return {"error": False}
    if only_use_cache and not app.redis.exists(f"auth:{authorization_key}"):
        return {"error": ml.tr(request, "unauthorized"), "code": 401}

    # do not extend because it can lead to data hanging in cache
    # app.redis.expire(f"auth:{authorization_key}", 60)
    auth_cache = app.redis.hgetall(f"auth:{authorization_key}")

    async def get_user_info(uid):
        # these data are available to admin
        # language is excluded as we are keeping it private

        (app, dhrid) = (request.app, request.state.dhrid)

        await app.db.execute(dhrid, f"SELECT userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, mfa_secret, join_timestamp, tracker_in_use FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            return {"error": ml.tr(request, "unauthorized"), "code": 401}

        global_note = ""
        await app.db.execute(dhrid, f"SELECT note FROM user_note WHERE from_uid = -1000 AND to_uid = {uid}")
        un = await app.db.fetchall(dhrid)
        if len(un) != 0:
            global_note = un[0][0]

        tracker = "unknown"
        if t[0][11] == 2:
            tracker = "tracksim"
        elif t[0][11] == 3:
            tracker = "trucky"
        elif t[0][11] == 4:
            tracker = "custom"
        elif t[0][11] == 5:
            tracker = "unitracker"

        mfa_enabled = 0
        if t[0][9] != "":
            mfa_enabled = 1

        app.redis.hset(f"uinfo:{uid}", mapping = {"uid": uid, "userid": t[0][0], "name": t[0][1], "email": t[0][2] if t[0][2] is not None else "", "discordid": t[0][6] if t[0][6] is not None else "", "steamid": t[0][7] if t[0][7] is not None else "", "truckersmpid": t[0][8] if t[0][8] is not None else "", "tracker": tracker, "avatar": t[0][3], "bio": b64d(t[0][4]), "note": "", "global_note": global_note, "roles": t[0][5], "activity": "", "mfa": mfa_enabled, "join_timestamp": t[0][10]})
        app.redis.expire(f"uinfo:{uid}", 60)

        return {"uid": uid, "userid": t[0][0], "name": t[0][1], "email": t[0][2], "discordid": t[0][6], "steamid": t[0][7], "truckersmpid": t[0][8], "tracker": tracker, "avatar": t[0][3], "bio": b64d(t[0][4]), "note": "", "global_note": global_note, "roles": str2list(t[0][5]), "activity": "", "mfa": TF[mfa_enabled], "join_timestamp": t[0][10]}

    # application token
    if tokentype == "Application":
        # check if allowed
        if not allow_application_token:
            return {"error": ml.tr(request, "application_token_not_allowed"), "code": 401}

        if not auth_cache or "uid" not in auth_cache.keys():
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            # validate token if there's no cache
            await app.db.execute(dhrid, f"SELECT uid, last_used_timestamp FROM application_token WHERE token = '{stoken}'")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            uid = t[0][0]
            last_used_timestamp = t[0][1]

            app.redis.hset(f"auth:{authorization_key}", mapping = {"uid": uid, "last_used_timestamp": int(time.time())})
        else:
            uid = int(auth_cache["uid"])
            last_used_timestamp = int(auth_cache["last_used_timestamp"])

        # application token will skip ip / country check

        user_cache = app.redis.hgetall(f"uinfo:{uid}")
        if not user_cache or "uid" not in user_cache.keys():
            # get user info
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            userinfo = await get_user_info(uid)
            if "error" in userinfo:
                return userinfo
            else:
                userid = userinfo["userid"]
                discordid = userinfo["discordid"]
                name = userinfo["name"]
                avatar = userinfo["avatar"]
                roles = userinfo["roles"]
        else:
            userid = int(user_cache["userid"]) # cached userid is always a valid stringified int
            discordid = nint(user_cache["discordid"]) # cached discordid may be "" if not exist
            name = user_cache["name"]
            avatar = user_cache["avatar"]
            roles = str2list(user_cache["roles"])

        # get user language
        language = app.redis.get(f"ulang:{uid}")
        if not language:
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
            t = await app.db.fetchall(dhrid)
            language = ""
            if len(t) != 0:
                language = t[0][0]

            app.redis.set(f"ulang:{uid}", language)
            app.redis.expire(f"ulang:{uid}", 60)

        # check accesss
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": ml.tr(request, "no_access_to_resource"), "code": 403}

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False
            for role in roles:
                for perm in required_permission:
                    if perm in app.config.__dict__["perms"].__dict__.keys() and role in app.config.__dict__["perms"].__dict__[perm] or role in app.config.__dict__["perms"].__dict__["administrator"]:
                        ok = True

            if not ok:
                return {"error": ml.tr(request, "no_access_to_resource"), "code": 403}

        # update last used timestamp
        if int(time.time()) - last_used_timestamp >= 5:
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            await app.db.execute(dhrid, f"UPDATE application_token SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await app.db.commit(dhrid)

            # update last_used_timestamp in cache
            app.redis.hset(f"auth:{authorization_key}", mapping = {"last_used_timestamp": int(time.time())})
            app.redis.expire(f"auth:{authorization_key}", 60)

        return {"error": False, "uid": uid, "userid": userid, "discordid": discordid, "name": name, "avatar": avatar, "roles": roles, "language": language, "application_token": True}

    # bearer token
    elif tokentype == "Bearer":
        curCountry = getRequestCountry(request, abbr = True)

        if not auth_cache or "uid" not in auth_cache.keys():
            # validate token if there's no cache
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            await app.db.execute(dhrid, f"SELECT uid, ip, country, last_used_timestamp, user_agent FROM session WHERE token = '{stoken}'")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            uid = t[0][0]
            ip = t[0][1]
            country = t[0][2]
            last_used_timestamp = t[0][3]
            user_agent = t[0][4]

            app.redis.hset(f"auth:{authorization_key}", mapping = {"uid": uid, "last_used_timestamp": int(time.time()), "country": curCountry, "ip": request.client.host, "user_agent": getUserAgent(request)})
            app.redis.expire(f"auth:{authorization_key}", 60)
        else:
            uid = int(auth_cache["uid"])
            country = auth_cache["country"]
            ip = auth_cache["ip"]
            user_agent = auth_cache["user_agent"]
            last_used_timestamp = int(auth_cache["last_used_timestamp"])

        user_cache = app.redis.hgetall(f"uinfo:{uid}")
        if not user_cache or "uid" not in user_cache.keys():
            # get user info
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            userinfo = await get_user_info(uid)
            if "error" in userinfo.keys():
                return userinfo
            else:
                userid = userinfo["userid"]
                discordid = userinfo["discordid"]
                name = userinfo["name"]
                avatar = userinfo["avatar"]
                roles = userinfo["roles"]
        else:
            userid = int(user_cache["userid"]) # cached userid is always a valid stringified int
            discordid = nint(user_cache["discordid"]) # cached discordid may be "" if not exist
            name = user_cache["name"]
            avatar = user_cache["avatar"]
            roles = str2list(user_cache["roles"])

        language = app.redis.get(f"ulang:{uid}")
        if not language:
            await app.db.new_conn(dhrid, db_name = app.config.db_name)

            await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
            t = await app.db.fetchall(dhrid)
            language = ""
            if len(t) != 0:
                language = t[0][0]

            app.redis.set(f"ulang:{uid}", language)
            app.redis.expire(f"ulang:{uid}", 60)

        # check country
        if app.config.security_level >= 1 and request.client.host not in app.config.whitelist_ips:
            if curCountry != country and country != "":
                await app.db.new_conn(dhrid, db_name = app.config.db_name)
                await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                await app.db.commit(dhrid)
                app.redis.delete(f"auth:{authorization_key}")
                return {"error": ml.tr(request, "unauthorized"), "code": 401}

        if app.config.security_level >= 2 and request.client.host not in app.config.whitelist_ips:
            orgiptype = iptype(ip)
            if orgiptype != 0:
                curiptype = iptype(request.client.host)
                if orgiptype == curiptype:
                    if curiptype == 6:
                        curip = ipaddress.ip_address(request.client.host).exploded
                        orgip = ipaddress.ip_address(ip).exploded
                        if curip.split(":")[:4] != orgip.split(":")[:4]:
                            await app.db.new_conn(dhrid, db_name = app.config.db_name)
                            await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                            await app.db.commit(dhrid)
                            app.redis.delete(f"auth:{authorization_key}")
                            return {"error": ml.tr(request, "unauthorized"), "code": 401}
                    elif curiptype == 4:
                        if ip.split(".")[:3] != request.client.host.split(".")[:3]:
                            await app.db.new_conn(dhrid, db_name = app.config.db_name)
                            await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                            await app.db.commit(dhrid)
                            app.redis.delete(f"auth:{authorization_key}")
                            return {"error": ml.tr(request, "unauthorized"), "code": 401}

        if request.client.host not in app.config.whitelist_ips:
            cnt = 0
            if ip != request.client.host:
                await app.db.new_conn(dhrid, db_name = app.config.db_name)
                await app.db.execute(dhrid, f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                cnt += 1
            if curCountry != country:
                await app.db.new_conn(dhrid, db_name = app.config.db_name)
                await app.db.execute(dhrid, f"UPDATE session SET country = '{curCountry}' WHERE token = '{stoken}'")
                cnt += 1
            if getUserAgent(request) != user_agent:
                await app.db.new_conn(dhrid, db_name = app.config.db_name)
                await app.db.execute(dhrid, f"UPDATE session SET user_agent = '{getUserAgent(request)}' WHERE token = '{stoken}'")
                cnt += 1
            if cnt > 0:
                await app.db.commit(dhrid)

            # update ip/country/user_agent in cache
            app.redis.hset(f"auth:{authorization_key}", mapping = {"ip": request.client.host, "country": curCountry, "user_agent": getUserAgent(request)})

        # check accesss
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": ml.tr(request, "no_access_to_resource"), "code": 403}

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False

            for role in roles:
                for perm in required_permission:
                    if perm in app.config.__dict__["perms"].__dict__.keys() and role in app.config.__dict__["perms"].__dict__[perm] or role in app.config.__dict__["perms"].__dict__["administrator"]:
                        ok = True

            if not ok:
                return {"error": ml.tr(request, "no_access_to_resource"), "code": 403}

        if int(time.time()) - last_used_timestamp >= 5:
            await app.db.new_conn(dhrid, db_name = app.config.db_name)
            await app.db.execute(dhrid, f"UPDATE session SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await app.db.commit(dhrid)
            await app.db.execute(dhrid, f"SELECT timestamp FROM user_activity WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                await app.db.execute(dhrid, f"UPDATE user_activity SET timestamp = {int(time.time())} WHERE uid = {uid}")
            else:
                await app.db.execute(dhrid, f"INSERT INTO user_activity VALUES ({uid}, 'online', {int(time.time())})")
            await app.db.commit(dhrid)

            # update last_used_timestamp in cache
            app.redis.hset(f"auth:{authorization_key}", mapping = {"last_used_timestamp": int(time.time())})

        return {"error": False, "uid": uid, "userid": userid, "discordid": discordid, "name": name, "avatar": avatar, "roles": roles, "language": language, "application_token": False}

    return {"error": ml.tr(request, "unauthorized"), "code": 401}

async def isSecureAuth(authorization, request):
    (app, dhrid) = (request.app, request.state.dhrid)
    stoken = authorization.split(" ")[1]
    if not stoken.startswith("e"):
        return True

    au = await auth(authorization, request, check_member=False)
    if au["error"]:
        return False
    uid = au["uid"]

    await app.db.execute(dhrid, f"SELECT discordid, steamid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return False
    if t[0][0] is None and t[0][1] is None:
        return True
    return False
