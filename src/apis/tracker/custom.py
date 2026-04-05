# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This accepts any custom tracker that uses TrackSim data format
# In addition to TrackSim's data format, `warp: int` is accepted
# under `data.object`, and `realistic_settings: dict[str, bool]`
# is accepted under `data.object.game`. These attributes are
# derived from data provided by Trucky.

import asyncio
import hashlib
import hmac
import json

from fastapi import Request, Response

import multilang as ml
from functions import *


async def FetchRoute(app, gameid, userid, logid, route):
    d = route
    t = []
    for i in range(len(d)-1):
        # auto complete route
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
    if "custom" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    webhook_signature = request.headers.get('signature')

    ip_ok = False
    needs_validate = False
    for tracker in app.config.trackers:
        if tracker["type"] != "custom":
            continue
        if type(tracker["ip_whitelist"]) == list and len(tracker["ip_whitelist"]) > 0:
            needs_validate = True
            if request.client.host in tracker["ip_whitelist"]:
                ip_ok = True
    if needs_validate and not ip_ok:
        response.status_code = 403
        await AuditLog(request, -999, "tracker", ml.ctr(request, "rejected_tracker_webhook_post_ip", var = {"tracker": "custom", "ip": request.client.host}))
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
        if tracker["type"] != "custom":
            continue
        if tracker["webhook_secret"] is not None and tracker["webhook_secret"] != "":
            needs_validate = True
            sig = hmac.new(tracker["webhook_secret"].encode(), msg=json.dumps(d).encode(), digestmod=hashlib.sha256).hexdigest()
            if webhook_signature is not None and hmac.compare_digest(sig, webhook_signature):
                sig_ok = True
    if needs_validate and not sig_ok:
        response.status_code = 403
        await AuditLog(request, -999, "tracker", ml.ctr(request, "rejected_tracker_webhook_post_signature", var = {"tracker": "custom", "ip": request.client.host}))
        return {"error": "Validation failed."}

    result = await handle_new_job(request, copy.deepcopy(d), copy.deepcopy(d), "custom")
    if len(result) == 2:
        response.status_code = result[0]
        return {"error": result[1]}

    (logid, userid, gameid, _) = result
    if "route" in app.config.plugins and "route" in d["data"]["object"].keys():
        route = d["data"]["object"]["route"]
        asyncio.create_task(FetchRoute(app, gameid, userid, logid, route))

    return Response(status_code = 204)
