# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from datetime import timedelta

import aiomysql
from fastapi import Header, Request, Response

from functions import *
from multilang import LANGUAGES


async def get_index(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if authorization is not None:
        await app.db.new_conn(dhrid, db_name = app.config.db_name)
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if not au["error"]:
            await ActivityUpdate(request, au["uid"], "index")
    return {"name": app.config.name, "abbr": app.config.abbr, "language": app.config.language, "version": app.version, "copyright": "Copyright (C) 2022-2026 CharlesWithC"}

async def get_status(request: Request, response: Response):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /status', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    dbstatus = "unavailable"
    try:
        dhrid = request.state.dhrid
        await app.db.new_conn(dhrid, db_name = app.config.db_name)
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
        await app.db.new_conn(dhrid, db_name = app.config.db_name)
        dbstatus = "available"
    except:
        pass

    if dbstatus == "available":
        return {"error": "Database pool restart is not necessary."}

    if app.db.is_restarting and time.time() - app.db.restart_start < 60:
        return {"error": "Database pool is already restarting."}

    app.db.is_restarting = True
    app.db.restart_start = time.time()
    try:
        app.db.pool.terminate()
        app.db.pool = await aiomysql.create_pool(host = app.db.host, user = app.db.user, password = app.db.passwd, \
                                            db = app.db.db_name, autocommit = False, pool_recycle = 5, \
                                            maxsize = app.db.db_pool_size)
        return {"success": True}
    except Exception as exc:
        from api import tracebackHandler
        await tracebackHandler(request, exc, traceback.format_exc())
        return {"success": False}
    finally:
        app.db.is_restarting = False
        app.db.restart_start = 0
