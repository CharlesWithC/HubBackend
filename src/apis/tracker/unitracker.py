# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import base64
import copy
import json
import zlib
from datetime import datetime, timezone

from fastapi import Request, Response

import multilang as ml
from functions import *


async def FetchRoute(app, gameid, userid, logid, route):
    d = json.loads(zlib.decompress(base64.b64decode(route.encode())).decode())
    t = []
    for i in range(len(d)-1):
        # no need for auto complete route
        # as time is not provided by tracker and frontend animation was dropped
        t.append((float(d[i]["X"]), 0, float(d[i]["Z"])))

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

def convert_format(data):
    if "Events" not in data: # malformed data
        return None
    last_event_name = data["Events"][-1]["name"]
    job_event_type_mapping = {"player.job.delivered": "job.delivered", "player.job.cancelled": "job.cancelled"}
    if last_event_name not in job_event_type_mapping.keys():
        return None
    job_event_type = job_event_type_mapping[last_event_name]

    d = copy.deepcopy(data["JobData"])

    multiplayer = None
    if d["isMultiplayer"] == "1":
        # unitracker only supports truckersmp
        multiplayer = {"type": "truckersmp", "meta": {"server": d["serverName"] if d["serverName"] != "" else None}}

    job_damage = json.loads(d["job_damage"])
    current_damage = json.loads(d["current_damage"])

    events = []
    event_type_mapping = {"player.fined": "fine", "player.job.cancelled": "job.cancelled", "player.job.delivered": "job.delivered", "player.job.resumed": "job.resumed", "player.job.started": "job.started", "player.tollgate.paid": "tollgate", "player.truck.refuel": "refuel", "player.use.ferry": "transport", "player.use.repair": "repair", "player.use.train": "transport"}
    # transport needs to be handled manually
    # events.append({"location": None, "real_time": d["started_at"].split(".")[0]+"Z", "time": int(datetime.strptime(d["started_at"].split(".")[0]+"Z", "%Y-%m-%dT%H:%M:%SZ").timestamp()), "type": "job.started", "meta": {"autoLoaded": d["auto_load"]}})
    for event in data["Events"]:
        et = event_type_mapping[event["name"]]
        meta = {}
        if et == "fine":
            meta = {"offence": event["type"], "amount": int(event["amount"])}
        elif et == "tollgate":
            meta = {"cost": int(event["amount"])}
        elif et == "refuel":
            meta = {"amount": int(event["amount"])}
        elif et == "transport":
            et = event["name"].split(".")[-1] # ferry|train
            meta = {"cost": int(event["amount"]), "source_id": event["sourceID"], "source_name": event["source"], "target_id": event["targetID"], "target_name": event["target"]}
        elif et == "job.started":
            meta = {"autoLoaded": bool(int(d["autoLoadUsed"]))}
        elif et == "job.delivered":
            meta = {"revenue": int(d["income"]), "earnedXP": int(d["earnedXP"]), "cargoDamage": round(float(d["cargoDamage"]) / 100, 2), "distance": int(d["distanceDriven"]), "timeTaken": int(d["realTimeTaken"]), "autoParked": bool(int(d["autoParkUsed"]))}
        elif et == "job.cancelled":
            meta = {} # penalty not for unitracker
        events.append({"location": {"x": float(event["mapX"]), "mapZ": float(event["mapZ"])}, "real_time": event["currentTime"], "time": int(datetime.strptime(event["currentTime"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()), "type": et, "meta": meta})

    return {
        "object": "event",
        "type": job_event_type,
        "data": {
            "object": {
                "id": d["id"],
                "uuid": d["jobID"], # no hyphen included
                "object": "job",
                "driver": {
                    "steam_id": d["steamID"]
                },
                "start_time": d["realTimeStarted"],
                "stop_time": d["realTimeEnded"],
                "time_spent": int(d["realTimeTaken"]),
                "planned_distance": int(d["plannedDistance"]),
                "driven_distance": int(d["distanceDriven"]),
                "adblue_used": None, # not for unitracker
                "fuel_used": int(d["fuelStartJob"]) + int(d["truckRefueledAmount"]) - int(d["fuelEndJob"]),
                "is_special": bool(int(d["isSpecial"])),
                "is_late": bool(int(d["isLate"])),
                "market": d["jobMarket"],
                "cargo": {
                    "unique_id": d["cargoID"],
                    "name": d["cargo"],
                    "mass": int(d["cargoMass"]),
                    "damage": round(float(d["cargoDamage"]) / 100, 2)
                },
                "game": {
                    "short_name": "eut2" if d["gameID"] == "ETS2" else "ats",
                    "language": None, # not for unitracker
                    "had_police_enabled": bool(int(d["hasPoliceEnabled"]))
                },
                "multiplayer": multiplayer,
                "source_city": {
                    "unique_id": d["sourceCityID"],
                    "name": d["sourceCity"]
                },
                "source_company": {
                    "unique_id": d["sourceCompanyID"],
                    "name": d["sourceCompany"]
                },
                "destination_city": {
                    "unique_id": d["destinationCityID"],
                    "name": d["destinationCity"]
                },
                "destination_company": {
                    "unique_id": d["destinationCompanyID"],
                    "name": d["destinationCompany"]
                },
                "truck": {
                    "unique_id": d["truckModelID"],
                    "name": d["truck"],
                    "brand": {
                        "unique_id": d["truckMakeID"],
                        "name": d["truckMake"]
                    },
                    "fuel": int(d["fuelEndJob"]), # exclusive to unitracker
                    "initial_fuel": int(d["fuelStartJob"]), # exclusive to unitracker
                    "refueled_amount": int(d["truckRefueledAmount"]), # exclusive to unitracker
                    "fuel_consumption": float(d["truckRealConsumption"]), # exclusive to unitracker
                    "odometer": int(d["odometerEndJob"]),
                    "initial_odometer": int(d["odometerStartJob"]),
                    "wheel_count": int(d["truckWheelsCount"]),
                    "license_plate": d["truckLicensePlate"],
                    "license_plate_country": {
                        "unique_id": d["truckLicensePlateCountryID"],
                        "name": d["truckLicensePlateCountry"]
                    },
                    "current_damage": {
                        "cabin": round(current_damage["truck_cabin"] / 100, 4),
                        "chassis": round(current_damage["truck_chassis"] / 100, 4),
                        "engine": round(current_damage["truck_engine"] / 100, 4),
                        "transmission": round(current_damage["truck_transmission"] / 100, 4),
                        "wheels": round(current_damage["truck_wheels"] / 100, 4)
                    },
                    "total_damage": {
                        "cabin": round(job_damage["truck_cabin"] / 100, 4),
                        "chassis": round(job_damage["truck_chassis"] / 100, 4),
                        "engine": round(job_damage["truck_engine"] / 100, 4),
                        "transmission": round(job_damage["truck_transmission"] / 100, 4),
                        "wheels": round(job_damage["truck_wheels"] / 100, 4)
                    },
                    "top_speed": round(float(d["topSpeed"]) / 3.6, 2),
                    "average_speed": round(float(d["truckRealAverageSpeed"]) / 3.6, 2)
                },
                "trailers": [
                    {
                        "unique_id": d["trailerModelID"], # exclusive to unitracker
                        "name": d["trailerModel"],
                        "body_type": d["trailerBodyType"],
                        "chain_type": d["trailerChainType"],
                        "wheel_count": int(d["trailerWheelsCount"]),
                        "brand": {
                            "unique_id": d["trailerMakeID"],
                            "name": None # not for unitracker (tracksim also doesn't seem to provide this)
                        } if d["trailerMakeID"] != "" else None,
                        "license_plate": d["trailerLicensePlate"],
                        "license_plate_country": {
                            "unique_id": d["trailerLicensePlateCountryID"],
                            "name": d["trailerLicensePlateCountry"]
                        },
                        "current_damage": {
                            "body": current_damage["trailer_body"] / 100,
                            "cargo": current_damage["trailer_cargo"] / 100,
                            "chassis": current_damage["trailer_chassis"] / 100,
                            "wheels": current_damage["trailer_wheels"] / 100
                        },
                        "total_damage": {
                            "body": job_damage["trailer_body"] / 100,
                            "cargo": job_damage["trailer_cargo"] / 100,
                            "chassis": job_damage["trailer_chassis"] / 100,
                            "wheels": job_damage["trailer_wheels"] / 100
                        }
                    }
                ],
                "events": events,
                "mods": [],
            }
        }
    }

async def post_update(response: Response, request: Request):
    app = request.app
    if "unitracker" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    # NOTE: at the time of the release, unitracker does not support webhook signing
    # webhook_signature = request.headers.get('unitracker-signature')

    ip_ok = False
    needs_validate = False
    for tracker in app.config.trackers:
        if tracker["type"] != "unitracker":
            continue
        if type(tracker["ip_whitelist"]) == list and len(tracker["ip_whitelist"]) > 0:
            needs_validate = True
            if request.client.host in tracker["ip_whitelist"]:
                ip_ok = True
    if needs_validate and not ip_ok:
        response.status_code = 403
        await AuditLog(request, -999, "tracker", ml.ctr(request, "rejected_tracker_webhook_post_ip", var = {"tracker": "UniTracker", "ip": request.client.host}))
        return {"error": "Validation failed."}

    if request.headers.get("Content-Type") == "application/x-www-form-urlencoded":
        d = await request.form()
    elif request.headers.get("Content-Type") == "application/json":
        d = await request.json()
    else:
        response.status_code = 400
        return {"error": "Unsupported content type."}

    # note: unitracker does not sign webhook data, and so there is no signature check

    original_data = copy.deepcopy(d)
    converted_data = convert_format(copy.deepcopy(d))
    if converted_data is None:
        response.status_code = 400
        return {"error": "Only player.job.delivered and player.job.cancelled events are accepted."}

    result = await handle_new_job(request, original_data, converted_data, "unitracker")
    if len(result) == 2:
        response.status_code = result[0]
        return {"error": result[1]}

    (logid, userid, gameid, _) = result
    if "route" in app.config.plugins and "Route" in original_data and "route" in original_data["Route"]:
        asyncio.create_task(FetchRoute(app, gameid, userid, logid, original_data["Route"]["route"]))

    return Response(status_code = 204)
