# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This is an example of external plugin.
# This plugin modifies `/` route and creates a new route called `/external`.

from datetime import datetime

from fastapi import Header, Request
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from functions import *


async def get_index(request: Request, authorization: str = Header(None)):
    '''Rework original get_index and add `with_external_plugin = True` to response'''
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
    return {"name": app.config.name, "abbr": app.config.abbr, "language": app.config.language, "version": app.version, "with_external_plugin": True, "copyright": f"Copyright (C) {year} CharlesWithC"}

async def get_external(request: Request):
    '''New route responding with `app.state.message`'''
    return {"message": request.app.state.message}

def init(app, first_init = False):
    # Modify app.state.external_routes to add new routes
    app.state.external_routes = [
        # overwrite / route
        APIRoute("/", get_index, methods=["GET"], response_class=JSONResponse),
        # create /external route
        APIRoute("/external", get_external, methods=["GET"], response_class=JSONResponse)
    ]

    # Add new state data
    app.state.message = "This is the route created by an external plugin."

    # Plugin can be loaded, return True
    # If plugin should not be loaded (e.g. due to specific conditions), return False
    return True