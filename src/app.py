# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
from discord import Colour
from io import BytesIO
import os, sys, json, requests, time, logging

config_path = os.environ["HUB_CONFIG_FILE"]

version = "v1.19.5"

DH_START_TIME = int(time.time())

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

config_txt = open(config_path, "r").read()
config = json.loads(config_txt)

hex_color = config["hex_color"][-6:]
try:
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
except:
    hex_color = "FFFFFF"
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)

perms = config["perms"]
for perm in perms.keys():
    roles = perms[perm]
    newroles = []
    for role in roles:
        try:
            newroles.append(int(role))
        except:
            pass
    perms[perm] = newroles
config["perms"] = perms

if not "server_workers" in config.keys():
    config["server_workers"] = 1

tconfig = config
config = Dict2Obj(config)
del tconfig["intcolor"]
del tconfig["rgbcolor"]

if os.path.exists(config.apidoc):
    app = FastAPI(openapi_url=f"/{config.abbr}/openapi.json", docs_url=f"/{config.abbr}/doc", redoc_url=None)
    def openapi():
        f = open(config.apidoc, "r")
        d = f.read().replace("/abbr", f"/{config.abbr}")
        return json.loads(d)
    app.openapi = openapi
else:
    app = FastAPI()