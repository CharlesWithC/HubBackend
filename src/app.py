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
from functions import Dict2Obj
from logger import logger

abspath = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))

version = "2.7.13"

for argv in sys.argv:
    if argv.endswith(".py"):
        version += ".dev"

def initApp(app, first_init = False, args = {}):
    if not first_init:
        return app

    logger.info(f"[{app.config.abbr}] Name: {app.config.name} | Prefix: {app.config.prefix}")
    if app.config.openapi:
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

    if app.enable_performance_header:
        logger.warning(f"[{app.config.abbr}] Performance header enabled")

    if "disable_upgrader" not in args.keys() or not args["disable_upgrader"]:
        import upgrades.manager
        cur_version = app.version.replace(".dev", "").replace(".", "_")
        pre_version = cur_version.lstrip("v")
        conn = db.genconn(app)
        cur = conn.cursor()
        cur.execute("SELECT sval FROM settings WHERE skey = 'version'")
        t = cur.fetchall()
        cur.close()
        conn.close()
        if len(t) != 0:
            pre_version = t[0][0].replace(".dev", "").replace(".", "_").lstrip("v")
        if "force_upgrade_from" in args.keys() and args["force_upgrade_from"] is not None:
            pre_version = args["force_upgrade_from"]
            if pre_version not in upgrades.manager.VERSION_CHAIN:
                logger.warning(f"[{app.config.abbr}] Force upgrade version ({t[0][0]}) is not recognized. Aborted launch to prevent incompatability.")
                return None
        if pre_version != cur_version:
            if pre_version not in upgrades.manager.VERSION_CHAIN:
                logger.warning(f"[{app.config.abbr}] Previous version ({t[0][0]}) is not recognized. Aborted launch to prevent incompatability.")
                return None
            pre_idx = upgrades.manager.VERSION_CHAIN.index(pre_version)
            if cur_version not in upgrades.manager.VERSION_CHAIN:
                logger.warning(f"[{app.config.abbr}] Current version ({version}) is not recognized. Aborted launch to prevent incompatability.")
                return None
            cur_idx = upgrades.manager.VERSION_CHAIN.index(cur_version)
            for idx in range(pre_idx + 1, cur_idx + 1):
                v = upgrades.manager.VERSION_CHAIN[idx]
                if v in upgrades.manager.UPGRADER.keys():
                    logger.info(f"[{app.config.abbr}] Updating data to be compatible with {v.replace('_', '.')}...")
                    upgrades.manager.UPGRADER[v].run(app)
        upgrades.manager.unload()
    else:
        logger.warning(f"[{app.config.abbr}] Upgrader disabled")

    if first_init:
        conn = db.genconn(app)
        cur = conn.cursor()
        cur.execute("DELETE FROM settings WHERE skey = 'multiprocess-pid' OR skey = 'multiprocess-last-update'")
        if not version.endswith(".dev"):
            cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
        conn.commit()
        cur.close()
        conn.close()

    return app

