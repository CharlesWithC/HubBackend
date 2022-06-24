# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
import json, os, sys
from sys import exit

from app import app, config
from db import newconn
from functions import *
import multilang as ml

from importlib.machinery import SourceFileLoader

# Load external code before original code to prevent overwrite
for external_plugin in config.external_plugins:
    if os.path.exists(f"./external_plugins/{external_plugin}.py"):
        print("Loading external plugin: " + external_plugin)
        SourceFileLoader(external_plugin, f"./external_plugins/{external_plugin}.py").load_module()

import apis.admin
import apis.auth
import apis.dlog
import apis.member
import apis.navio
import apis.user

if "announcement" in config.enabled_plugins:
    import plugins.announcement
if "application" in config.enabled_plugins:
    import plugins.application
if "division" in config.enabled_plugins:
    import plugins.division
if "downloads" in config.enabled_plugins:
    import plugins.downloads
if "event" in config.enabled_plugins:
    import plugins.event

@app.get(f'/{config.vtcprefix}/info')
async def home():
    return {"error": False, "response": {"vtc": config.vtcname, "prefix": config.vtcprefix, "version": "v1.8.9", "copyright": "Copyright (C) 2022 CharlesWithC"}}

@app.get(f"/{config.vtcprefix}/ip")
async def apiGetIP(request: Request):
    return {"error": False, "response": request.client.host}