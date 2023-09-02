# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import traceback

import multilang as ml
from api import tracebackHandler
from functions import arequests


async def add_driver(request, steamid):
    (app, dhrid) = (request.app, request.state.dhrid)
    tracker_app_error = ""
    try:
        if app.config.tracker == "tracksim":
            r = await arequests.post(app, "https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + app.config.tracker_api_token}, dhrid = dhrid)
        elif app.config.tracker == "trucky":
            r = await arequests.post(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid)}, headers = {"Authorization": "X-ACCESS-TOKEN " + app.config.tracker_api_token}, dhrid = dhrid)
        if app.config.tracker == "trucky" and resp["success"]:
            return ""
        if r.status_code in [401, 403]:
            tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: {ml.ctr(request, 'invalid_api_token')}"
        elif r.status_code // 100 != 2:
            try:
                resp = json.loads(r.text)
                if "error" in resp.keys() and resp["error"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{resp['error']}`"
                elif "message" in resp.keys() and resp["message"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + resp["message"] + "`"
                elif len(r.text) <= 64:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + r.text + "`"
                else:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())
                tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
    except:
        tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_timeout')}"
    return tracker_app_error

async def remove_driver(request, steamid):
    (app, dhrid) = (request.app, request.state.dhrid)
    tracker_app_error = ""
    try:
        if app.config.tracker == "tracksim":
            r = await arequests.delete(app, "https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + app.config.tracker_api_token}, dhrid = dhrid)
        elif app.config.tracker == "trucky":
            r = await arequests.delete(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid)}, headers = {"Authorization": "X-ACCESS-TOKEN " + app.config.tracker_api_token}, dhrid = dhrid)
        if app.config.tracker == "trucky" and resp["success"]:
            return ""
        if r.status_code in [401, 403]:
            tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: {ml.ctr(request, 'invalid_api_token')}"
        elif r.status_code // 100 != 2:
            try:
                resp = json.loads(r.text)
                if "error" in resp.keys() and resp["error"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{resp['error']}`"
                elif "message" in resp.keys() and resp["message"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + resp["message"] + "`"
                elif len(r.text) <= 64:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + r.text + "`"
                else:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())
                tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
    except:
        tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_timeout')}"
    return tracker_app_error
