# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
import random
import re
import string
import time
from datetime import datetime

import requests
from fastapi import Request

import multilang as ml
from functions.dataop import *
from static import *


class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

def restart(app):
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {app.config.abbr} > /dev/null")

def genrid():
    return str(int(time.time()*10000000)) + str(random.randint(0, 10000)).zfill(5)

def gensecret(length = 32):
    return ''.join(random.choice(string.ascii_letters) for i in range(length))

def getDayStartTs(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    return int(datetime(dt.year, dt.month, dt.day).timestamp())

def isurl(s):
    r = re.compile(
            r'^(?:http)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(r, s) is not None

def getDomainFromUrl(s):
    if not isurl(s):
        return False
    r = re.search(r"(?<=://)[^/]+", s)
    if r:
        return r.group(0)
    else:
        return False

def getFullCountry(abbr):
    if abbr.upper() in ISO_COUNTRIES.keys():
        return convertQuotation(ISO_COUNTRIES[abbr.upper()])
    else:
        return ""

def getRequestCountry(request, abbr = False):
    if "cf-ipcountry" in request.headers.keys():
        country = request.headers["cf-ipcountry"]
        if country.upper() in ISO_COUNTRIES.keys(): # makre sure abbr is a valid country code
            if abbr:
                return convertQuotation(request.headers["cf-ipcountry"])
            else:
                return convertQuotation(ISO_COUNTRIES[country.upper()])
    return ""

def getUserAgent(request):
    if "user-agent" in request.headers.keys():
        if len(request.headers["user-agent"]) < 256:
            return convertQuotation(request.headers["user-agent"])
        else:
            return convertQuotation(request.headers["user-agent"])[:256]
    else:
        return ""

def DisableDiscordIntegration(app):
    request = Request(scope={"type":"http", "app": app})
    app.config.discord_bot_token = ""
    try:
        if app.config.hook_audit_log.webhook_url != "":
            requests.post(app.config.hook_audit_log.webhook_url, data=json.dumps({"embeds": [{"title": ml.ctr(request, "attention_required"), "description": ml.ctr(request, "invalid_discord_token"), "color": int(app.config.hex_color, 16), "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
    except:
        pass

async def EnsureEconomyBalance(request, userid):
    (app, dhrid) = (request.app, request.state.dhrid)
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO economy_balance VALUES ({userid}, 0)")
