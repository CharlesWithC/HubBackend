# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json

import multilang as ml
from functions import arequests, gensecret
from static import TRACKER


async def add_driver(request, steamid):
    (app, dhrid) = (request.app, request.state.dhrid)
    tracker_app_error = ""
    try:
        if app.config.tracker == "tracksim":
            r = await arequests.post(app, "https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + app.config.tracker_api_token}, dhrid = dhrid)
        elif app.config.tracker == "trucky":
            await app.db.execute(dhrid, f"SELECT name, email FROM user WHERE steamid = {steamid}")
            t = await app.db.fetchall(dhrid)
            email = t[0][1]
            if email is None or "@" not in email:
                email = gensecret(8) + "@example.com"
            r = await arequests.post(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid), "name": t[0][0], "email": email}, headers = {"X-ACCESS-TOKEN": app.config.tracker_api_token, "User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
        if app.config.tracker == "tracksim":
            if r.status_code != 200:
                try:
                    resp = json.loads(r.text)
                    if "error" in resp.keys() and resp["error"] is not None:
                        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{resp['error']}`"
                    else:
                        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
                except:
                    tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
        elif app.config.tracker == "trucky":
            try:
                resp = json.loads(r.text)
                if not resp["success"]:
                    tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `" + resp["message"] + "`"
            except:
                tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
    except:
        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_timeout')}"
    return tracker_app_error

async def remove_driver(request, steamid):
    (app, dhrid) = (request.app, request.state.dhrid)
    tracker_app_error = ""
    try:
        if app.config.tracker == "tracksim":
            r = await arequests.delete(app, "https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + app.config.tracker_api_token}, dhrid = dhrid)
        elif app.config.tracker == "trucky":
            r = await arequests.delete(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid)}, headers = {"X-ACCESS-TOKEN": app.config.tracker_api_token, "User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
        if app.config.tracker == "tracksim":
            if r.status_code != 200:
                try:
                    resp = json.loads(r.text)
                    if "error" in resp.keys() and resp["error"] is not None:
                        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{resp['error']}`"
                    else:
                        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
                except:
                    tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
        elif app.config.tracker == "trucky":
            try:
                resp = json.loads(r.text)
                if not resp["success"]:
                    tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `" + resp["message"] + "`"
            except:
                tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
    except:
        tracker_app_error = f"{TRACKER[app.config.tracker]} {ml.ctr(request, 'api_timeout')}"
    return tracker_app_error
