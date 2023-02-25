# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
import sys
import time
from datetime import datetime, timedelta
# Load external code before original code to prevent overwrite
from importlib.machinery import SourceFileLoader

import pymysql
from fastapi import Header, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app import DH_START_TIME, app, config, version
from db import aiosql
from functions import *

for external_plugin in config.external_plugins:
    if os.path.exists(f"./external_plugins/{external_plugin}.py"):
        SourceFileLoader(external_plugin, f"./external_plugins/{external_plugin}.py").load_module()
    else:
        print(f"Error: External plugin \"{external_plugin}\" not found, exited.")
        sys.exit(1)

# import basic api
import apis.admin
import apis.auth
import apis.dlog
import apis.member
if config.tracker.lower() == "tracksim":
    import apis.tracksim
elif config.tracker.lower() == "navio":
    import apis.navio
import apis.user

# import plugins
if "announcement" in config.enabled_plugins:
    import plugins.announcement
if "application" in config.enabled_plugins:
    import plugins.application
if "challenge" in config.enabled_plugins:
    import plugins.challenge
if "division" in config.enabled_plugins:
    import plugins.division
if "downloads" in config.enabled_plugins:
    import plugins.downloads
if "event" in config.enabled_plugins:
    import plugins.event

# basic info
@app.get(f'/{config.abbr}')
async def index(request: Request, authorization: str = Header(None)):
    if not authorization is None:
        dhrid = request.state.dhrid
        await aiosql.new_conn(dhrid)
        au = await auth(dhrid, authorization, request, check_member = False)
        if not au["error"]:
            await activityUpdate(dhrid, au["discordid"], "index")
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    return {"error": False, "response": {"name": config.name, "abbr": config.abbr, \
        "version": version, "copyright": f"Copyright (C) {year} CharlesWithC"}}

# uptime
@app.get(f'/{config.abbr}/uptime')
async def uptime():
    up_time_second = int(time.time()) - DH_START_TIME
    return {"error": False, "response": {"uptime": str(timedelta(seconds = up_time_second))}}

# supported languages
@app.get(f'/{config.abbr}/languages')
async def languages():
    l = os.listdir(config.language_dir)
    t = []
    for ll in l:
        t.append(ll.split(".")[0])
    t = sorted(t)
    return {"error": False, "response": {"company": config.language, "supported": t}}

# middleware to manage database connection
# also include 500 error handler
err500 = []
pymysql_errs = [err for name, err in vars(pymysql.err).items() if name.endswith("Error")]
@app.middleware("http")
async def dispatch(request: Request, call_next):
    dhrid = genrid()
    request.state.dhrid = dhrid
    try:
        response = await call_next(request)
        await aiosql.close_conn(dhrid)
        return response
    except Exception as exc:
        await aiosql.close_conn(dhrid)
        traceback.print_exc()
        ismysqlerr = False
        for err in pymysql_errs:
            if isinstance(exc, err):
                ismysqlerr = True
                break
        if ismysqlerr:
            global err500
            if not -1 in err500 and int(time.time()) - DH_START_TIME >= 60:
                err500.append(time.time())
                err500[:] = [i for i in err500 if i > time.time() - 1800] # 5 error / 30 minutes = restart
                if len(err500) > 5:
                    try:
                        await arequests.post(config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Detected too many database errors. API will restart automatically.", "color": config.intcolor, "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
                    except:
                        pass
                    threading.Thread(target=restart).start()
                    err500.append(-1)
            return JSONResponse({"error": True, "descriptor": "Service Unavailable"}, status_code = 503)
        else:
            return JSONResponse({"error": True, "descriptor": "Internal Server Error"}, status_code = 500)

# thread to restart service
def restart():
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {config.abbr} > /dev/null")

# error handler to format error response
@app.exception_handler(StarletteHTTPException)
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": True, "descriptor": exc.detail}, status_code = exc.status_code)

@app.exception_handler(RequestValidationError)
async def error422Handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": True, "descriptor": "Unprocessable Entity"}, status_code = 422)

@app.exception_handler(500)
async def error500Handler(request: Request, exc: Exception):
    ismysqlerr = False
    for err in pymysql_errs:
        if isinstance(exc, err):
            ismysqlerr = True
            break
    if ismysqlerr:
        global err500
        if not -1 in err500 and int(time.time()) - DH_START_TIME >= 60:
            err500.append(time.time())
            err500[:] = [i for i in err500 if i > time.time() - 1800] # 5 error / 30 minutes = restart
            if len(err500) > 5:
                try:
                    await arequests.post(config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Detected too many database errors. API will restart automatically.", "color": config.intcolor, "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
                except:
                    pass
                threading.Thread(target=restart).start()
                err500.append(-1)
        return JSONResponse({"error": True, "descriptor": "Service Unavailable"}, status_code = 503)
    else:
        return JSONResponse({"error": True, "descriptor": "Internal Server Error"}, status_code = 500)
        
@app.on_event("startup")
async def startupEvent():
    await aiosql.create_pool()

@app.on_event("shutdown")
async def shutdownEvent():
    aiosql.close_pool()