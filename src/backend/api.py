# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
from captcha.image import ImageCaptcha
import json, base64, uuid
from io import BytesIO

from app import app, config
from db import newconn
from functions import *

import apis.announcement
import apis.application
import apis.auth
import apis.division
import apis.dlog
import apis.event
import apis.member
import apis.navio
import apis.user

@app.get('/atm/info')
async def home():
    return {"error": False, "response":{"message": "At The Mile Logistics DriversHub.\nBackend by CharlesWithC#7777."}}

@app.get("/atm/info/version")
async def apiGetVersion(request: Request):
    return {"error": False, "response":{"version": "v1.0"}}

@app.get("/atm/info/ip")
async def apiGetIP(request: Request):
    return {"error": False, "response":{"ip": request.client.host}}