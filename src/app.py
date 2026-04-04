# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import functools
import importlib.util
import inspect
import json
import os
import time

import redis
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.gzip import GZipMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException

import api
import apis
import apis.auth
import apis.dlog
import apis.member
import apis.tracker
import apis.user
import db
import plugins
import static
from config import validateConfig
from functions import Dict2Obj
from logger import logger
from static import version

abspath = os.path.dirname(os.path.abspath(inspect.getframeinfo(inspect.currentframe()).filename))

class PrefixedRedis:
    NO_KEY_METHODS = {"ping","info","time","client_list","client_setname","config_get","config_set","script_load","script_exists","pubsub","close","connection_pool"}
    EXEMPT_KEYS = {"session_errs"}

    def __init__(self, redis_instance, prefix):
        self.redis = redis_instance
        self.prefix = prefix

    def _prefix_key(self, key):
        if not isinstance(key, str) or key in PrefixedRedis.EXEMPT_KEYS:
            return key
        if key.startswith(self.prefix + ":"):
            logger.warning("[redis] Ignored duplicate prefix in key: %s", key)
            return key
        return f"{self.prefix}:{key}"

    def _wrap_client(self, client):
        def wrap_call(fn):
            @functools.wraps(fn)
            def inner(*args, **kwargs):
                if args:
                    args = (self._prefix_key(args[0]),) + args[1:]
                return fn(*args, **kwargs)
            return inner

        class Wrapper:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                if hasattr(client, "__exit__"):
                    return client.__exit__(exc_type, exc, tb)
                return False

            def __getattr__(self, name):
                attr = getattr(client, name)
                if not callable(attr) or name in PrefixedRedis.NO_KEY_METHODS:
                    return attr
                return wrap_call(attr)
        return Wrapper()

    def pipeline(self, *args, **kwargs):
        return self._wrap_client(self.redis.pipeline(*args, **kwargs))

    def __getattr__(self, name):
        return getattr(self._wrap_client(self.redis), name)

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

    if args["ignore_external_plugins"]:
        logger.warning(f"[{app.config.abbr}] Ignoring external plugins")

    if app.use_master_db:
        logger.warning(f"[{app.config.abbr}] Using master database pool")

    if app.enable_performance_header:
        logger.warning(f"[{app.config.abbr}] Performance header enabled")
    if app.memory_threshold != 0:
        logger.warning(f"[{app.config.abbr}] Memory threshold: {app.memory_threshold}MB (New requests will be put on hold when the threshold is reached)")

    if app.config.db_pool_size < 5 and not app.use_master_db:
        logger.warning(f"[{app.config.abbr}] Database pool size is smaller than 5, database error rate may increase")

    if "disable_upgrader" not in args.keys() or not args["disable_upgrader"]:
        import upgrades.manager
        cur_version = app.version.replace(".dev", "").replace(".", "_")
        pre_version = cur_version.lstrip("v")
        conn = db.genconn(app.config)
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

    conn = db.genconn(app.config)
    cur = conn.cursor()
    app.redis.delete("multiprocess-pid")
    app.redis.set("running_export", 0)
    app.redis.delete("avgrt:value")
    app.redis.delete("avgrt:counter")
    app.redis.delete("avgrt:reset-time")
    if not version.endswith(".dev"):
        cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
    conn.commit()
    cur.close()
    conn.close()

    return app

