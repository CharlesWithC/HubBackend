# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This is an example of external plugin.
# This plugin modifies `/` route and creates a new route called `/external`.

from datetime import datetime

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from functions import *


async def get_index(request: Request, authorization: str = Header(None)):
    '''Rework original get_index and add `message` to response'''
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
    return {"name": app.config.name, "abbr": app.config.abbr, "language": app.config.language, "version": app.version, "message": app.state.message, "copyright": f"Copyright (C) {year} CharlesWithC"}

async def get_external(request: Request):
    '''New route responding with `app.state.message`'''
    return {"message": request.app.state.message}

async def startup(app):
    print("STARTUP")

async def request(request: Request):
    print(f"NEW REQUEST from {request.client.host}")

async def response_ok(request: Request, response):
    print(f"RESPONSE OK: {response}")

async def response_fail(request: Request, exception, traceback):
    print(f"RESPONSE FAIL: {exception}")

async def error_handler(request: Request, exception, traceback):
    return JSONResponse({"error": str(exception)}, status_code=400)

def init(config: dict, print_log: bool = False):
    # Define routes
    routes = [
        # overwrite / route
        APIRoute("/", get_index, methods=["GET"], response_class=JSONResponse),
        # create /external route
        APIRoute("/external", get_external, methods=["GET"], response_class=JSONResponse)
    ]

    # Define additional state
    states = {"message": "External plugin loaded!"}

    # Plugin can be loaded, return (True, routes, state)
    # If plugin should not be loaded (e.g. due to specific conditions), return False
    return (True, routes, states, {"startup": startup, "request": request, "response_ok": response_ok, "response_fail": response_fail, "error_handler": error_handler})
