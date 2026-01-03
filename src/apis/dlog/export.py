# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import time
import traceback
from io import BytesIO
from typing import Optional

import cysimdjson
from fastapi import Header, Request, Response
from fastapi.responses import StreamingResponse

from api import tracebackHandler
from functions import *


async def get_export(request: Request, response: Response, authorization: str = Header(None), \
        after: Optional[int] = None, before: Optional[int] = None, \
        include_ids: Optional[bool] = False, userid: Optional[int] = None):
    app = request.app
    running_export = nint(app.redis.get("running_export"))
    if time.time() - running_export <= 300:
        return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

    rl = await ratelimit(request, 'GET /dlog/export', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if userid is not None:
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {userid} AND userid >= 0")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}

    if after is None:
        after = 0
    if before is None:
        before = int(time.time())

    f = BytesIO()

    limit = ""
    if userid is not None:
        limit += f"AND dlog.userid = {userid}"

    app.redis.set("running_export", int(time.time()))

    if not include_ids:
        f.write(b"logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense_tollgate, expense_ferry, expense_train, expense_total, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park, warp\n")
    else:
        f.write(b"logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense_tollgate, expense_ferry, expense_train, expense_total, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park, warp\n")

    await app.db.execute(dhrid, f"SELECT COUNT(dlog.logid), MIN(dlog.logid), MAX(dlog.logid) FROM dlog WHERE timestamp >= {after} AND timestamp <= {before} {limit} AND logid >= 0")
    t = await app.db.fetchone(dhrid)
    count = nint(t[0])
    if count == 0:
        app.redis.set("running_export", 0)

        response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
        for k in rl[1].keys():
            response.headers[k] = rl[1][k]
        response.headers["Content-Disposition"] = "attachment; filename=export.csv"
        return response

    min_logid = nint(t[1])
    max_logid = nint(t[2])

    await app.db.execute(dhrid, "SELECT userid, name FROM user WHERE userid >= 0")
    t = await app.db.fetchall(dhrid)
    all_users = {}
    for tt in t:
        all_users[tt[0]] = tt[1]

    await app.db.execute(dhrid, "SELECT challengeid, title FROM challenge WHERE challengeid >= 0")
    t = await app.db.fetchall(dhrid)
    all_challenges = {}
    for tt in t:
        all_challenges[tt[0]] = tt[1]

    division_data = {} # logid: divisionid
    challenge_data = {} # logid: [challengeid, ...]
    await app.db.execute(dhrid, f"SELECT logid, divisionid FROM division WHERE logid >= {min_logid} AND logid <= {max_logid} AND division.status = 1")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        division_data[tt[0]] = tt[1]

    await app.db.execute(dhrid, f"SELECT logid, challengeid FROM challenge_record WHERE logid >= {min_logid} AND logid <= {max_logid}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        if tt[0] not in challenge_data.keys():
            challenge_data[tt[0]] = [tt[1]]
        else:
            challenge_data[tt[0]].append(tt[1])

    page_size = 5000
    total_pages = (max_logid - min_logid) // page_size + 1

    json_parser = cysimdjson.JSONParser()

    for page in range(total_pages):
        ok = False

        d = None

        for _ in range(0,3):
            # 3 retries
            try:
                await asyncio.sleep(0.1)
                await app.db.extend_conn(dhrid, 30)
                await app.db.execute(dhrid, f"SELECT dlog.logid, dlog.userid, dlog.topspeed, dlog.unit, dlog.profit, dlog.unit, dlog.fuel, dlog.distance, dlog.data, dlog.isdelivered, dlog.timestamp, dlog.tracker_type FROM dlog \
                    WHERE dlog.logid >= {min_logid + page * page_size} AND dlog.logid <= {min(min_logid + (page + 1) * page_size, max_logid)} {limit}")
                d = await app.db.fetchall(dhrid)
                ok = True
                break
            except:
                await asyncio.sleep(1)

        if not ok:
            app.redis.set("running_export", 0)

            del f
            return JSONResponse({"error": "Service Unavailable"}, status_code = 503)

        for di in range(len(d)):
            dd = d[di]
            logid = dd[0]

            division_id = (division_data[logid] if logid in division_data else None)
            division = ""
            if division_id is None:
                division_id = ""
            else:
                if division_id in app.division_name.keys():
                    division = app.division_name[division_id]

            challengeids = (challenge_data[logid] if logid in challenge_data else None)
            challengenames = []
            if challengeids is None:
                challengeids = []
                challengenames = []
            else:
                for cid in challengeids:
                    if cid in all_challenges.keys():
                        challengenames.append(all_challenges[cid])
                    else:
                        challengeids.remove(cid)

            challenge_id = ", ".join([str(x) for x in challengeids])
            challenge = ", ".join(challengenames)

            tracker = ""
            tracker_type = dd[11]
            if tracker_type == 1:
                tracker = "navio"
            elif tracker_type == 2:
                tracker = "tracksim"
            elif tracker_type == 3:
                tracker = "trucky"
            elif tracker_type == 4:
                tracker = "custom"
            elif tracker_type == 5:
                tracker = "unitracker"
            trackerid = 0
            game = ""
            if dd[3] == 1:
                game = "ets2"
            elif dd[3] == 2:
                game = "ats"

            time_submitted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dd[10]))
            start_time = "1970-01-01 00:00:00"
            stop_time = "1970-01-01 00:00:00"

            is_delivered = dd[9]

            user_id = dd[1]
            if user_id in all_users.keys():
                username = all_users[user_id]
            else:
                user_id = None
                username = ml.ctr(request, "unknown")

            source_city = ""
            source_city_id = ""
            source_company = ""
            source_company_id = ""
            destination_city = ""
            destination_city_id = ""
            destination_company = ""
            destination_company_id = ""

            logged_distance = dd[7]
            planned_distance = 0
            reported_distance = 0

            cargo = ""
            cargo_id = ""
            cargo_mass = 0
            cargo_damage = 0

            truck_brand = ""
            truck_brand_id = ""
            truck_name = ""
            truck_id = ""
            license_plate = ""
            license_plate_country = ""
            license_plate_country_id = ""

            warp = 1

            fuel = dd[6]
            avg_fuel = 0
            if logged_distance != 0:
                avg_fuel = round(fuel / logged_distance * 100, 2)
            adblue = 0
            max_speed = dd[2]
            avg_speed = 0

            revenue = 0
            expense_tollgate = 0
            expense_ferry = 0
            expense_train = 0
            expense_total = 0
            offence = 0
            net_profit = dd[4]

            xp = 0

            is_special = 0
            is_late = 0
            has_police_enabled = -1
            market = ""
            multiplayer = ""
            auto_load = 0
            auto_park = 0

            if dd[8] != "":
                try:
                    decompressed = decompress(dd[8])
                    data = json_parser.loads(decompressed)["data"]["object"]
                    first_event = data["events"][0]
                    last_event = data["events"][len(data["events"]) - 1] # cannot use "-1" due to cysimdjson standard

                    trackerid = data["id"]

                    start_time = data["start_time"]
                    stop_time = data["stop_time"]

                    if data["source_city"] is not None:
                        source_city = data["source_city"]["name"]
                        source_city_id = data["source_city"]["unique_id"]
                    if data["source_company"] is not None:
                        source_company = data["source_company"]["name"]
                        source_company_id = data["source_company"]["unique_id"]
                    if data["destination_city"] is not None:
                        destination_city = data["destination_city"]["name"]
                        destination_city_id = data["destination_city"]["unique_id"]
                    if data["destination_company"] is not None:
                        destination_company = data["destination_company"]["name"]
                        destination_company_id = data["destination_company"]["unique_id"]

                    planned_distance = data["planned_distance"]
                    if "distance" in last_event["meta"]:
                        reported_distance = last_event["meta"]["distance"]

                    if data["cargo"] is not None:
                        cargo = data["cargo"]["name"]
                        cargo_id = data["cargo"]["unique_id"]
                        cargo_mass = data["cargo"]["mass"]
                        cargo_damage = data["cargo"]["damage"]

                    if data["truck"] is not None:
                        truck = data["truck"]
                        if truck["brand"] is not None:
                            truck_brand = truck["brand"]["name"]
                            truck_brand_id = truck["brand"]["unique_id"]
                        truck_name = truck["name"]
                        truck_id = truck["unique_id"]
                        license_plate = truck["license_plate"]
                        if truck["license_plate_country"] is not None:
                            license_plate_country = truck["license_plate_country"]["name"]
                            license_plate_country_id = truck["license_plate_country"]["unique_id"]
                        avg_speed = truck["average_speed"]

                    adblue = data["adblue_used"]

                    if is_delivered:
                        if "revenue" in last_event["meta"].keys():
                            revenue = float(last_event["meta"]["revenue"])
                            if tracker_type == 1:
                                xp = float(last_event["meta"]["earned_xp"])
                                auto_load = last_event["meta"]["auto_load"]
                                auto_park = last_event["meta"]["auto_park"]
                            elif tracker_type == 2:
                                xp = float(last_event["meta"]["earnedXP"])
                                auto_load = first_event["meta"]["autoLoaded"]
                                if "autoParked" in last_event["meta"].keys():
                                    auto_park = last_event["meta"]["autoParked"]
                                elif "autoPark" in last_event["meta"].keys():
                                    auto_park = last_event["meta"]["autoPark"]
                                else:
                                    auto_park = False
                    else:
                        if "penalty" in last_event["meta"].keys():
                            revenue = -float(last_event["meta"]["penalty"])

                    auto_load = bool(auto_load)
                    auto_park = bool(auto_park)

                    allevents = data["events"]
                    for eve in allevents:
                        if eve["type"] == "fine":
                            offence += int(eve["meta"]["amount"])
                        elif eve["type"] == "tollgate":
                            expense_tollgate += int(eve["meta"]["cost"])
                            expense_total += int(eve["meta"]["cost"])
                        elif eve["type"] == "ferry":
                            expense_ferry += int(eve["meta"]["cost"])
                            expense_total += int(eve["meta"]["cost"])
                        elif eve["type"] == "train":
                            expense_train += int(eve["meta"]["cost"])
                            expense_total += int(eve["meta"]["cost"])

                    is_special = bool(data["is_special"])
                    is_late = bool(data["is_late"])
                    try:
                        if "had_police_enabled" in data["game"].keys():
                            if data["game"]["had_police_enabled"] is None:
                                has_police_enabled = "NULL"
                            else:
                                has_police_enabled = bool(data["game"]["had_police_enabled"])
                        elif "has_police_enabled" in data["game"].keys():
                            if data["game"]["has_police_enabled"] is None:
                                has_police_enabled = "NULL"
                            else:
                                has_police_enabled = bool(data["game"]["has_police_enabled"])
                        else:
                            has_police_enabled = "NULL"
                    except: # trucky does not have this data
                        has_police_enabled = "NULL"
                    market = data["market"]
                    if data["multiplayer"] is not None:
                        multiplayer = data["multiplayer"]["type"]

                    if "warp" in data.keys():
                        warp = data["warp"]

                except Exception as exc:
                    await tracebackHandler(request, exc, f"Regarding dlog #{logid}\n" + traceback.format_exc())

            if not include_ids:
                data = [logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense_tollgate, expense_ferry, expense_train, expense_total, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park, warp]
            else:
                data = [logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense_tollgate, expense_ferry, expense_train, expense_total, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park, warp]

            for i in range(len(data)):
                if data[i] is None:
                    data[i] = '""'
                else:
                    data[i] = '"' + str(data[i]) + '"'

            f.write(",".join(data).encode("utf-8"))
            f.write(b"\n")

    f.seek(0)

    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    response.headers["Content-Disposition"] = "attachment; filename=export.csv"

    app.redis.set("running_export", 0)

    return response
