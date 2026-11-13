# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import hmac
import json
import traceback
from datetime import datetime, timezone

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *


def normalize_job_payload(data):
    """Convert TrackSim payload variants to the native truck-job schema.

    Native ``job.*`` payloads already follow the shared schema and receive
    only compatibility aliases for documented TrackSim variants. Alternative
    payload families are converted in their own match case so the
    job-specific contracts remain independent.
    """
    # Validate the Coach Job conversion against a real payload once TrackSim
    # Tracker v2.3.0 is released.
    normalized = copy.deepcopy(data)
    event_type = normalized.get("type")
    match event_type:
        # Native truck payloads already use the shared schema. Fill only the
        # compatibility aliases that differ between TrackSim's documentation
        # and payloads observed in production.
        case "job.delivered" | "job.cancelled":
            job = normalized.get("data", {}).get("object")
            if not isinstance(job, dict):
                return normalized

            game = job.get("game")
            if isinstance(game, dict):
                game.setdefault("realistic_settings", {})

            multiplayer = job.get("multiplayer")
            if isinstance(multiplayer, dict) and "type" not in multiplayer and "mode" in multiplayer:
                multiplayer["type"] = multiplayer["mode"]

            events = job.get("events")
            if isinstance(events, list):
                for event in events:
                    if not isinstance(event, dict) or not isinstance(event.get("meta"), dict):
                        continue
                    meta = event["meta"]
                    if event.get("type") == "speeding":
                        meta.setdefault("max_speed", meta.get("speed"))
                    elif event.get("type") == "job.delivered" and "autoParked" not in meta and "autoPark" in meta:
                        meta["autoParked"] = meta["autoPark"]

            return normalized

        # TrackSim car payloads use car_job.* events and a car vehicle object.
        case "car_job.delivered" | "car_job.cancelled":
            # Car jobs currently expose these customer priority flags:
            # - cargo_handling
            # - time
            # - vehicle_appearance
            # They describe what matters to the customer, but the payload does
            # not include the resulting customer rating or all evaluation data.
            # Preserve them untouched for possible future use.
            normalized["tracksim_original_type"] = event_type
            normalized["type"] = "job.delivered" if event_type == "car_job.delivered" else "job.cancelled"

            job = normalized.get("data", {}).get("object")
            if not isinstance(job, dict) or not isinstance(job.get("car"), dict):
                return normalized

            # TrackSim starts a separate numeric ID sequence for each job
            # family. Keep truck IDs positive and encode alternative families
            # as -(raw_id * 256 + family_code). Car uses family code 1 and
            # Coach uses family code 2.
            normalized["tracksim_original_id"] = job["id"]
            job["id"] = -(int(job["id"]) * 256 + 1)

            # The shared tracker pipeline calls its generic vehicle field
            # "truck". Keep the original car object alongside the copy.
            job["truck"] = copy.deepcopy(job["car"])

            # These native truck fields have no equivalent in the car payload.
            job.setdefault("adblue_used", 0)
            job.setdefault("is_special", False)
            # The current frontend assumes that trailers[0] exists while
            # rendering delivery details. Use a neutral placeholder that is
            # ignored by trailer statistics and displayed as unavailable.
            job.setdefault("trailers", [{
                "brand": None,
                "name": None,
                "license_plate": None,
                "license_plate_country": None
            }])

            if isinstance(job.get("game"), dict):
                job["game"].setdefault("realistic_settings", {})
            if isinstance(job.get("cargo"), dict):
                # TrackSim cannot obtain a cargo mass for car jobs. These jobs
                # represent small express parcels or documents rather than the
                # vehicle's complete payload capacity, so use a modest default.
                cargo = job["cargo"]
                cargo.setdefault("mass", 100)
                cargo_name = cargo.get("name") or cargo.get("unique_id") or "N/A"
                cargo["name"] = f"Car: {cargo_name}"

            events = job.get("events")
            if not isinstance(events, list):
                return normalized

            # Normalize nested event names as well as the top-level event type.
            for event in events:
                if not isinstance(event, dict):
                    continue
                current_type = event.get("type")
                if isinstance(current_type, str) and current_type.startswith("car_job."):
                    event["type"] = "job." + current_type.removeprefix("car_job.")
                elif current_type == "speeding" and isinstance(event.get("meta"), dict):
                    # Car payloads document ``speed`` and ``speed_limit`` but
                    # do not guarantee the ``max_speed`` field consumed by the
                    # shared tracker pipeline.
                    event["meta"].setdefault("max_speed", event["meta"].get("speed"))

            # The shared pipeline expects the start event first and the event
            # matching the top-level job type last. TrackSim may append state
            # changes such as multiplayer.changed after delivery.
            start_event = next((event for event in events if isinstance(event, dict) and event.get("type") == "job.started"), None)
            final_event = next((event for event in reversed(events) if isinstance(event, dict) and event.get("type") == normalized["type"]), None)
            if start_event is not None and final_event is not None:
                events = [event for event in events if event is not start_event and event is not final_event]
                job["events"] = [start_event, *events, final_event]

                first_meta = start_event.setdefault("meta", {})
                if isinstance(first_meta, dict):
                    first_meta.setdefault("autoLoaded", False)

                final_meta = final_event.setdefault("meta", {})
                if isinstance(final_meta, dict):
                    final_meta.setdefault("autoParked", False)
                    final_meta.setdefault("earnedXP", 0)
                    if "distance" not in final_meta and "distance.km" in final_meta:
                        final_meta["distance"] = final_meta["distance.km"]

            return normalized

        # TrackSim calls these Coach Jobs in its documentation, while payload
        # identifiers use bus_job and the vehicle is stored in bus.
        case "bus_job.completed" | "bus_job.cancelled":
            normalized["tracksim_original_type"] = event_type
            normalized["type"] = "job.delivered" if event_type == "bus_job.completed" else "job.cancelled"

            job = normalized.get("data", {}).get("object")
            if not isinstance(job, dict) or not isinstance(job.get("bus"), dict):
                return normalized

            try:
                normalized["tracksim_original_id"] = job["id"]
                job["id"] = -(int(job["id"]) * 256 + 2)
            except (KeyError, TypeError, ValueError):
                return normalized

            bus = job["bus"]
            truck = copy.deepcopy(bus)
            truck["unique_id"] = truck.get("id")
            if isinstance(truck.get("brand"), dict):
                truck["brand"]["unique_id"] = truck["brand"].get("id")

            license_plate = truck.get("license_plate")
            if isinstance(license_plate, dict):
                country = license_plate.get("country")
                truck["license_plate"] = license_plate.get("text")
                if isinstance(country, dict):
                    truck["license_plate_country"] = {
                        "unique_id": country.get("id"),
                        "name": country.get("name")
                    }
                else:
                    truck["license_plate_country"] = None

            job["truck"] = truck
            job["fuel_used"] = bus.get("fuel_used", 0)
            job.setdefault("adblue_used", 0)
            job.setdefault("is_special", False)
            job["trailers"] = [{
                "brand": None,
                "name": None,
                "license_plate": None,
                "license_plate_country": None
            }]

            game = job.get("game")
            if not isinstance(game, dict):
                game = {}
                job["game"] = game
            game["short_name"] = "eut2"
            game["had_police_enabled"] = bool(game.get("config", {}).get("police_enabled", False))
            game.setdefault("realistic_settings", {})
            job["mods"] = game.get("mods", [])

            multiplayer = game.get("multiplayer")
            if not isinstance(multiplayer, dict) or multiplayer.get("mode") == "single_player":
                job["multiplayer"] = None
            else:
                mode = multiplayer.get("mode")
                job["multiplayer"] = {
                    "type": "multiplayer" if mode == "convoy" else mode,
                    "meta": multiplayer.get("meta", {})
                }

            source = job.get("source", {}).get("city")
            destination = job.get("destination", {}).get("city")
            job["source_city"] = {
                "unique_id": source.get("id"),
                "name": source.get("name") or "N/A"
            } if isinstance(source, dict) else {"unique_id": "", "name": "N/A"}
            job["destination_city"] = {
                "unique_id": destination.get("id"),
                "name": destination.get("name") or "N/A"
            } if isinstance(destination, dict) else {"unique_id": "", "name": "N/A"}
            job["source_company"] = {"unique_id": "coach_stop", "name": "Coach Stop"}
            job["destination_company"] = {"unique_id": "coach_stop", "name": "Coach Stop"}

            if event_type == "bus_job.completed":
                passenger_count = int(job.get("passengers_planned", 0))
            else:
                passenger_count = 0
                stops = job.get("stops", {})
                if isinstance(stops, dict) and isinstance(stops.get("items"), list):
                    for stop in stops["items"]:
                        if not isinstance(stop, dict):
                            continue
                        departure = stop.get("departure")
                        passengers = stop.get("passengers")
                        if isinstance(departure, dict) and departure.get("actual") is not None and isinstance(passengers, dict):
                            passenger_count += int(passengers.get("entering_planned", 0))

            satisfaction = job.get("satisfaction")
            final_satisfaction = satisfaction.get("final") if isinstance(satisfaction, dict) else None
            passenger_label = "passenger" if passenger_count == 1 else "passengers"
            cargo_name = f"Coach: {passenger_count} {passenger_label}"
            if final_satisfaction is not None:
                cargo_name += f", {float(final_satisfaction) * 100:.1f}% satisfaction"
            job["cargo"] = {
                "unique_id": "coach_passengers",
                "name": cargo_name,
                "mass": passenger_count * 75,
                "damage": 0
            }

            for key in ["start_time", "stop_time"]:
                if isinstance(job.get(key), (int, float)):
                    job[key] = datetime.fromtimestamp(job[key], timezone.utc).isoformat().replace("+00:00", "Z")

            events = job.get("events")
            if not isinstance(events, list):
                return normalized

            for event in events:
                if not isinstance(event, dict):
                    continue
                current_type = event.get("type")
                if current_type == "bus_job.started":
                    event["type"] = "job.started"
                elif current_type == "bus_job.completed":
                    event["type"] = "job.delivered"
                elif current_type == "bus_job.cancelled":
                    event["type"] = "job.cancelled"
                elif current_type == "speeding" and isinstance(event.get("meta"), dict):
                    event["meta"].setdefault("max_speed", event["meta"].get("speed"))

            start_event = next((event for event in events if isinstance(event, dict) and event.get("type") == "job.started"), None)
            final_event = next((event for event in reversed(events) if isinstance(event, dict) and event.get("type") == normalized["type"]), None)
            if start_event is not None and final_event is not None:
                events = [event for event in events if event is not start_event and event is not final_event]
                job["events"] = [start_event, *events, final_event]

                start_meta = start_event.setdefault("meta", {})
                if isinstance(start_meta, dict):
                    start_meta.setdefault("autoLoaded", False)

                final_meta = final_event.setdefault("meta", {})
                if isinstance(final_meta, dict):
                    final_meta.setdefault("autoParked", False)
                    final_meta["earnedXP"] = final_meta.get("earned.xp", 0)
                    if "distance" not in final_meta and "distance.km" in final_meta:
                        final_meta["distance"] = final_meta["distance.km"]

            return normalized

        # Unknown payload families are left untouched.
        case _:
            return normalized

