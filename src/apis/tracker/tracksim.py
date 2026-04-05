# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import hmac
import json
import traceback

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *

async def FetchRoute(app, gameid, userid, logid, trackerid, request, dhrid = None):
    r = None
    for tracker in app.config.trackers:
        if tracker["type"] != "tracksim":
            continue
        try: # try multiple tracker's api token
            r = await arequests.get(app, f"https://api.tracksim.app/v1/jobs/{trackerid}/route", headers = {"Authorization": f"Api-Key {tracker['api_token']}"}, timeout = 15, dhrid = dhrid)
        except:
            return {"error": f"{TRACKER['tracksim']} {ml.ctr(request, 'api_timeout')}"}
        if r.status_code == 200:
            # when request succeeds, exit
            # if fails, r will exit as None
            break
    if r is None: # tracksim is not being used as tracker
        return {"error": "Not Found"}
    if r.status_code != 200: # tracksim is being used as tracker but there's an error
        try:
            resp = r.json()
            if "error" in resp.keys() and resp["error"] is not None:
                return {"error": TRACKER['tracksim'] + " " + resp["error"]}
            elif "message" in resp.keys() and resp["message"] is not None:
                return {"error": TRACKER['tracksim'] + " " + resp["message"]}
            elif "detail" in resp.keys() and resp["detail"] is not None:
                return {"error": TRACKER['tracksim'] + " " + resp["detail"]}
            elif len(r.text) <= 64:
                return {"error": TRACKER['tracksim'] + " " + r.text}
            else:
                return {"error": TRACKER['tracksim'] + " " + ml.tr(request, "unknown_error")}
        except Exception as exc:
            await tracebackHandler(request, exc, traceback.format_exc())
            return {"error": TRACKER['tracksim'] + " " + ml.tr(request, "unknown_error")}

    d = r.json()
    t = []
    for i in range(len(d)-1):
        # auto complete route
        # NOTE: this is to ensure data points have same time interval
        # for animation purpose in frontend as 'time' property is not stored
        # however, animation has been dropped in v2->v3 upgrade
        # so technically this is no longer needed
        # but it has been kept for archaeology purpose
        dup = 1
        if int(d[i+1]["time"]-d[i]["time"]) >= 1:
            dup = min((d[i+1]["time"]-d[i]["time"]) * 2, 6)
        if dup == 1:
            t.append((float(d[i]["x"]), 0, float(d[i]["z"])))
        else:
            sx = float(d[i]["x"])
            sz = float(d[i]["z"])
            tx = float(d[i+1]["x"])
            tz = float(d[i+1]["z"])
            if abs(tx - sx) <= 50 and abs(tz - sz) <= 50:
                dx = (tx - sx) / dup
                dz = (tz - sz) / dup
                if dx <= 10 and dz <= 10:
                    t.append((float(d[i]["x"]), 0, float(d[i]["z"])))
                else:
                    for _ in range(dup):
                        t.append((sx, 0, sz))
                        sx += dx
                        sz += dz
            else:
                t.append((float(d[i]["x"]), 0, float(d[i]["z"])))

    if len(d) > 0:
        t.append((float(d[-1]["x"]), 0, float(d[-1]["z"])))

    data = f"{gameid},,v5;"
    cnt = 0
    lastx = 0
    lastz = 0
    idle = 0
    for tt in t:
        if round(tt[0]) - lastx == 0 and round(tt[2]) - lastz == 0:
            if cnt != 0:
                idle += 1
            continue
        else:
            if idle > 0:
                data += f"^{idle}^"
                idle = 0
        st = "ZYXWVUTSRQPONMLKJIHGFEDCBA0abcdefghijklmnopqrstuvwxyz"
        rx = (round(tt[0]) - lastx) + 26
        rz = (round(tt[2]) - lastz) + 26
        if rx >= 0 and rz >= 0 and rx <= 52 and rz <= 52:
            # using this method to compress data can save 60+% storage comparing with v4
            data += f"{st[rx]}{st[rz]}"
        else:
            data += f";{b62encode(round(tt[0]) - lastx)},{b62encode(round(tt[2]) - lastz)};"
        lastx = round(tt[0])
        lastz = round(tt[2])
        cnt += 1

    if dhrid is None:
        dhrid = genrid()
        await app.db.new_conn(dhrid, extra_time = 5, db_name = app.config.db_name)

    for _ in range(3):
        try:
            await app.db.execute(dhrid, f"SELECT logid FROM telemetry WHERE logid = {logid}")
            p = await app.db.fetchall(dhrid)
            if len(p) > 0:
                break

            await app.db.execute(dhrid, f"INSERT INTO telemetry VALUES ({logid}, '', {userid}, '{compress(data)}')")
            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)
            break
        except:
            await app.db.close_conn(dhrid)
            dhrid = genrid()
            await app.db.new_conn(dhrid, extra_time = 5, db_name = app.config.db_name)
            continue

    return True

