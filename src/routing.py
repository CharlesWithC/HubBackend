# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os

from fastapi import FastAPI
from starlette.routing import Mount

import app as base
import static
from logger import logger

app = FastAPI()

# gracefully stops all async tasks
def shutdownEvent():
    os._exit(42)

def initRoutes(config_paths, openapi_path, first_init = False, enable_performance_header = False):
    global app
    routes = []
    scopes = {}
    servers = []

    for config_path in config_paths:
        dh = base.createApp(config_path, multi_mode = len(config_paths) > 1, first_init = first_init, enable_performance_header = enable_performance_header)
        if dh is not None:
            try:
                scopes = {"host": dh.config.server_host, "port": int(dh.config.server_port), "workers": int(dh.config.server_workers)}
            except:
                continue
            routes.append(Mount(f"{dh.config.prefix}", dh, name = f"{dh.config.name} Drivers Hub"))
            servers.append({"url": f"https://{dh.config.domain}{dh.config.prefix}", "description": dh.config.name})

    if len(routes) == 0:
        logger.warning("No valid config is loaded, quited.")
        os._exit(42)

    if first_init:
        logger.info("")

    if openapi_path != "" and static.OPENAPI is not None:
        app = FastAPI(title = "Drivers Hub", routes = routes, version = base.version, \
                      openapi_url = f"{openapi_path.rstrip('/')}/openapi.json", docs_url = f"{openapi_path}", redoc_url=None)

        def openapi():
            data = static.OPENAPI
            data["servers"] = servers
            data["info"]["version"] = base.version
            return static.OPENAPI
        app.openapi = openapi
    else:
        app = FastAPI(title = "Drivers Hub", version = base.version, routes = routes)

    app.add_event_handler("shutdown", shutdownEvent)

    if len(routes) == 1:
        return scopes
    else:
        return None
