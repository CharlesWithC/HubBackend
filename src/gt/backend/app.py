# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
import os
import json

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
    config = Dict2Obj(json.loads(config_txt))
    
app = FastAPI(openapi_url="/gt/openapi.json", docs_url="/gt/doc", redoc_url=None)
def openapi():
    with open("openapi.json", "r") as openapi:
        return json.load(openapi)
app.openapi = openapi

# import discord
# from discord.ext import commands,tasks

# intents = discord.Intents().all()
# bot = commands.Bot(command_prefix='dh?', intents=intents)