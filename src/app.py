# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import importlib.util
import inspect
import json
import os
import sys
import time

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import api
import apis
import apis.auth
import apis.dlog
import apis.member
import apis.user
import db
import plugins
import static
from config import validateConfig
from logger import logger

abspath = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))

version = "2.5.4"

for argv in sys.argv:
    if argv.endswith(".py"):
        version += ".dev"

class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

def initApp(app, first_init = False):
    if not first_init:
        return app
    
    import upgrades.manager
    cur_version = app.version.replace(".dev", "").replace(".", "_")
    pre_version = cur_version.lstrip("v")
    conn = db.genconn(app)
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'version'")
    t = cur.fetchall()
    cur.close()
    conn.close()
    if len(t) != 0:
        pre_version = t[0][0].replace(".dev", "").replace(".", "_").lstrip("v")
    if pre_version != cur_version:
        if not pre_version in upgrades.manager.VERSION_CHAIN:
            logger.warning(f"[{app.config.abbr}] Previous version ({t[0][0]}) is not recognized. Aborted launch to prevent incompatability.")
            return None
        pre_idx = upgrades.manager.VERSION_CHAIN.index(pre_version)
        if not cur_version in upgrades.manager.VERSION_CHAIN:
            logger.warning(f"[{app.config.abbr}] Current version ({version}) is not recognized. Aborted launch to prevent incompatability.")
            return None
        cur_idx = upgrades.manager.VERSION_CHAIN.index(cur_version)
        for idx in range(pre_idx + 1, cur_idx + 1):
            v = upgrades.manager.VERSION_CHAIN[idx]
            if v in upgrades.manager.UPGRADEABLE_VERSION:
                logger.info(f"[{app.config.abbr}] Updating data to be compatible with {v.replace('_', '.')}...")
                upgrades.manager.UPGRADER[v].run(app)
    upgrades.manager.unload()
    
    if not version.endswith(".dev"):
        conn = db.genconn(app)
        cur = conn.cursor()
        cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
        conn.commit()
        cur.close()
        conn.close()
        
    logger.info(f"[{app.config.abbr}] Name: {app.config.name}")
    if app.openapi_enabled:
        logger.info(f"[{app.config.abbr}] OpenAPI: Enabled")
    else:
        logger.info(f"[{app.config.abbr}] OpenAPI: Disabled")
    if len(app.config.plugins) != 0:
        logger.info(f"[{app.config.abbr}] Plugins: {', '.join(sorted(app.config.plugins))}")
    else:
        logger.info(f"[{app.config.abbr}] Plugins: /")
    if len(app.config.external_plugins) != 0:
        extp = []
        for plugin_name in app.config.external_plugins:
            if plugin_name in app.loaded_external_plugins:
                extp.append(f"{plugin_name} (loaded)")
            else:
                extp.append(f"{plugin_name} (not loaded)")
        logger.info(f"[{app.config.abbr}] External Plugins: {', '.join(sorted(extp))}")
    else:
        logger.info(f"[{app.config.abbr}] External Plugins: /")

    os.system(f"rm -rf /tmp/hub/logo/{app.config.abbr}.png")
    os.system(f"rm -rf /tmp/hub/logo/{app.config.abbr}_bg.png")

    return app

