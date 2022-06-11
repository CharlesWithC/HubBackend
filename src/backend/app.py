# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
import os
import json
import discord

class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

config = None
if os.path.exists("./config.json"):
    config_txt = open("./config.json","r").read()
    config = json.loads(config_txt)
    hexcolor = config["hexcolor"]
    rgbcolor = tuple(int(hexcolor[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = discord.Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config = Dict2Obj(config)
    
app = FastAPI(openapi_url=f"/{config.vtcprefix}/openapi.json", docs_url=f"/{config.vtcprefix}/doc", redoc_url=None)
def openapi():
    with open("openapi.json", "r") as openapi:
        return json.load(openapi)
app.openapi = openapi