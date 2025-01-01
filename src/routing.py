# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

import api
import app as base
import db
import static
from logger import logger

app = FastAPI()

@asynccontextmanager
async def lifespan(app: FastAPI):
    for route in app.routes:
        if hasattr(route, "app") and hasattr(route, "name") and route.name.endswith("Drivers Hub"):
            await api.startup_event(route.app)
    yield
    for route in app.routes:
        if hasattr(route, "app") and hasattr(route, "name") and route.name.endswith("Drivers Hub"):
            await api.shutdown_event(route.app)
    os._exit(42)

def initRoutes(config_paths, openapi_path, first_init = False, args = {}):
    global app
    scopes = {}
    servers = []

    # create main application
    if openapi_path != "" and static.OPENAPI is not None:
        app = FastAPI(title = "Drivers Hub", version = base.version, lifespan=lifespan, \
                      openapi_url = f"{openapi_path.rstrip('/')}/openapi.json", docs_url = f"{openapi_path}", redoc_url=None)

        # set openapi
        def openapi():
            data = static.OPENAPI
            data["servers"] = servers
            data["info"]["version"] = base.version
            return static.OPENAPI
        app.openapi = openapi
    else:
        app = FastAPI(title = "Drivers Hub", version = base.version, lifespan=lifespan)

    if args["use_master_db_pool"]:
        app.db = db.aiosql(host = args["master_db_host"], user = args["master_db_user"], passwd = args["master_db_password"], db_name = 'information_schema', db_pool_size = args['master_db_pool_size'], master_db=True)
    else:
        app.db = None

    # mount drivers hub sub-applications
    for config_path in config_paths:
        dh = base.createApp(config_path, multi_mode = len(config_paths) > 1, first_init = first_init, args = args, master_db = app.db)
        if dh is not None:
            try:
                scopes = {"host": dh.config.server_host, "port": int(dh.config.server_port), "workers": int(dh.config.server_workers)}
            except:
                continue
            app.mount(f"{dh.config.prefix}", dh, name = f"{dh.config.name} Drivers Hub")
            servers.append({"url": f"https://{dh.config.domain}{dh.config.prefix}", "description": dh.config.name})

    # check
    if len(servers) == 0:
        logger.warning("No valid config is loaded, quited.")
        os._exit(42)

    if first_init:
        logger.info("")

    if len(servers) == 1:
        return scopes
    else:
        return None
