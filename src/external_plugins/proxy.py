# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This plugin provides limited CORS proxy service.

from urllib.parse import urlparse

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from functions import *


async def get_proxy(request: Request, response: Response, url: str):
    domain = urlparse(url).netloc
    if domain not in ["api.truckersmp.com"]:
        response.status_code = 403
        return {"error": "Forbidden"}
    r = await arequests.get(request.app, url, headers={ "User-Agent": "The Drivers Hub Project (CHub)" })
    response.status_code = r.status_code
    return r.json()

def init(config: dict, print_log: bool = False):
    routes = [
        APIRoute("/proxy", get_proxy, methods=["GET"], response_class=JSONResponse)
    ]

    states = {}

    return (True, routes, states, {})
