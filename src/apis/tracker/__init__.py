# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

import apis.tracker.tracksim as tracksim
import apis.tracker.trucky as trucky
import apis.tracker.custom as custom

routes_tracksim = [
    APIRoute("/tracksim/update", tracksim.post_update, methods=["POST"], response_class=JSONResponse),
    APIRoute("/tracksim/driver/{userid}", tracksim.put_driver, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/tracksim/driver/{userid}", tracksim.delete_driver, methods=["DELETE"], response_class=JSONResponse)
]

routes_tracksim_route = [
    APIRoute("/tracksim/update/route", tracksim.post_update_route, methods=["POST"], response_class=JSONResponse)
]

routes_trucky = [
    APIRoute("/trucky/update", trucky.post_update, methods=["POST"], response_class=JSONResponse),
    APIRoute("/trucky/import/{jobid}", trucky.post_import, methods=["POST"], response_class=JSONResponse),
    APIRoute("/trucky/driver/{userid}", trucky.put_driver, methods=["PUT"], response_class=JSONResponse),
    APIRoute("/trucky/driver/{userid}", trucky.delete_driver, methods=["DELETE"], response_class=JSONResponse)
]

routes_custom = [
    APIRoute("/custom-tracker/update", custom.post_update, methods=["POST"], response_class=JSONResponse),
]