async def FetchRoute(app, gameid, userid, logid, trackerid, request, dhrid = None, job_type = None):
    r = None
    match job_type:
        case "car_job.delivered" | "car_job.cancelled":
            route_job_type = "car"
        case "bus_job.completed" | "bus_job.cancelled":
            route_job_type = "bus"
        case _:
            route_job_type = "truck"

    for tracker in app.config.trackers:
        if tracker["type"] != "tracksim":
            continue
        try: # try multiple tracker's api token
            r = await arequests.get(app, f"https://api.tracksim.app/v2/jobs/{trackerid}/route?job_type={route_job_type}", headers = {"Authorization": f"Api-Key {tracker['api_token']}"}, timeout = 15, dhrid = dhrid)
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

    result = await handle_new_job(request, copy.deepcopy(d), normalize_job_payload(d), "tracksim")
    if len(result) == 2:
        response.status_code = result[0]
        return {"error": result[1]}

    (logid, userid, gameid, logid_tracker) = result
    if "route" in app.config.plugins:
        job = d.get("data", {}).get("object", {})
        asyncio.create_task(FetchRoute(app, gameid, userid, logid, job.get("id", logid_tracker), request, job_type = d.get("type")))

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

    await app.db.execute(dhrid, f"SELECT unit, tracker_type, trackerid, userid, data FROM dlog WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "delivery_log_not_found", force_lang = au["language"])}
    (gameid, tracker_type, trackerid, userid, stored_data) = t[0]

    if tracker_type != 2:
        response.status_code = 404
        return {"error": ml.tr(request, "tracker_must_be", var = {"tracker": "TrackSim"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT logid FROM telemetry WHERE logid = {logid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "route_already_fetched", force_lang = au["language"])}

    job_type = None
    route_trackerid = trackerid
    try:
        stored_payload = json.loads(decompress(stored_data))
        job_type = stored_payload.get("tracksim_original_type", stored_payload.get("type"))
        route_trackerid = stored_payload.get("tracksim_original_id", trackerid)
    except (TypeError, ValueError):
        pass

    r = await FetchRoute(app, gameid, userid, logid, route_trackerid, request, dhrid, job_type)

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
