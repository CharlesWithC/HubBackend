# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import ipaddress
import time

from fastapi.responses import JSONResponse

import multilang as ml
from functions.dataop import *
from functions.general import *
from functions.iptype import *
from static import *


def checkPerm(app, roles, perms):
    '''`perms` is "or"-based, aka matching any `perms` will return `True`.'''
    if type(perms) == str:
        perms = [perms]
    for role in roles:
        for perm in perms:
            if perm in app.config.__dict__["perms"].__dict__.keys() and role in app.config.__dict__["perms"].__dict__[perm]:
                return True
    return False

# app.redit.hgetall("auth:{authorization_key}") <= app.state.cache_session(_extended)
# app.state.cache_ratelimit = {}

async def ratelimit(request, endpoint, limittime, limitcnt, cGlobalOnly = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    # identifier is precise and will be stored in database
    # cidentifier is a worker-level identifier stored in memory to prevent excessive amount of traffic
    # cidentifier will only handle global ratelimit
    cidentifier = f"ip/{request.client.host}"
    if "authorization" in request.headers.keys():
        authorization = request.headers["authorization"]
        authorization_key = f"{authorization[0].upper()}-{authorization.split(' ')[1].replace('-','')}"
        uid = app.redis.hget(f"auth:{authorization_key}", "uid")
        if uid:
            cidentifier = f"uid/{uid}"

    # whitelist ip (only active when request is not authed)
    if cidentifier.startswith("ip") and request.client.host in app.config.whitelist_ips:
        return (False, {})

    # check ratelimit in memory
    k = list(app.state.cache_ratelimit.keys())
    for i in k:
        for j in range(len(app.state.cache_ratelimit[i])):
            try:
                if app.state.cache_ratelimit[i][j] < time.time() - 60:
                    del app.state.cache_ratelimit[i][j]
            except:
                pass
    if cidentifier in app.state.cache_ratelimit.keys():
        app.state.cache_ratelimit[cidentifier].append(int(time.time()))
        if len(app.state.cache_ratelimit[cidentifier]) >= 300:
            try:
                del app.state.cache_ratelimit[cidentifier][1:(len(app.state.cache_ratelimit[cidentifier])-299)]
            except:
                pass
            # global ratelimit active
            maxban = app.state.cache_ratelimit[cidentifier][0] + 600
            resp_headers = {}
            resp_headers["Retry-After"] = str(maxban - int(time.time()))
            resp_headers["X-RateLimit-Limit"] = str(limitcnt)
            resp_headers["X-RateLimit-Remaining"] = str(0)
            resp_headers["X-RateLimit-Reset"] = str(maxban)
            resp_headers["X-RateLimit-Reset-After"] = str(maxban - int(time.time()))
            resp_headers["X-RateLimit-Global"] = "true"
            resp_content = {"error": ml.tr(request, "rate_limit"), \
                "retry_after": str(maxban - int(time.time())), "global": True}
            return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    else:
        app.state.cache_ratelimit[cidentifier] = [int(time.time())]

    # only check cached global ratelimit, used by middleware
    if cGlobalOnly:
        return (False, {})

    identifier = f"ip/{request.client.host}"
    if "authorization" in request.headers.keys():
        authorization = request.headers["authorization"]
        au = await auth(authorization, request, check_member=False)
        if not au["error"]:
            identifier = f"uid/{au['uid']}"

    # whitelist ip (only active when request is not authed)
    if identifier.startswith("ip") and request.client.host in app.config.whitelist_ips:
        return (False, {})

    # check global ratelimit
    await app.db.execute(dhrid, f"SELECT first_request_timestamp, endpoint FROM ratelimit WHERE identifier = '{identifier}' AND endpoint LIKE 'global-ban-%'")
    t = await app.db.fetchall(dhrid)
    maxban = 0
    for tt in t:
        frt = tt[0]
        bansec = int(tt[1].split("-")[-1])
        maxban = max(frt + bansec, maxban)
        if maxban < time.time():
            # global ratelimit expired
            await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE identifier = '{identifier}' AND endpoint = 'global-ban-{bansec}'")
            await app.db.commit(dhrid)
            maxban = 0
    if maxban > 0:
        # global ratelimit active
        resp_headers = {}
        resp_headers["Retry-After"] = str(maxban - int(time.time()))
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(maxban)
        resp_headers["X-RateLimit-Reset-After"] = str(maxban - int(time.time()))
        resp_headers["X-RateLimit-Global"] = "true"
        resp_content = {"error": ml.tr(request, "rate_limit"), \
            "retry_after": str(maxban - int(time.time())), "global": True}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))

    # check route ratelimit
    await app.db.execute(dhrid, f"SELECT SUM(request_count) FROM ratelimit WHERE identifier = '{identifier}' AND first_request_timestamp > {int(time.time() - 60)}")
    t = await app.db.fetchall(dhrid)
    if t[0][0] is not None and t[0][0] > 300:
        # more than 300r/m combined
        # including 429 requests
        # 10min global ratelimit
        await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE identifier = '{identifier}' AND endpoint = 'global-ban-600'")
        await app.db.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{identifier}', 'global-ban-600', {int(time.time())}, 0)")
        await app.db.commit(dhrid)
        resp_headers = {}
        resp_headers["Retry-After"] = str(600)
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + 600)
        resp_headers["X-RateLimit-Reset-After"] = str(600)
        resp_headers["X-RateLimit-Global"] = "true"
        resp_content = {"error": ml.tr(request, "rate_limit"), \
            "retry_after": "600", "global": True}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))

    await app.db.execute(dhrid, f"SELECT first_request_timestamp, request_count FROM ratelimit WHERE identifier = '{identifier}' AND endpoint = '{endpoint}'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{identifier}', '{endpoint}', {int(time.time())}, 1)")
        await app.db.commit(dhrid)
        resp_headers = {}
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
        resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
        resp_headers["X-RateLimit-Reset-After"] = str(limittime)
        return (False, resp_headers)
    else:
        first_request_timestamp = t[0][0]
        request_count = t[0][1]
        if int(time.time()) - first_request_timestamp > limittime:
            await app.db.execute(dhrid, f"UPDATE ratelimit SET first_request_timestamp = {int(time.time())}, request_count = 1 WHERE identifier = '{identifier}' AND endpoint = '{endpoint}'")
            await app.db.commit(dhrid)
            resp_headers = {}
            resp_headers["X-RateLimit-Limit"] = str(limitcnt)
            resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
            resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
            resp_headers["X-RateLimit-Reset-After"] = str(limittime)
            return (False, resp_headers)
        else:
            if request_count + 1 > limitcnt:
                await app.db.execute(dhrid, f"SELECT request_count FROM ratelimit WHERE identifier = '{identifier}' AND endpoint = '429-error'")
                t = await app.db.fetchall(dhrid)
                if len(t) > 0:
                    await app.db.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE identifier = '{identifier}' AND endpoint = '429-error'")
                    await app.db.commit(dhrid)
                else:
                    await app.db.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{identifier}', '429-error', {int(time.time())}, 1)")
                    await app.db.commit(dhrid)

                retry_after = limittime - (int(time.time()) - first_request_timestamp)
                resp_headers = {}
                resp_headers["Retry-After"] = str(retry_after)
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(0)
                resp_headers["X-RateLimit-Reset"] = str(retry_after + int(time.time()))
                resp_headers["X-RateLimit-Reset-After"] = str(retry_after)
                resp_headers["X-RateLimit-Global"] = "false"
                resp_content = {"error": ml.tr(request, "rate_limit"), \
                    "retry_after": str(retry_after), "global": False}
                return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
            else:
                await app.db.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE identifier = '{identifier}' AND endpoint = '{endpoint}'")
                await app.db.commit(dhrid)
                resp_headers = {}
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(limitcnt - request_count - 1)
                resp_headers["X-RateLimit-Reset"] = str(first_request_timestamp + limittime)
                resp_headers["X-RateLimit-Reset-After"] = str(limittime - (int(time.time()) - first_request_timestamp))
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

    auth_cache = app.redis.hgetall(f"auth:{authorization_key}")

    # application token
    if tokentype == "Application":
        # check if allowed
        if not allow_application_token:
            return {"error": ml.tr(request, "application_token_not_allowed"), "code": 401}

        if not auth_cache:
            # validate token if there's no cache
            await app.db.execute(dhrid, f"SELECT uid, last_used_timestamp FROM application_token WHERE token = '{stoken}'")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            uid = t[0][0]
            last_used_timestamp = t[0][1]

            # application token will skip ip / country check

            # get user info
            await app.db.execute(dhrid, f"SELECT userid, discordid, roles, name, avatar FROM user WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            userid = t[0][0]
            discordid = t[0][1]
            roles = str2list(t[0][2])
            name = t[0][3]
            avatar = t[0][4]

            await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
            t = await app.db.fetchall(dhrid)
            language = ""
            if len(t) != 0:
                language = t[0][0]

            # write cache
            app.redis.hset(f"auth:{authorization_key}", mapping = {"uid": uid, "userid": userid, "discordid": discordid, "name": name, "avatar": avatar, "roles": list2str(roles), "language": language, "last_used_timestamp": int(time.time())})
        else:
            # use cache if available
            uid = int(auth_cache["uid"])
            userid = int(auth_cache["userid"])
            discordid = int(auth_cache["discordid"])
            name = auth_cache["name"]
            avatar = auth_cache["avatar"]
            roles = str2list(auth_cache["roles"])
            language = auth_cache["language"]
            last_used_timestamp = int(auth_cache["last_used_timestamp"])

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
            await app.db.execute(dhrid, f"UPDATE application_token SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await app.db.commit(dhrid)

            # update last_used_timestamp in cache
            app.redis.hset(f"auth:{authorization_key}", "last_used_timestamp", int(time.time()))

        # update expire time
        app.redis.expire(f"auth:{authorization_key}", 60)

        return {"error": False, "uid": uid, "userid": userid, "discordid": discordid, "name": name, "avatar": avatar, "roles": roles, "language": language, "application_token": True}

    # bearer token
    elif tokentype == "Bearer":
        curCountry = getRequestCountry(request, abbr = True)

        if not auth_cache:
            # validate token if there's no cache
            await app.db.execute(dhrid, f"SELECT uid, ip, country, last_used_timestamp, user_agent FROM session WHERE token = '{stoken}'")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            uid = t[0][0]
            ip = t[0][1]
            country = t[0][2]
            last_used_timestamp = t[0][3]
            user_agent = t[0][4]

            # get user info
            await app.db.execute(dhrid, f"SELECT userid, discordid, roles, name, avatar FROM user WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                return {"error": ml.tr(request, "unauthorized"), "code": 401}
            userid = t[0][0]
            discordid = t[0][1]
            roles = str2list(t[0][2])
            name = t[0][3]
            avatar = t[0][4]

            await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'language'")
            t = await app.db.fetchall(dhrid)
            language = ""
            if len(t) != 0:
                language = t[0][0]

            # write cache
            # we'll use the curCountry rather than the country from db
            # because if it won't work the cache will be directly deleted
            app.redis.hset(f"auth:{authorization_key}", mapping = {"uid": uid, "userid": userid, "discordid": discordid, "name": name, "avatar": avatar, "roles": list2str(roles), "language": language, "last_used_timestamp": int(time.time()), "country": curCountry, "ip": request.client.host, "user_agent": getUserAgent(request)})
        else:
            # use cache if available
            uid = int(auth_cache["uid"])
            userid = int(auth_cache["userid"])
            discordid = int(auth_cache["discordid"])
            name = auth_cache["name"]
            avatar = auth_cache["avatar"]
            roles = str2list(auth_cache["roles"])
            language = auth_cache["language"]
            last_used_timestamp = int(auth_cache["last_used_timestamp"])
            country = auth_cache["country"]
            ip = auth_cache["ip"]
            user_agent = auth_cache["user_agent"]

        # check country
        if app.config.security_level >= 1 and request.client.host not in app.config.whitelist_ips:
            if curCountry != country and country != "":
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
                            await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                            await app.db.commit(dhrid)
                            app.redis.delete(f"auth:{authorization_key}")
                            return {"error": ml.tr(request, "unauthorized"), "code": 401}
                    elif curiptype == 4:
                        if ip.split(".")[:3] != request.client.host.split(".")[:3]:
                            await app.db.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                            await app.db.commit(dhrid)
                            app.redis.delete(f"auth:{authorization_key}")
                            return {"error": ml.tr(request, "unauthorized"), "code": 401}

        if request.client.host not in app.config.whitelist_ips:
            if ip != request.client.host:
                await app.db.execute(dhrid, f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            if curCountry != country:
                await app.db.execute(dhrid, f"UPDATE session SET country = '{curCountry}' WHERE token = '{stoken}'")
            if getUserAgent(request) != user_agent:
                await app.db.execute(dhrid, f"UPDATE session SET user_agent = '{getUserAgent(request)}' WHERE token = '{stoken}'")
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
            app.redis.hset(f"auth:{authorization_key}", "last_used_timestamp", int(time.time()))

        # update expire time
        app.redis.expire(f"auth:{authorization_key}", 60)

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
