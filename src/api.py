# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import inspect
import json
import time
import traceback
from datetime import datetime

import psutil
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import URL, Address
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from functions import *
from logger import logger
from threads import *


async def startup_event(app):
    await app.db.create_pool()

    loop = asyncio.get_event_loop()
    loop.create_task(ClearOutdatedData(app))
    loop.create_task(DetectConfigChanges(app))
    loop.create_task(RefreshDiscordAccessToken(app))
    loop.create_task(ProcessDiscordMessage(app))
    loop.create_task(opqueue.run(app))
    loop.create_task(UpdateDlogStats(app))
    loop.create_task(SendDailyBonusNotification(app))
    if "event" in app.config.plugins:
        from plugins.event import EventNotification
        loop.create_task(EventNotification(app))
    if "poll" in app.config.plugins:
        from plugins.poll import PollResultNotification
        loop.create_task(PollResultNotification(app))

    for middleware in app.external_middleware["startup"]:
        if inspect.iscoroutinefunction(middleware):
            await middleware(app = app)
        else:
            middleware(app = app)

async def shutdown_event(app):
    app.db.close_pool()

# request param is needed as `call_next` will include it
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code = exc.status_code)

async def error422Handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": "Unprocessable Entity"}, status_code = 422)

# app.state.dberr = []
# redis session_errs (list)
async def tracebackHandler(request: Request, exc: Exception, err: str):
    try:
        if "mocked" in request.scope.keys():
            request = Request(scope={"type":"http", "app": request.app, "client": Address(host='127.0.0.1', port=80), "url": URL('http://127.0.0.1:80'), "path": "/", "headers": []})

        app = request.app

        if type(exc) is asyncio.exceptions.TimeoutError:
            # ascynio timeout error (usually triggered by arequests)
            return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

        ismysqlerr = False

        lines = err.split("\n")
        idx = 0
        # remove anyio.EndOfStream error
        for i in range(len(lines)):
            if lines[i].find("During handling of the above exception") != -1:
                idx = i+1
        lines = lines[idx:]
        while lines[0].startswith("\n") or lines[0] == "":
            lines = lines[1:]
        fmt = [lines[0]]
        i = 1
        IGNORE_TRACE = ["/fastapi/", "/starlette/", "/anyio/", "/pymysql/", "/aiomysql/"]
        while i < len(lines):
            ignore = False
            if lines[i].find("File") != -1 and lines[i].find("line") != -1:
                for to_ignore in IGNORE_TRACE:
                    if lines[i].find(to_ignore) != -1:
                        ignore = True
            if ignore:
                if i + 1 < len(lines) and app.version.endswith(".dev"):
                    # not compiled, has detail code in next line
                    i += 1
                # else: compiled, next line is file trace
            else:
                fmt.append(lines[i])
            i += 1
        err = "\n".join(fmt)
        err_hash = str(hashlib.sha256(err.encode()).hexdigest())[:16]

        if "json.decoder.JSONDecodeError" in err:
            # unable to parse json
            return JSONResponse({"error": ml.tr(request, "bad_json")}, status_code=400)

        for keyword in app.config.db_error_keywords:
            if keyword in err.lower():
                ismysqlerr = True
                break

        if ismysqlerr:
            if app.db.shutdown_lock:
                return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

            # this will filter mysql error + connection/timeout error (including custom errors flagged by "[aiosql]")
            # it's literally impossible to identify programming (query) error from database-side errors from error code
            # as they are mixed up
            # hence we'll just check and filter connection/timeout errors
            err = err.replace("[aiosql] ", "")
            if app.redis.lpos("session_errs", err_hash) is None:
                app.redis.lpush("session_errs", err_hash)

            logger.error(f"[{app.config.abbr}] {err_hash} [DATABASE] [{str(datetime.now())}]\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")

            if int(time.time()) - app.db.POOL_START_TIME >= 60 and app.db.POOL_START_TIME != 0:
                app.state.dberr.append(time.time())
                app.state.dberr[:] = [i for i in app.state.dberr if i > time.time() - 1800]

                if len(app.state.dberr) % 50 == 0:
                    opqueue.queue(app, "post", app.config.webhook_error, app.config.webhook_error, json.dumps({"embeds": [{"title": "Database Error", "description": "Detected too many database errors, it's recommended to restart service.", "fields": [{"name": "Host", "value": app.config.domain, "inline": True}, {"name": "Abbreviation", "value": app.config.abbr, "inline": True}, {"name": "Version", "value": app.version, "inline": True}], "color": int(app.config.hex_color, 16), "timestamp": str(datetime.now())}]}), {"Content-Type": "application/json"}, None)

                if len(app.state.dberr) % 100 == 0:
                    app.state.dberr = []

                if len(app.state.dberr) % 10 == 0:
                    logger.info(f"[{app.config.abbr}] Restarting database connection pool")
                    await app.db.restart_pool()

            return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

        else:
            logger.error(f"[{app.config.abbr}] {err_hash} [{str(datetime.now())}]\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")

            if app.redis.lpos("session_errs", err_hash) is None:
                app.redis.lpush("session_errs", err_hash)
                if app.config.webhook_error != "":
                    opqueue.queue(app, "post", app.config.webhook_error, app.config.webhook_error, json.dumps({"embeds": [{"title": "Error", "description": f"```{err}```", "fields": [{"name": "Host", "value": app.config.domain, "inline": True}, {"name": "Abbreviation", "value": app.config.abbr, "inline": True}, {"name": "Version", "value": app.version, "inline": True}, {"name": "Request IP", "value": f"`{request.client.host}`", "inline": False}, {"name": "Request URL", "value": str(request.url), "inline": False}], "footer": {"text": err_hash}, "color": int(app.config.hex_color, 16), "timestamp": str(datetime.now())}]}), {"Content-Type": "application/json"}, None)

            return JSONResponse({"error": "Internal Server Error"}, status_code = 500)
    except:
        traceback.print_exc()
        return JSONResponse({"error": "Internal Server Error"}, status_code = 500)

