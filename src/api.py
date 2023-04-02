# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import hashlib
import json
import os
import sys
import threading
import time
from datetime import datetime
# Load external code before original code to prevent overwrite
from importlib.machinery import SourceFileLoader

import pymysql
from fastapi import Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from apis import routes as apis_routes  # admin + tracksim
from apis.auth import routes as auth_routes
from apis.dlog import routes as dlog_routes
from apis.member import routes as member_routes
from apis.user import routes as user_routes
from app import app, version
from functions import *
from plugins import routes as plugins_routes

routes = apis_routes + auth_routes + dlog_routes + member_routes + user_routes + plugins_routes
for route in routes:
    app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)

# for external_plugin in app.config.external_plugins:
#     if os.path.exists(f"./external_plugins/{external_plugin}.py"):
#         SourceFileLoader(external_plugin, f"./external_plugins/{external_plugin}.py").load_module()
#     else:
#         print(f"Error: External plugin \"{external_plugin}\" not found, exited.")
#         sys.exit(1)

# thread to restart service
def restart():
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {app.config.abbr} > /dev/null")

# NOTE Due to FastAPI not supporting events for sub-applications, we'll have to detour like this
# The startup_event will be called by middleware once at least one request is sent
async def startup_event():   
    await app.db.create_pool()

    dhrid = 0
    await app.db.new_conn(dhrid)
    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'process-event-notification-pid' OR skey = 'process-event-notification-last-update'")
    await app.db.commit(dhrid)
    await app.db.close_conn(dhrid)

    loop = asyncio.get_event_loop()
    loop.create_task(ClearOutdatedData())
    loop.create_task(ProcessDiscordMessage())
    from plugins.events import EventNotification
    loop.create_task(EventNotification())

# request param is needed as `call_next` will include it
@app.exception_handler(StarletteHTTPException)
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code = exc.status_code)

@app.exception_handler(RequestValidationError)
async def error422Handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": "Unprocessable Entity"}, status_code = 422)

# middleware to manage database connection
# also include 500 error handler
app.state.dberr = []
app.state.pymysql_errs = [err for name, err in vars(pymysql.err).items() if name.endswith("Error") and err not in [pymysql.err.ProgrammingError]]
app.state.session_errs = []
@app.middleware("http")
async def http_middleware(request: Request, call_next):
    if request.method != "GET" and request.url.path.split("/")[2] not in ["tracksim"]:
        if "content-type" in request.headers.keys():
            if request.headers["content-type"] != "application/json":
                return JSONResponse({"error": "Content-Type must be application/json."}, status_code=400)
    if not "started" in app.state.__dict__["_state"].keys(): 
        app.state.started = True
        await startup_event()
    dhrid = genrid()
    request.state.dhrid = dhrid
    try:
        rl = await ratelimit(dhrid, request, 'MIDDLEWARE', 60, 150, cGlobalOnly=True)
        if rl[0]:
            return rl[1]
        response = await call_next(request)
        await app.db.close_conn(dhrid)
        return response
    except Exception as exc:
        await app.db.close_conn(dhrid)

        ismysqlerr = False
        if type(exc) in app.state.pymysql_errs:
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
                        await arequests.post(app.config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Detected too many database errors. API will restart automatically.", "color": int(app.config.hex_color, 16), "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
                    except:
                        pass
                    threading.Thread(target=restart).start()
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
                    await arequests.post(app.config.webhook_error, data=json.dumps({"embeds": [{"title": "Error", "description": f"```{err}```", "fields": [{"name": "Host", "value": app.config.apidomain, "inline": True}, {"name": "Abbreviation", "value": app.config.abbr, "inline": True}, {"name": "Version", "value": version, "inline": True}, {"name": "Request IP", "value": request.client.host, "inline": False}, {"name": "Request URL", "value": str(request.url), "inline": False}], "footer": {"text": err_hash}, "color": int(app.config.hex_color, 16), "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"}, timeout = 10)
                except:
                    pass
            return JSONResponse({"error": "Internal Server Error"}, status_code = 500)