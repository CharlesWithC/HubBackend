# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This plugin is created for internal testing purpose.

from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from functions import *
import aiomysql


async def close_pool(request: Request):
    app = request.app
    try:
        app.db.pool.terminate()
        return {"message": "Database pool terminated"}
    except:
        import traceback
        traceback.print_exc()
        return {"message": "Failed to terminate database pool"}

async def create_pool(request: Request):
    app = request.app
    try:
        app.db.pool = await aiomysql.create_pool(host = app.db.host, user = app.db.user, password = app.db.passwd, \
                                        db = app.db.db, autocommit = False, pool_recycle = 5, \
                                        maxsize = min(20, app.db.app.config.mysql_pool_size))
        return {"message": "Database pool created"}
    except:
        import traceback
        traceback.print_exc()
        return {"message": "Failed to create database pool"}

def init(config: dict, print_log: bool = False):
    routes = [
        APIRoute("/db-test/close-pool", close_pool, methods=["GET"], response_class=JSONResponse),
        APIRoute("/db-test/create-pool", create_pool, methods=["GET"], response_class=JSONResponse),
    ]

    return (True, routes, {}, {})
