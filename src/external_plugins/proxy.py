# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This plugin provides limited CORS proxy service.

from urllib.parse import urlparse

from fastapi import Header, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from functions import *

DOMAIN_WHITELIST = ["api.truckersmp.com"]

async def get_proxy(request: Request, response: Response, url: str, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid

    await app.db.new_conn(dhrid, db_name = app.config.db_name)
    au = await auth(authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    domain = urlparse(url).netloc
    if domain not in DOMAIN_WHITELIST:
        return JSONResponse({"error": "Forbidden"}, 403)

    r = await arequests.get(app, url, dhrid = dhrid)
    content_type = r.headers.get("Content-Type", "application/octet-stream")
    return Response(
        content=r.content,
        status_code=r.status_code,
        media_type=content_type
    )

def init(config: dict, print_log: bool = False):
    routes = [
        APIRoute("/proxy", get_proxy, methods=["GET"])
    ]

    states = {}

    return (True, routes, states, {})
