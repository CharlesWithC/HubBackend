# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import json
import os
import sys
import time

from fastapi import FastAPI

from config import validateConfig

version = "v2.4.1"

for argv in sys.argv:
    if argv.endswith(".py"):
        version += ".rc"

class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

config_txt = open(os.environ["HUB_CONFIG_FILE"], "r", encoding="utf-8").read()
config = validateConfig(json.loads(config_txt))
config = Dict2Obj(config)

if os.path.exists(config.openapi):
    app = FastAPI(title="Drivers Hub", version=version[1:], openapi_url=f"/openapi.json", docs_url=f"/doc", redoc_url=None)
    
    OPENAPI_RESPONSES = '"responses": {"200": {"description": "Success"}, "204": {"description": "Success (No Content)"}, "400": {"description": "Bad Request - You need to correct the json data."}, "401": {"description": "Unauthorized - You need to use a valid token."}, "403": {"description": "Forbidden - You don\'t have permission to access the response."}, "404": {"description": "Not Found - The resource could not be found."}, "429": {"description": "Too Many Requests - You are being ratelimited."}, "500": {"description": "Internal Server Error - Usually caused by a bug or database issue."}, "503": {"description": "Service Unavailable - Database outage or rate limited."}}'
    
    OPENAPI = json.loads(open(config.openapi, "r", encoding="utf-8").read()
                            .replace("/abbr", f"/{config.abbr}")
                            .replace('"responses": {}', OPENAPI_RESPONSES))
    def openapi():
        return OPENAPI
    app.openapi = openapi
    
else:
    app = FastAPI(title="Drivers Hub", version=version[1:])

app.config = config
app.backup_config = copy.deepcopy(config.__dict__)
app.config_path = os.environ["HUB_CONFIG_FILE"]
app.start_time = int(time.time())