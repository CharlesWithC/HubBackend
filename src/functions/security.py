# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time

from fastapi.responses import JSONResponse

import multilang as ml
from app import config, tconfig
from db import aiosql
from functions.dataop import *
from functions.general import *
from static import *


async def ratelimit(dhrid, request, ip, endpoint, limittime, limitcnt):
    if request.client.host in config.whitelist_ips:
        return (False, {})
    await aiosql.execute(dhrid, f"SELECT first_request_timestamp, endpoint FROM ratelimit WHERE ip = '{ip}' AND endpoint LIKE 'ip-ban-%'")
    t = await aiosql.fetchall(dhrid)
    maxban = 0
    for tt in t:
        frt = tt[0]
        bansec = int(tt[1].split("-")[-1])
        maxban = max(frt + bansec, maxban)
        if maxban < int(time.time()):
            await aiosql.execute(dhrid, f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-{bansec}'")
            await aiosql.commit(dhrid)
            maxban = 0
    if maxban > 0:
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
    await aiosql.execute(dhrid, f"SELECT SUM(request_count) FROM ratelimit WHERE ip = '{ip}' AND first_request_timestamp > {int(time.time() - 60)}")
    t = await aiosql.fetchall(dhrid)
    if t[0][0] != None and t[0][0] > 150:
        # more than 150r/m combined
        # including 429 requests
        # 10min ip ban
        await aiosql.execute(dhrid, f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-600'")
        await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', 'ip-ban-600', {int(time.time())}, 0)")
        await aiosql.commit(dhrid)
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
    await aiosql.execute(dhrid, f"SELECT first_request_timestamp, request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', '{endpoint}', {int(time.time())}, 1)")
        await aiosql.commit(dhrid)
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
            await aiosql.execute(dhrid, f"UPDATE ratelimit SET first_request_timestamp = {int(time.time())}, request_count = 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
            await aiosql.commit(dhrid)
            resp_headers = {}
            resp_headers["X-RateLimit-Limit"] = str(limitcnt)
            resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
            resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
            resp_headers["X-RateLimit-Reset-After"] = str(limittime)
            return (False, resp_headers)
        else:
            if request_count + 1 > limitcnt:
                await aiosql.execute(dhrid, f"SELECT request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '429-error'")
                t = await aiosql.fetchall(dhrid)
                if len(t) > 0:
                    await aiosql.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '429-error'")
                    await aiosql.commit(dhrid)
                else:
                    await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', '429-error', {int(time.time())}, 1)")
                    await aiosql.commit(dhrid)

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
                await aiosql.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
                await aiosql.commit(dhrid)
                resp_headers = {}
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(limitcnt - request_count - 1)
                resp_headers["X-RateLimit-Reset"] = str(first_request_timestamp + limittime)
                resp_headers["X-RateLimit-Reset-After"] = str(limittime - (int(time.time()) - first_request_timestamp))
                return (False, resp_headers)

async def auth(dhrid, authorization, request, allow_application_token = False, check_member = True, required_permission = []):
    # authorization header basic check
    if authorization is None:
        return {"error": "Unauthorized", "code": 401}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        return {"error": "Unauthorized", "code": 401}
    
    tokentype = authorization.split(" ")[0]
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": "Unauthorized", "code": 401}

    # application token
    if tokentype.lower() == "application":
        # check if allowed
        if not allow_application_token:
            return {"error": ml.tr(request, "application_token_prohibited"), "code": 401}

        # validate token
        await aiosql.execute(dhrid, f"SELECT uid, last_used_timestamp FROM application_token WHERE token = '{stoken}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": "Unauthorized", "code": 401}
        uid = t[0][0]
        last_used_timestamp = t[0][1]

        # application token will skip ip check

        # additional check
        
        # this should not happen but just in case
        await aiosql.execute(dhrid, f"SELECT userid, discordid, roles, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": "Unauthorized", "code": 401}
        userid = t[0][0]
        discordid = t[0][1]
        roles = t[0][2].split(",")
        name = t[0][3]
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": "Unauthorized", "code": 401}

        roles = [int(x) for x in roles if isint(x)]

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": "Forbidden", "code": 403}

        if int(time.time()) - last_used_timestamp >= 5:
            await aiosql.execute(dhrid, f"UPDATE application_token SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await aiosql.commit(dhrid)

        await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'language'")
        t = await aiosql.fetchall(dhrid)
        language = ""
        if len(t) != 0:
            language = t[0][0]

        return {"error": False, "uid": uid, "userid": userid, "discordid": discordid, "name": name, "roles": roles, "language": language, "application_token": True}

    # bearer token
    elif tokentype.lower() == "bearer":
        await aiosql.execute(dhrid, f"SELECT uid, ip, country, last_used_timestamp, user_agent FROM session WHERE token = '{stoken}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": "Unauthorized", "code": 401}
        uid = t[0][0]
        ip = t[0][1]
        country = t[0][2]
        last_used_timestamp = t[0][3]
        user_agent = t[0][4]

        # check country
        if not request.client.host in config.whitelist_ips:
            curCountry = getRequestCountry(request, abbr = True)
            if curCountry != country and country != "":
                await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
                await aiosql.commit(dhrid)
                return {"error": "Unauthorized", "code": 401}

            if ip != request.client.host:
                await aiosql.execute(dhrid, f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
            if curCountry != country and not curCountry != "" and country != "":
                await aiosql.execute(dhrid, f"UPDATE session SET country = '{curCountry}' WHERE token = '{stoken}'")
            if getUserAgent(request) != user_agent:
                await aiosql.execute(dhrid, f"UPDATE session SET user_agent = '{getUserAgent(request)}' WHERE token = '{stoken}'")
            await aiosql.commit(dhrid)
        
        # additional check
        
        # this should not happen but just in case
        await aiosql.execute(dhrid, f"SELECT userid, discordid, roles, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": "Unauthorized", "code": 401}
        userid = t[0][0]
        discordid = t[0][1]
        roles = t[0][2].split(",")
        name = t[0][3]
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": "Unauthorized", "code": 401}

        roles = [int(x) for x in roles if isint(x)]

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False
            
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": "Forbidden", "code": 403}

        if int(time.time()) - last_used_timestamp >= 5:
            await aiosql.execute(dhrid, f"UPDATE session SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await aiosql.commit(dhrid)

        await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'language'")
        t = await aiosql.fetchall(dhrid)
        language = ""
        if len(t) != 0:
            language = t[0][0]
            
        return {"error": False, "uid": uid, "userid": userid, "discordid": discordid, "name": name, "roles": roles, "language": language, "application_token": False}
    
    return {"error": "Unauthorized", "code": 401}