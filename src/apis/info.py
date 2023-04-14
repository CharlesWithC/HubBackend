# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from datetime import datetime, timedelta

from fastapi import Header, Request, Response

from multilang import LANGUAGES
from functions import *
import static


async def get_index(request: Request, authorization: str = Header(None)):
    app = request.app
    if authorization is not None:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        au = await auth(authorization, request, check_member = False)
        if not au["error"]:
            await ActivityUpdate(request, au["uid"], "index")
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    return {"name": app.config.name, "abbr": app.config.abbr, "language": app.config.language, "version": app.version, "copyright": f"Copyright (C) {year} CharlesWithC"}

async def get_status(request: Request):
    app = request.app
    dbstatus = "unavailable"
    try:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        dbstatus = "available"
    except:
        pass
    up_time_second = int(time.time()) - app.start_time
    return {"api": "active", "database": dbstatus, "uptime": str(timedelta(seconds = up_time_second))}

async def get_languages(request: Request):
    app = request.app
    return {"company": app.config.language, "supported": LANGUAGES}