# middleware to manage database connection
class HubMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        app = request.app
        try:
            real_path = "/" + "/".join(request.url.path.split("/")[2:])
        except:
            real_path = "/"

        try:
            process = psutil.Process()
            sleep_cnt = 0
            while process.memory_info().rss / 1024 / 1024 > app.memory_threshold and app.memory_threshold != 0:
                sleep_cnt += 0.1
                await asyncio.sleep(0.1)
                if sleep_cnt >= 30:
                    return JSONResponse({"error": "Service Unavailable"}, status_code = 503)
        except:
            return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

        try:
            for middleware in app.external_middleware["request"]:
                if inspect.iscoroutinefunction(middleware):
                    ret = await middleware(request = request)
                else:
                    ret = middleware(request = request)
                if ret is not None:
                    (request, resp) = ret
                    if resp is not None:
                        return resp
        except Exception as exc:
            err = traceback.format_exc()

            for middleware in app.external_middleware["response_fail"]:
                if inspect.iscoroutinefunction(middleware):
                    resp = await middleware(request = request, exception = exc, traceback = err)
                else:
                    resp = middleware(request = request, exception = exc, traceback = err)
                if resp is not None:
                    return resp

            if len(app.external_middleware["error_handler"]) != 0:
                middleware = app.external_middleware["error_handler"][0]
                try:
                    if inspect.iscoroutinefunction(middleware):
                        response = await middleware(request = request, exception = exc, traceback = err)
                    else:
                        response = middleware(request = request, exception = exc, traceback = err)
                    return response
                except:
                    pass

            response = (await tracebackHandler(request, exc, err))

            return response

        if request.method != "GET" and real_path.split("/")[1] not in ["tracksim", "trucky", "custom-tracker"]:
            if "content-type" in request.headers.keys():
                if request.headers["content-type"] != "application/json":
                    return JSONResponse({"error": "Content-Type must be application/json"}, status_code=400)
        if request.client is None:
            client_host = request.headers.get('X-Forwarded-For', '').split(',')[0].strip()
            request.client = client_host
            if client_host is None:
                return JSONResponse({"error": "Invalid Request"}, status_code=400)

        if real_path.startswith("/tracksim") and "tracksim" not in configured_trackers(app):
            return JSONResponse({"error": "Not Found"}, status_code=404)
        if real_path.startswith("/trucky") and not real_path.startswith("/trucky/import") and "trucky" not in configured_trackers(app):
            return JSONResponse({"error": "Not Found"}, status_code=404)
        if real_path.startswith("/custom-tracker") and "custom" not in configured_trackers(app):
            return JSONResponse({"error": "Not Found"}, status_code=404)

        dhrid = genrid()
        request.state.dhrid = dhrid
        try:
            request_start_time = time.time()
            rl = await ratelimit(request, 'MIDDLEWARE', 60, 300, cGlobalOnly=True)
            if rl[0]:
                await app.db.close_conn(dhrid)
                return rl[1]
            response = await call_next(request)

            if response.status_code not in [404, 500, 503] and real_path in ["/", "/config", "/dlog/list", "/dlog", "/announcements/list", "/announcements", "/events/list", "/events"]:
                # validate token after all (only to formalize responses in case auth is not necessarily needed)
                if request.headers.get("Authorization") is not None and request.headers.get("Authorization").split(" ")[0] in ["Bearer", "Application"]:
                    au = await auth(request.headers.get("Authorization"), request, check_member = False, allow_application_token = True, only_validate_token = True, only_use_cache = True)
                    if au["error"]:
                        response = JSONResponse({"error": au["error"]}, status_code=au["code"])

            iowait = app.db.get_iowait(dhrid)
            request_end_time = time.time()

            if app.enable_performance_header:
                response.headers["X-Response-Time"] = str(round(request_end_time - request_start_time, 4))
                if iowait is not None:
                    response.headers["X-Database-Response-Time"] = str(round(iowait, 4))

            for middleware in app.external_middleware["response_ok"]:
                if inspect.iscoroutinefunction(middleware):
                    resp = await middleware(request = request, response = response)
                else:
                    resp = middleware(request = request, response = response)
                if resp is not None:
                    await app.db.close_conn(dhrid)
                    return resp

            await app.db.close_conn(dhrid)

            return response

        except Exception as exc:
            err = traceback.format_exc()

            for middleware in app.external_middleware["response_fail"]:
                if inspect.iscoroutinefunction(middleware):
                    resp = await middleware(request = request, exception = exc, traceback = err)
                else:
                    resp = middleware(request = request, exception = exc, traceback = err)
                if resp is not None:
                    await app.db.close_conn(dhrid)
                    return resp

            if len(app.external_middleware["error_handler"]) != 0:
                middleware = app.external_middleware["error_handler"][0]
                try:
                    if inspect.iscoroutinefunction(middleware):
                        response = await middleware(request = request, exception = exc, traceback = err)
                    else:
                        response = middleware(request = request, exception = exc, traceback = err)
                    await app.db.close_conn(dhrid)
                    return response
                except:
                    pass

            response = (await tracebackHandler(request, exc, err))

            await app.db.close_conn(dhrid)

            return response
