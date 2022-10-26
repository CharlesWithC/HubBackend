# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from datetime import datetime, timedelta
import json, os

from app import app, config, version, DH_START_TIME
from db import newconn
from functions import *
import multilang as ml

# Load external code before original code to prevent overwrite
from importlib.machinery import SourceFileLoader

for external_plugin in config.external_plugins:
    if os.path.exists(f"./external_plugins/{external_plugin}.py"):
        SourceFileLoader(external_plugin, f"./external_plugins/{external_plugin}.py").load_module()
        print("Loaded external plugin: " + external_plugin)

# import basic api
import apis.admin
import apis.auth
import apis.dlog
import apis.member
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
async def index():
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    return {"error": False, "response": {"name": config.name, "abbr": config.abbr, \
        "version": version, "copyright": f"Copyright (C) {year} CharlesWithC"}}

# ping
@app.get(f'/{config.abbr}/ping')
async def ping():
    up_time_second = int(time.time()) - DH_START_TIME
    return {"error": False, "response": {"status": "active", "uptime": str(timedelta(seconds = up_time_second))}}

# error handler to uniform error response
@app.exception_handler(StarletteHTTPException)
async def errorHandler(request: Request, exc: StarletteHTTPException):
    return JSONResponse({"error": True, "descriptor": exc.detail}, status_code = exc.status_code)