def createApp(config_path, multi_mode = False, first_init = False, args = {}):
    if not os.path.exists(config_path):
        return None

    try:
        config_txt = open(config_path, "r", encoding="utf-8").read()
    except:
        return None
    try:
        config_json = json.loads(config_txt)
    except:
        return None
    if "abbr" not in config_json.keys() or "name" not in config_json.keys():
        return None
    config = validateConfig(config_json)
    config = Dict2Obj(config)

    if config.openapi and static.OPENAPI is not None:
        app = FastAPI(title="Drivers Hub", version=version, openapi_url="/doc/openapi.json", docs_url="/doc", redoc_url=None)
        def openapi():
            data = static.OPENAPI
            data["servers"] = [{"url": f"https://{config.domain}{config.prefix}", "description": config.name}]
            data["info"]["version"] = version
            return static.OPENAPI
        app.openapi = openapi
    else:
        app = FastAPI(title="Drivers Hub", version=version)

    app.config = config
    app.backup_config = copy.copy(config.__dict__)
    app.config_path = config_path
    app.config_last_modified = os.path.getmtime(app.config_path)
    app.start_time = int(time.time())
    app.multi_mode = multi_mode
    app.db = db.aiosql(app = app, host = app.config.mysql_host, user = app.config.mysql_user, passwd = app.config.mysql_passwd, db = app.config.mysql_db)
    app.enable_performance_header = "enable_performance_header" in args.keys() and args["enable_performance_header"]

    # External routes must be loaded before internal routes so that they can replace internal routes (if needed)
    external_routes = []
    app.loaded_external_plugins = []
    app.external_middleware = {"startup": [], "request": [], "response_ok": [], "response_fail": [], "error_handler": []}
    for plugin_name in app.config.external_plugins:
        if os.path.exists(f"external_plugins/{plugin_name}.py"):
            spec = importlib.util.spec_from_file_location(plugin_name, os.path.join(os.path.join(abspath, "external_plugins"), plugin_name + ".py"))
            external_plugin = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(external_plugin)
        else:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': File not found.")
            continue

        # init external plugin
        try:
            res = external_plugin.init(app.config.__dict__, first_init)
            if res is False:
                if first_init:
                    logger.warning(f"[{app.config.abbr}] [External Plugin] '{plugin_name}' is not loaded: 'init' function did not return True.")
                continue
            routes = res[1]
            states = res[2]
            middlewares = res[3]
        except Exception as exc:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': {exc}")
            continue

        # test routes and state
        try:
            test_app = FastAPI()
            test_app.external_middleware = {"startup": [], "request": [], "response_ok": [], "response_fail": [], "error_handler": []}
            for route in routes:
                test_app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)
            for state in states.keys():
                if state not in app.state.__dict__.keys():
                    test_app.state.__dict__[state] = states[state]
            for middleware_type in middlewares.keys():
                if middleware_type in test_app.external_middleware:
                    middleware = middlewares[middleware_type]
                    if callable(middleware):
                        test_app.external_middleware[middleware_type].append(middleware)
                    elif type(middleware) == list:
                        for mdw in middleware:
                            if callable(mdw):
                                test_app.external_middleware[middleware_type].append(mdw)
        except Exception as exc:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': {exc}")
            continue

        # load routes and state
        try:
            for route in routes:
                app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)
                external_routes.append(route.path)
            for state in states.keys():
                if state not in app.state.__dict__.keys():
                    app.state.__dict__[state] = states[state]
            for middleware_type in middlewares.keys():
                if middleware_type in app.external_middleware:
                    middleware = middlewares[middleware_type]
                    if callable(middleware):
                        app.external_middleware[middleware_type].append(middleware)
                    elif type(middleware) == list:
                        for mdw in middleware:
                            if callable(mdw):
                                app.external_middleware[middleware_type].append(mdw)
        except Exception as exc:
            if first_init:
                logger.error(f"[{app.config.abbr}] [External Plugin] Error loading '{plugin_name}': {exc}")
            continue

        app.loaded_external_plugins.append(plugin_name)

    routes = apis.routes + apis.auth.routes + apis.dlog.routes + apis.member.routes + apis.user.routes
    if app.config.tracker == "tracksim":
        routes += apis.routes_tracksim
        if "route" in app.config.plugins:
            routes += apis.routes_tracksim_route
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
    if "poll" in app.config.plugins:
        routes += plugins.routes_poll
    for route in routes:
        if route.path not in external_routes:
            if multi_mode and route.path == "/restart":
                continue
            app.add_api_route(path=route.path, endpoint=route.endpoint, methods=route.methods, response_class=route.response_class)

    app.add_exception_handler(StarletteHTTPException, api.errorHandler)
    app.add_exception_handler(RequestValidationError, api.error422Handler)
    app.add_middleware(api.HubMiddleware)
    app.add_middleware(GZipMiddleware)

    app = static.load(app)

    app.state.dberr = []
    app.state.session_errs = []
    app.state.cache_language = {} # language cache (3 seconds)
    app.state.cache_timezone = {} # timezone cache (3 seconds)
    app.state.cache_privacy = {} # privacy cache (3 seconds)
    app.state.cache_note = {} # note cache (3 seconds)
    app.state.cache_leaderboard = {}
    app.state.cache_nleaderboard = {}
    app.state.cache_all_users = []
    app.state.cache_all_users_ts = 0
    app.state.cache_statistics = {}
    app.state.discord_message_queue = []
    app.state.discord_retry_after = {}
    app.state.discord_opqueue = []
    app.state.cache_session = {} # session token cache, this only checks if a session token is valid
    app.state.cache_session_extended = {} # extended session storage for ratelimit
    app.state.cache_ratelimit = {}
    app.state.cache_userinfo = {} # user info cache (15 seconds)
    app.state_cache_activity = {} # activity cache (2 seconds)
    app.state.statistics_details_last_work = -1
    app.state.running_export = 0

    try:
        if os.path.exists(f"/tmp/hub/logo/{app.config.abbr}.png"):
            os.remove(f"/tmp/hub/logo/{app.config.abbr}.png")
        if os.path.exists(f"/tmp/hub/logo/{app.config.abbr}_bg.png"):
            os.remove(f"/tmp/hub/logo/{app.config.abbr}_bg.png")
    except:
        pass

    try:
        db.init(app)
        app = initApp(app, first_init = first_init, args = args)
    except Exception as exc:
        if first_init:
            logger.error(f"[{app.config.abbr}] Error initializing app: {exc}")
        return None

    if first_init and "rebuild_dlog_stats" in args.keys() and args["rebuild_dlog_stats"]:
        logger.warning(f"[{app.config.abbr}] Rebuilding dlog stats, this might take some time...")
        apis.dlog.statistics.rebuild(app)

    return app
