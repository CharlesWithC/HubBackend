# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from datetime import datetime, timedelta

import aiomysql
from fastapi import Header, Request

from functions import *
from multilang import LANGUAGES


async def get_index(request: Request, authorization: str = Header(None)):
    app = request.app
    if authorization is not None:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
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

async def restart_database(request: Request):
    app = request.app
    if time.time() - app.db.POOL_START_TIME < 60:
        return {"error": "Database pool is too young to be restarted."}

    dbstatus = "unavailable"
    try:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid)
        dbstatus = "available"
    except:
        pass

    if dbstatus == "available":
        return {"error": "Database pool restart is not necessary."}

    try:
        app.db.pool.terminate()
        app.db.pool = await aiomysql.create_pool(host = app.db.host, user = app.db.user, password = app.db.passwd, \
                                            db = app.db.db, autocommit = False, pool_recycle = 5, \
                                            maxsize = min(20, app.db.app.config.mysql_pool_size))
        return {"success": True}
    except:
        return {"success": False}
