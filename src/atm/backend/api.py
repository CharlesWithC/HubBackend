# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from fastapi import Request
from captcha.image import ImageCaptcha
import json, base64, uuid
from io import BytesIO

from app import app
from db import newconn
from functions import *

import apis.auth
import apis.member
import apis.application

@app.get('/atm/info')
async def home():
    return {"error": False, "response":{"message": "At The Mile Logistics DriversHub.\nBackend by CharlesWithC#7777."}}

@app.get("/atm/info/version")
async def apiGetVersion(request: Request):
    return {"error": False, "response":{"version": "v1.0"}}

@app.get("/atm/info/ip")
async def apiGetIP(request: Request):
    return {"error": False, "response":{"ip": request.client.host}}