def createApp(config_path, first_init = False):
    if not os.path.exists(config_path):
        return None
    
    config_txt = open(config_path, "r", encoding="utf-8").read()
    try:
        config_json = json.loads(config_txt)
    except:
        return None
    if not "abbr" in config_json.keys() or not "name" in config_json.keys():
        return None
    config = validateConfig(config_json)
    config = Dict2Obj(config)

    if os.path.exists(config.openapi):
        app = FastAPI(title="Drivers Hub", version=version, openapi_url=f"/doc/openapi.json", docs_url=f"/doc", redoc_url=None)
        
        OPENAPI_RESPONSES = '"responses": {"200": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Success"}, "204": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Success (No Content)"}, "400": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Bad Request - You need to correct the json data."}, "401": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Unauthorized - You need to use a valid token."}, "403": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Forbidden - You don\'t have permission to access the response."}, "404": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Not Found - The resource could not be found."}, "429": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Too Many Requests - You are being ratelimited."}, "500": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Internal Server Error - Usually caused by a bug or database issue."}, "503": {"content": {"application/json": {"schema": {"type": "object"}}},  "description": "Service Unavailable - Database outage or rate limited."}}'
        
        OPENAPI = json.loads(open(config.openapi, "r", encoding="utf-8").read()
                                .replace("/abbr", f"/{config.abbr}")
                                .replace('"responses": {}', OPENAPI_RESPONSES))
        def openapi():
            return OPENAPI
        app.openapi = openapi
        app.openapi_enabled = True
        
    else:
        app = FastAPI(title="Drivers Hub", version=version)
        app.openapi_enabled = False

    app.config = config
    app.backup_config = copy.deepcopy(config.__dict__)
    app.config_path = config_path
    app.start_time = int(time.time())
    app.db = db.aiosql(app = app, host = app.config.mysql_host, user = app.config.mysql_user, passwd = app.config.mysql_passwd, db = app.config.mysql_db)

    # External routes must be loaded before internal routes so that they can replace internal routes (if needed)
    external_routes = []
    app.loaded_external_plugins = []
    for plugin_name in app.config.external_plugins:
        if os.path.exists(f"external_plugins/{plugin_name}.py"):
            spec = importlib.util.spec_from_file_location(plugin_name, os.path.join(os.path.join(abspath, "external_plugins"), plugin_name + ".py"))
            external_plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(external_plugin)
        else:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': File not found.")
            continue

        app_bak = copy.copy(app)
        app.state.external_routes = []
        
        # init external plugin
        try:
            # NOTE: The 'app_to_modify' object will be modified by external plugin
            # We'll copy back additional state to original app
            app_to_modify = copy.copy(app)
            if external_plugin.init(app_to_modify, first_init) != True:
                if first_init:
                    logger.warning(f"[{app.config.abbr}] [External Plugin] '{plugin_name}' is not loaded: 'init' function did not return True.")
                continue
            for state in app_to_modify.state.__dict__.keys():
                if not state in app.state.__dict__.keys():
                    app.state.__dict__[state] = app_to_modify.state.__dict__[state]
        except Exception as exc:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': {exc}")
            app = copy.copy(app_bak)
            continue
        
        # load routes from app.state
        try:
            for route in app.state.external_routes:
                app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)
                external_routes.append(route.path)
        except Exception as exc:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': {exc}")
            app = copy.copy(app_bak)
            continue
        del app.state.external_routes

        app.loaded_external_plugins.append(plugin_name)

    routes = apis.routes + apis.auth.routes + apis.dlog.routes + apis.member.routes + apis.user.routes
    if app.config.tracker == "tracksim":
        routes += apis.routes_tracksim
    if "banner" in app.config.plugins:
        routes += apis.member.routes_banner
    if "announcement" in app.config.plugins:
        routes += plugins.routes_announcement
    if "application" in app.config.plugins:
        routes += plugins.routes_application
    if "challenge" in app.config.plugins:
        routes += plugins.routes_challenge
    if "division" in app.config.plugins:
        routes += plugins.routes_division
    if "downloads" in app.config.plugins:
        routes += plugins.routes_downloads
    if "economy" in app.config.plugins:
        routes += plugins.routes_economy
    if "event" in app.config.plugins:
        routes += plugins.routes_event
    for route in routes:
        if not route.path in external_routes:
            app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)

    app.add_exception_handler(StarletteHTTPException, api.errorHandler)
    app.add_exception_handler(RequestValidationError, api.error422Handler)
    app.add_middleware(api.HubMiddleware)
    app.add_middleware(GZipMiddleware)

    app = static.load(app)

    app.state.dberr = []
    app.state.session_errs = []
    app.state.cache_language = {} # language cache (3 seconds)
    app.state.cache_leaderboard = {}
    app.state.cache_nleaderboard = {}
    app.state.cache_all_users = []
    app.state.cache_all_users_ts = 0
    app.state.cache_statistics = {}
    app.state.discord_message_queue = []
    app.state.cache_session = {} # session token cache, this only checks if a session token is valid
    app.state.cache_session_extended = {} # extended session storage for ratelimit
    app.state.cache_ratelimit = {}
    app.state.cache_userinfo = {} # user info cache (15 seconds)
    app.state_cache_activity = {} # activity cache (2 seconds)
    
    try:
        db.init(app)
        app = initApp(app, first_init = first_init)
    except Exception as exc:
        if first_init:
            logger.error(f"[{app.config.abbr}] Error initializing app: {exc}")
        return None

    return app