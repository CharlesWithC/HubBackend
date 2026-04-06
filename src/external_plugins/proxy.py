# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This plugin provides limited CORS proxy service.

from urllib.parse import urlparse

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from functions import *

DOMAIN_WHITELIST = []

async def get_proxy(request: Request, url: str):
    domain = urlparse(url).netloc
    if domain not in DOMAIN_WHITELIST:
        return JSONResponse({"error": "Forbidden"}, 403)

    r = await arequests.get(request.app, url)
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
