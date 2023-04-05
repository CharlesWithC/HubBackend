# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import sys

from fastapi import FastAPI
from starlette.routing import Mount

import app as base

app = FastAPI()

# gracefully stops all async tasks
def shutdownEvent():
    os._exit(42)

def initRoutes(config_paths, first_init = False):
    global app
    routes = []
    scopes = {}

    for config_path in config_paths:
        dh = base.createApp(config_path, first_init = first_init)
        if dh is not None:
            try:
                scopes = {"host": dh.config.server_host, "port": int(dh.config.server_port), "workers": int(dh.config.server_workers)}
            except:
                continue
            if len(config_paths) > 1:
                dh.multi_mode = True
            else:
                dh.multi_mode = False
            routes.append(Mount(f"/{dh.config.abbr}", dh, name = f"{dh.config.name} Drivers Hub"))

    if len(routes) == 0:
        print("No valid config is loaded, aborted.")
        sys.exit(1)

    app = FastAPI(routes = routes)
    app.add_event_handler("shutdown", shutdownEvent)

    if len(routes) == 1:
        return scopes
    else:
        return None