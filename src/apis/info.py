# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import time
from datetime import datetime, timedelta

from fastapi import Header, Request

from app import app, version
from functions import *


async def get_index(request: Request, authorization: str = Header(None)):
    if authorization is not None:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        au = await auth(dhrid, authorization, request, check_member = False)
        if not au["error"]:
            await ActivityUpdate(dhrid, au["uid"], "index")
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    return {"name": app.config.name, "abbr": app.config.abbr, "language": app.config.language, "version": version, "copyright": f"Copyright (C) {year} CharlesWithC"}

async def get_status(request: Request):
    dbstatus = "unavailable"
    try:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        dbstatus = "available"
    except:
        pass
    up_time_second = int(time.time()) - app.start_time
    return {"api": "active", "database": dbstatus, "uptime": str(timedelta(seconds = up_time_second))}

async def get_languages():
    l = os.listdir(app.config.language_dir)
    t = []
    for ll in l:
        t.append(ll.split(".")[0])
    t = sorted(t)
    return {"company": app.config.language, "supported": t}