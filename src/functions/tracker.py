# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json

import multilang as ml
from functions import arequests, gensecret, AuditLog
from static import TRACKER


async def add_driver(request, steamid, staff_uid, userid, username, trackers = ["tracksim", "trucky"]):
    (app, dhrid) = (request.app, request.state.dhrid)
    all_errors = ""
    for tracker in app.config.trackers:
        resp_error = ""
        plain_error = ""
        try:
            if tracker["type"] not in trackers:
                continue
            if tracker["type"] == "tracksim":
                r = await arequests.post(app, "https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + tracker["api_token"]}, dhrid = dhrid)
            elif tracker["type"] == "trucky":
                await app.db.execute(dhrid, f"SELECT name, email FROM user WHERE steamid = {steamid}")
                t = await app.db.fetchall(dhrid)
                email = t[0][1]
                if email is None or "@" not in email:
                    email = gensecret(8) + "@example.com"
                r = await arequests.post(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid), "name": t[0][0], "email": email}, headers = {"X-ACCESS-TOKEN": tracker["api_token"], "User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
            if tracker["type"] == "tracksim":
                if r.status_code != 200:
                    try:
                        resp = json.loads(r.text)
                        if "error" in resp.keys() and resp["error"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['error']}`"
                            plain_error = resp['error']
                        elif "message" in resp.keys() and resp["message"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['message']}`"
                            plain_error = resp['message']
                        elif "detail" in resp.keys() and resp["detail"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['detail']}`"
                            plain_error = resp['detail']
                        else:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                            plain_error = ml.ctr(request, 'unknown_error')
                    except:
                        resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                        plain_error = ml.ctr(request, 'unknown_error')
            elif tracker["type"] == "trucky":
                try:
                    resp = json.loads(r.text)
                    if not resp["success"]:
                        resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `" + resp["message"] + "`"
                        plain_error = resp["message"]
                except:
                    resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                    plain_error = ml.ctr(request, 'unknown_error')
        except:
            resp_error = f"{TRACKER[tracker['type']]} {ml.ctr(request, 'api_timeout')}"
            plain_error = ml.ctr(request, 'api_timeout')

        if resp_error != "":
            await AuditLog(request, staff_uid, "tracker", ml.ctr(request, "failed_to_add_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKER[tracker['type']], "error": resp_error}))
        else:
            await AuditLog(request, staff_uid, "tracker", ml.ctr(request, "added_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKER[tracker['type']]}))

        if plain_error != "":
            plain_error += "\n"
        all_errors += plain_error
    return all_errors

async def remove_driver(request, steamid, staff_uid, userid, username, trackers = ["tracksim", "trucky"]):
    (app, dhrid) = (request.app, request.state.dhrid)
    all_errors = ""
    for tracker in app.config.trackers:
        resp_error = ""
        plain_error = ""
        try:
            if tracker["type"] not in trackers:
                continue
            if tracker["type"] == "tracksim":
                r = await arequests.delete(app, "https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + tracker["api_token"]}, dhrid = dhrid)
            elif tracker["type"] == "trucky":
                r = await arequests.delete(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid)}, headers = {"X-ACCESS-TOKEN": tracker["api_token"], "User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
            if tracker["type"] == "tracksim":
                if r.status_code != 200:
                    try:
                        resp = json.loads(r.text)
                        if "error" in resp.keys() and resp["error"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['error']}`"
                            plain_error = resp['error']
                        elif "message" in resp.keys() and resp["message"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['message']}`"
                            plain_error = resp['message']
                        elif "detail" in resp.keys() and resp["detail"] is not None:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{resp['detail']}`"
                            plain_error = resp['detail']
                        else:
                            resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                            plain_error = ml.ctr(request, 'unknown_error')
                    except:
                        resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                        plain_error = ml.ctr(request, 'unknown_error')
            elif tracker["type"] == "trucky":
                try:
                    resp = json.loads(r.text)
                    if not resp["success"]:
                        resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `" + resp["message"] + "`"
                        plain_error = resp["message"]
                except:
                    resp_error = f"{ml.ctr(request, 'service_api_error', var = {'service': TRACKER[tracker['type']]})}: `{ml.ctr(request, 'unknown_error')}`"
                    plain_error = ml.ctr(request, 'unknown_error')
        except:
            resp_error = f"{TRACKER[tracker['type']]} {ml.ctr(request, 'api_timeout')}"
            plain_error = ml.ctr(request, 'api_timeout')

        if resp_error != "":
            await AuditLog(request, staff_uid, "tracker", ml.ctr(request, "failed_remove_user_from_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKER[tracker['type']], "error": resp_error}))
        else:
            await AuditLog(request, staff_uid, "tracker", ml.ctr(request, "removed_user_from_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKER[tracker['type']]}))

        if plain_error != "":
            plain_error += "\n"
        all_errors += plain_error
    return all_errors
