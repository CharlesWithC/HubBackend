# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import json
import random
import re
import string
import time
from datetime import datetime

import requests

from functions.dataop import *
from static import *


def getUrl4Msg(message):
    return app.config.frontend_urls.auth_message.replace("{message}", str(message))

def getUrl4Token(token):
    return app.config.frontend_urls.auth_token.replace("{token}", str(token))

def getUrl4MFA(token):
    return app.config.frontend_urls.auth_mfa.replace("{token}", str(token))

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
    if abbr.upper() in ISO3166_COUNTRIES.keys():
        return convertQuotation(ISO3166_COUNTRIES[abbr.upper()])
    else:
        return ""

def getRequestCountry(request, abbr = False):
    if "cf-ipcountry" in request.headers.keys():
        country = request.headers["cf-ipcountry"]
        if country.upper() in ISO3166_COUNTRIES.keys(): # makre sure abbr is a valid country code
            if abbr:
                return convertQuotation(request.headers["cf-ipcountry"])
            else:
                return convertQuotation(ISO3166_COUNTRIES[country.upper()])
    return ""

def getUserAgent(request):
    if "user-agent" in request.headers.keys():
        if len(request.headers["user-agent"]) <= 200:
            return convertQuotation(request.headers["user-agent"])
        return ""
    else:
        return ""
    
def DisableDiscordIntegration():
    app.config.discord_bot_token = ""
    try:
        requests.post(app.config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Failed to validate Discord Bot Token. All Discord Integrations have been temporarily disabled within the current session. Setting a valid token in config and restarting API will restore the functions.", "color": int(app.config.hex_color, 16), "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
    except:
        pass

async def EnsureEconomyBalance(dhrid, userid):
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO economy_balance VALUES ({userid}, 0)")

async def ClearOutdatedData():
    while 1:
        # combined thread
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)

            await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE first_request_timestamp <= {round(time.time() - 3600)}")
            await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE endpoint = '429-error' AND first_request_timestamp <= {round(time.time() - 60)}")
            await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
            await app.db.execute(dhrid, f"SELECT uid FROM user WHERE email = 'pending' AND join_timestamp < {int(time.time() - 86400)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                uid = tt[0]
                await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
            
            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)
        except:
            pass
        
        try:
            await asyncio.sleep(30)
        except:
            return