async def post_update(response: Response, request: Request):
    app = request.app
    if "tracksim" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    webhook_signature = request.headers.get('tracksim-signature')

    ip_ok = False
    needs_validate = False
    for tracker in app.config.trackers:
        if tracker["type"] != "tracksim":
            continue
        if type(tracker["ip_whitelist"]) == list and len(tracker["ip_whitelist"]) > 0:
            needs_validate = True
            if request.client.host in tracker["ip_whitelist"]:
                ip_ok = True
    if needs_validate and not ip_ok:
        response.status_code = 403
        await AuditLog(request, -999, "tracker", ml.ctr(request, "rejected_tracker_webhook_post_ip", var = {"tracker": "TrackSim", "ip": request.client.host}))
        return {"error": "Validation failed."}

    if request.headers.get("Content-Type") == "application/x-www-form-urlencoded":
        d = await request.form()
    elif request.headers.get("Content-Type") == "application/json":
        d = await request.json()
    else:
        response.status_code = 400
        return {"error": "Unsupported content type."}
    sig_ok = False
    needs_validate = False # if at least one tracker has webhook secret, then true (only false when all doesn't have webhook secret)
    for tracker in app.config.trackers:
        if tracker["type"] != "tracksim":
            continue
        if tracker["webhook_secret"] is not None and tracker["webhook_secret"] != "":
            needs_validate = True
            sig = hmac.new(tracker["webhook_secret"].encode(), msg=json.dumps(d).encode(), digestmod=hashlib.sha256).hexdigest()
            if webhook_signature is not None and hmac.compare_digest(sig, webhook_signature):
                sig_ok = True
    if needs_validate and not sig_ok:
        response.status_code = 403
        await AuditLog(request, -999, "tracker", ml.ctr(request, "rejected_tracker_webhook_post_signature", var = {"tracker": "TrackSim", "ip": request.client.host}))
        return {"error": "Validation failed."}

    result = await handle_new_job(request, copy.deepcopy(d), copy.deepcopy(d), "tracksim")
    if len(result) == 2:
        response.status_code = result[0]
        return {"error": result[1]}

    (logid, userid, gameid, logid_tracker) = result
    if "route" in app.config.plugins:
        asyncio.create_task(FetchRoute(app, gameid, userid, logid, logid_tracker, request))

    return Response(status_code = 204)

async def post_update_route(response: Response, request: Request, authorization: str = Header(None)):
    app = request.app
    if "tracksim" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /tracksim/update/route', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        logid = data["logid"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT unit, tracker_type, trackerid, userid FROM dlog WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    (gameid, tracker_type, trackerid, userid) = t[0]

    if tracker_type != 2:
        response.status_code = 404
        return {"error": ml.tr(request, "tracker_must_be", var = {"tracker": "TrackSim"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT logid FROM telemetry WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "route_already_fetched", force_lang = au["language"])}

    r = await FetchRoute(app, gameid, userid, logid, trackerid, request, dhrid)

    if r is True:
        return Response(status_code=204)
    else:
        response.status_code = 503
        return r

async def put_driver(response: Response, request: Request, userid: int, authorization: str = Header(None)):
    app = request.app
    if "tracksim" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /tracksim/driver', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
    if userinfo["uid"] is None:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    tracker_app_error = await add_driver(request, userinfo["steamid"], au["uid"], userid, userinfo["name"], trackers = ["tracksim"])

    if tracker_app_error == "":
        return Response(status_code=204)
    else:
        response.status_code = 503
        return {"error": tracker_app_error}

async def delete_driver(response: Response, request: Request, userid: int, authorization: str = Header(None)):
    app = request.app
    if "tracksim" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /tracksim/driver', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
    if userinfo["uid"] is None:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    tracker_app_error = await remove_driver(request, userinfo["steamid"], au["uid"], userid, userinfo["name"], trackers = ["tracksim"])

    if tracker_app_error == "":
        return Response(status_code=204)
    else:
        response.status_code = 503
        return {"error": tracker_app_error}
