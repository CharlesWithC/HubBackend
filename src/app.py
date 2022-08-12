# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
import os
import json
import discord
import requests
from PIL import Image
from io import BytesIO

import sys
from sys import exit

config_path = os.environ["HUB_CONFIG_FILE"]

version = "v1.11.3"

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
    config["rgbcolor"] = discord.Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
except:
    hex_color = "FFFFFF"
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = discord.Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
perms = config["perms"]
for perm in perms.keys():
    roles = perms[perm]
    newroles = []
    for role in roles:
        newroles.append(int(role))
    perms[perm] = newroles
config["perms"] = perms
tconfig = config
config = Dict2Obj(config)
del tconfig["intcolor"]
del tconfig["rgbcolor"]

vtc_logo = ""
logo = Image.new("RGBA", (400,400),(255,255,255))
logobg = Image.new("RGB", (3400,3400),(255,255,255))
try:
    r = requests.get(config.vtc_logo_link, timeout = 10)
    if r.status_code == 200:
        vtc_logo = r.content
        vtc_logo = Image.open(BytesIO(vtc_logo)).convert("RGBA")

        logo = vtc_logo
        logobg = vtc_logo
        lnd = []
        lbnd = []
        datas = vtc_logo.getdata()
        for item in datas:
            if item[3] == 0:
                lnd.append((255, 255, 255, 255))
                lbnd.append((255, 255, 255, 255))
            else:
                lnd.append((item[0], item[1], item[2], 255))
                lbnd.append((int(0.85*255+0.15*item[0]), int(0.85*255+0.15*item[1]), int(0.85*255+0.15*item[2]), 255))
        logo.putdata(lnd)
        logo = logo.resize((400, 400), resample=Image.ANTIALIAS).convert("RGBA")
        logobg.putdata(lbnd)
        logobg = logobg.resize((3400, 3400), resample=Image.ANTIALIAS).convert("RGB")
except:
    import traceback
    traceback.print_exc()
    pass

if os.path.exists(config.apidoc):
    app = FastAPI(openapi_url=f"/{config.vtc_abbr}/openapi.json", docs_url=f"/{config.vtc_abbr}/doc", redoc_url=None)
    def openapi():
        with open(config.apidoc, "r") as openapi:
            return json.load(openapi)
    app.openapi = openapi
else:
    app = FastAPI()