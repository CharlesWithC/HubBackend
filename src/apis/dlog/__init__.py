# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi.routing import APIRoute
from fastapi.responses import JSONResponse

import apis.dlog.export as export
import apis.dlog.info as info
import apis.dlog.leaderboard as leaderboard
import apis.dlog.statistics as statistics

routes = [
    APIRoute("/dlog/list", info.get_list, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/leaderboard", leaderboard.get_leaderboard, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/export", export.get_export, methods=["GET"], response_class=JSONResponse),

    APIRoute("/dlog/statistics/summary", statistics.get_summary, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/statistics/chart", statistics.get_chart, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/statistics/details", statistics.get_details, methods=["GET"], response_class=JSONResponse),

    # these have to be put in the end, due to the speciality of the path
    APIRoute("/dlog/{logid}", info.get_dlog, methods=["GET"], response_class=JSONResponse),
    APIRoute("/dlog/{logid}", info.delete_dlog, methods=["DELETE"], response_class=JSONResponse)
]