def createApp(config_path, multi_mode = False, first_init = False, args = {}, master_db = None):
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
    config_dict = validateConfig(config_json)
    config = Dict2Obj(config_dict)

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
    app.config_dict = config_dict
    app.backup_config = copy.deepcopy(config_dict)
    app.config_path = config_path
    app.config_last_modified = os.path.getmtime(app.config_path)
    app.start_time = int(time.time())
    app.multi_mode = multi_mode
    app.use_master_db = master_db
    if master_db:
        # use the database pool from the master app
        # this happens when --use-master-db-pool is enabled
        app.db = master_db
    else:
        # create individual database pool
        app.db = db.aiosql(host = app.config.db_host, user = app.config.db_user, passwd = app.config.db_password, db_name = app.config.db_name, db_pool_size = app.config.db_pool_size)
    app.enable_performance_header = "enable_performance_header" in args.keys() and args["enable_performance_header"]
    app.memory_threshold = args["memory_threshold"] if "memory_threshold" in args.keys() else 0
    app.banner_service_url = args["banner_service_url"]

    app.redis = PrefixedRedis(redis.Redis(app.config.redis_host, app.config.redis_port, app.config.redis_db, app.config.redis_password, decode_responses = True), app.config.abbr)
    app.redis_bin = PrefixedRedis(redis.Redis(app.config.redis_host, app.config.redis_port, app.config.redis_db, app.config.redis_password, decode_responses = False), app.config.abbr)
    # auth:{authorization_key} | uinfo:{uid} | ulang:{uid} | utz:{uid} (timezone)
    # uprivacy:{uid} | unote:{from_uid}/{to_uid} | uactivity:{uid}
    # ratelimit:{identifier}(:{route}) => this is a set
    # stats:{rid}:{userid} | stats:after | stats:before
    # lb:{rid}:{speed_limit}:{game} | lb:after | lb:before | nlb

    # NOTE: In uinfo, userid is -1 if not exist, discordid/steamid/truckersmpid/email would be "" if not exist.
    # When extracting data, userid should be kept -1 unless returned in API response (converted to None),
    # discordid/steamid/truckersmpid should be handled by "nint" which converts "" to None,
    # email should be checked specially and converted to None if invalid.

    # for all redis objects with partial update, do extend expiry before accessing resource
    # if unsure about when the data expires or if data exists, do full update only
    # currently, we have partial update for: auth, uinfo

    # External routes must be loaded before internal routes so that they can replace internal routes (if needed)
    if args["ignore_external_plugins"]:
        app.config.external_plugins = []
    external_routes = []
    app.loaded_external_plugins = []
    app.external_middleware = {"startup": [], "request": [], "response_ok": [], "response_fail": [], "error_handler": [], "discord_request": []}
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
            res = external_plugin.init(app.config_dict, first_init)
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
            test_app.external_middleware = {"startup": [], "request": [], "response_ok": [], "response_fail": [], "error_handler": [], "discord_request": []}
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

    # both trackers will be added and 404 will be handled within the route
    # so we can realize switching tracker without needing to restart program
    routes += apis.tracker.routes_tracksim
    routes += apis.tracker.routes_trucky
    routes += apis.tracker.routes_custom
    routes += apis.tracker.routes_unitracker
    if "route" in app.config.plugins:
        routes += apis.tracker.routes_tracksim_route

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
    if "task" in app.config.plugins:
        routes += plugins.routes_task
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

    app.state.dberr = [] # must be local since db pool is created locally
    # session_errs was moved to redis to prevent duplicate report
    app.state.discord_message_queue = []
    app.state.discord_retry_after = {}
    app.state.discord_opqueue = []
    app.state.statistics_details_last_work = -1 # be local since it's not THAT cpu intensive like dlog export

    try:
        if os.path.exists(f"/tmp/hub/logo/{app.config.abbr}.png"):
            os.remove(f"/tmp/hub/logo/{app.config.abbr}.png")
        if os.path.exists(f"/tmp/hub/logo/{app.config.abbr}_bg.png"):
            os.remove(f"/tmp/hub/logo/{app.config.abbr}_bg.png")
        if os.path.exists(f"/tmp/hub/template/{app.config.abbr}.png"):
            os.remove(f"/tmp/hub/template/{app.config.abbr}.png")
    except:
        pass

    try:
        app = initApp(app, first_init = first_init, args = args)
    except Exception as exc:
        if first_init:
            import traceback
            traceback.print_exc()
            logger.error(f"[{app.config.abbr}] Error initializing app: {exc}")
        return None

    if first_init and "rebuild_dlog_stats" in args.keys() and args["rebuild_dlog_stats"]:
        logger.warning(f"[{app.config.abbr}] Rebuilding dlog stats, this might take some time...")
        apis.dlog.statistics.rebuild(app)

    return app
