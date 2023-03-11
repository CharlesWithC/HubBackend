# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta
# Load external code before original code to prevent overwrite
from importlib.machinery import SourceFileLoader

import pymysql
from fastapi import Header, Request, Response
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
    if authorization is not None:
        dhrid = request.state.dhrid
        await aiosql.new_conn(dhrid)
        au = await auth(dhrid, authorization, request, check_member = False)
        if not au["error"]:
            await ActivityUpdate(dhrid, au["discordid"], "index")
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    return {"name": config.name, "abbr": config.abbr, "version": version, "copyright": f"Copyright (C) {year} CharlesWithC"}

# uptime
@app.get(f'/{config.abbr}/uptime')
async def uptime():
    up_time_second = int(time.time()) - DH_START_TIME
    return {"uptime": str(timedelta(seconds = up_time_second))}

# supported languages
@app.get(f'/{config.abbr}/languages')
async def languages():
    l = os.listdir(config.language_dir)
    t = []
    for ll in l:
        t.append(ll.split(".")[0])
    t = sorted(t)
    return {"company": config.language, "supported": t}

# middleware to manage database connection
# also include 500 error handler
dberr = []
pymysql_errs = [err for name, err in vars(pymysql.err).items() if name.endswith("Error")]
session_errs = []
@app.middleware("http")
async def dispatch(request: Request, call_next):
    if request.method != "GET" and request.url.path.split("/")[2] not in ["tracksim", "navio"]:
        if "content-type" in request.headers.keys():
            if request.headers["content-type"] != "application/json":
                return JSONResponse({"error": "Content-Type must be application/json."}, status_code=400)
    dhrid = genrid()
    request.state.dhrid = dhrid
    try:
        response = await call_next(request)
        await aiosql.close_conn(dhrid)
        return response
    except Exception as exc:
        global session_errs
        await aiosql.close_conn(dhrid)

        ismysqlerr = False
        for err in pymysql_errs:
            if isinstance(exc, err):
                ismysqlerr = True
                break

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
            print(f"DATABASE ERROR\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")
            
            if err_hash not in session_errs:
                session_errs.append(err_hash)
                if config.webhook_error != "":
                    try:
                        await arequests.post(config.webhook_error, data=json.dumps({"embeds": [{"title": "Database Error", "description": f"```{err}```", "fields": [{"name": "Host", "value": config.apidomain, "inline": True}, {"name": "Abbreviation", "value": config.abbr, "inline": True}, {"name": "Version", "value": version, "inline": True}, {"name": "Request IP", "value": request.client.host, "inline": False}, {"name": "Request URL", "value": str(request.url), "inline": False}], "footer": {"text": err_hash}, "color": config.intcolor, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"}, timeout = 10)
                    except:
                        pass

            global dberr
            if not -1 in dberr and int(time.time()) - aiosql.POOL_START_TIME >= 60 and aiosql.POOL_START_TIME != 0:
                dberr.append(time.time())
                dberr[:] = [i for i in dberr if i > time.time() - 1800]
                if len(dberr) > 5:
                    # try restarting database connection first
                    print("Restarting database connection pool")
                    await aiosql.restart_pool()
                elif len(dberr) > 10:
                    print("Restarting service due to database errors")
                    try:
                        await arequests.post(config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Detected too many database errors. API will restart automatically.", "color": config.intcolor, "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
                    except:
                        pass
                    threading.Thread(target=restart).start()
                    dberr.append(-1)
            return JSONResponse({"error": "Service Unavailable"}, status_code = 503)
        
        else:
            if err_hash in session_errs:
                # recognized error, do not print log or send webhook
                print(f"ERROR: {err_hash}\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\nTraceback not logged as it has already been logged in the current worker.")
                return JSONResponse({"error": "Internal Server Error"}, status_code = 500)
            session_errs.append(err_hash)

            print(f"ERROR: {err_hash}\nRequest IP: {request.client.host}\nRequest URL: {str(request.url)}\n{err}")
            if config.webhook_error != "":
                try:
                    await arequests.post(config.webhook_error, data=json.dumps({"embeds": [{"title": "Error", "description": f"```{err}```", "fields": [{"name": "Host", "value": config.apidomain, "inline": True}, {"name": "Abbreviation", "value": config.abbr, "inline": True}, {"name": "Version", "value": version, "inline": True}, {"name": "Request IP", "value": request.client.host, "inline": False}, {"name": "Request URL", "value": str(request.url), "inline": False}], "footer": {"text": err_hash}, "color": config.intcolor, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"}, timeout = 10)
                except:
                    pass
            return JSONResponse({"error": "Internal Server Error"}, status_code = 500)

# thread to restart service
def restart():
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {config.abbr} > /dev/null")

# error handler to format error response
@app.exception_handler(StarletteHTTPException)
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": exc.detail}, status_code = exc.status_code)

@app.exception_handler(RequestValidationError)
async def error422Handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"error": "Unprocessable Entity"}, status_code = 422)

@app.on_event("startup")
async def startupEvent():
    await aiosql.create_pool()

@app.on_event("shutdown")
async def shutdownEvent():
    aiosql.close_pool()