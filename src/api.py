# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import json
import threading
import time
from datetime import datetime

import pymysql
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from functions import *


# NOTE Due to FastAPI not supporting events for sub-applications, we'll have to detour like this
# The startup_event will be called by middleware once at least one request is sent
async def startup_event(app):   
    await app.db.create_pool()

    dhrid = 0
    await app.db.new_conn(dhrid)
    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'process-event-notification-pid' OR skey = 'process-event-notification-last-update'")
    await app.db.commit(dhrid)
    await app.db.close_conn(dhrid)

    loop = asyncio.get_event_loop()
    loop.create_task(ClearOutdatedData(app))
    loop.create_task(ProcessDiscordMessage(app))
    from plugins.events import EventNotification
    loop.create_task(EventNotification(app))

# request param is needed as `call_next` will include it
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code = exc.status_code)

async def error422Handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": "Unprocessable Entity"}, status_code = 422)

# middleware to manage database connection
# also include 500 error handler
pymysql_errs = [err for name, err in vars(pymysql.err).items() if name.endswith("Error") and err not in [pymysql.err.ProgrammingError]]
# app.state.dberr = []
# app.state.session_errs = []
class HubMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        app = request.app
        if request.method != "GET" and request.url.path.split("/")[2] not in ["tracksim"]:
            if "content-type" in request.headers.keys():
                if request.headers["content-type"] != "application/json":
                    return JSONResponse({"error": "Content-Type must be application/json."}, status_code=400)
        if not "started" in app.state.__dict__["_state"].keys(): 
            app.state.started = True
            await startup_event(app)
        dhrid = genrid()
        request.state.dhrid = dhrid
        try:
            rl = await ratelimit(request, 'MIDDLEWARE', 60, 150, cGlobalOnly=True)
            if rl[0]:
                return rl[1]
            response = await call_next(request)
            await app.db.close_conn(dhrid)
            return response
        except Exception as exc:
            await app.db.close_conn(dhrid)

            ismysqlerr = False
            if type(exc) in pymysql_errs:
                ismysqlerr = True

            err = traceback.format_exc()
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
                for to_ignore in IGNORE_TRACE:
                    if lines[i].find(to_ignore) != -1:
                        ignore = True
                if ignore:
                    if i + 1 < len(lines) and lines[i + 1].find("File ") == -1 and lines[i + 1].find(" line ") == -1:
                        # not compiled, has detail code in next line
                        i += 1
                    # else: compiled, next line is file trace
                else:
                    fmt.append(lines[i])
                i += 1
            err = "\n".join(fmt)
            err_hash = str(hashlib.sha256(err.encode()).hexdigest())[:16]

            if "await request.json()" in err and "json.decoder.JSONDecodeError" in err:
                # unable to parse json
                return JSONResponse({"error": ml.tr(request, "bad_json")}, status_code=400)

            if ismysqlerr:
                print(f"DATABASE ERROR [{str(datetime.now())}]\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")

                if not -1 in app.state.dberr and int(time.time()) - app.db.POOL_START_TIME >= 60 and app.db.POOL_START_TIME != 0:
                    app.state.dberr.append(time.time())
                    app.state.dberr[:] = [i for i in app.state.dberr if i > time.time() - 1800]
                    if len(app.state.dberr) > 5:
                        # try restarting database connection first
                        print("Restarting database connection pool")
                        await app.db.restart_pool()
                    elif len(app.state.dberr) > 10:
                        print("Restarting service due to database errors")
                        try:
                            await arequests.post(app, app.config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Detected too many database errors. API will restart automatically.", "color": int(app.config.hex_color, 16), "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
                        except:
                            pass
                        threading.Thread(target=restart, args=(app,)).start()
                        app.state.dberr.append(-1)
                        
                return JSONResponse({"error": "Service Unavailable"}, status_code = 503)
            
            else:
                if err_hash in app.state.session_errs:
                    # recognized error, do not print log or send webhook
                    print(f"ERROR: {err_hash} [{str(datetime.now())}]\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\nTraceback not logged as it has already been logged in the current worker.")
                    return JSONResponse({"error": "Internal Server Error"}, status_code = 500)
                app.state.session_errs.append(err_hash)

                print(f"ERROR: {err_hash} [{str(datetime.now())}]\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")
                if app.config.webhook_error != "":
                    try:
                        await arequests.post(app, app.config.webhook_error, data=json.dumps({"embeds": [{"title": "Error", "description": f"```{err}```", "fields": [{"name": "Host", "value": app.config.apidomain, "inline": True}, {"name": "Abbreviation", "value": app.config.abbr, "inline": True}, {"name": "Version", "value": app.version, "inline": True}, {"name": "Request IP", "value": request.client.host, "inline": False}, {"name": "Request URL", "value": str(request.url), "inline": False}], "footer": {"text": err_hash}, "color": int(app.config.hex_color, 16), "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"}, timeout = 10)
                    except:
                        pass
                return JSONResponse({"error": "Internal Server Error"}, status_code = 500)