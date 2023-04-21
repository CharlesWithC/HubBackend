# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback
from io import BytesIO
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import StreamingResponse

from functions import *
from api import tracebackHandler


async def get_export(request: Request, response: Response, authorization: str = Header(None), \
        after: Optional[int] = None, before: Optional[int] = None, \
        include_ids: Optional[bool] = False, userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)
    
    if userid is not None:
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {userid} AND userid >= 0")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found")}

    rl = await ratelimit(request, 'GET /dlog/export', 300, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if after is None:
        after = 0
    if before is None:
        before = max(int(time.time()), 32503651200)
    
    limit = ""
    if userid is not None:
        limit += f"AND dlog.userid = {userid}"

    time.time()
    f = BytesIO()
    if not include_ids:
        f.write(b"logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park\n")
    else:
        f.write(b"logid, tracker, trackerid, game, time_submitted, start_time, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park\n")
    await app.db.execute(dhrid, f"SELECT dlog.logid, dlog.userid, dlog.topspeed, dlog.unit, dlog.profit, dlog.unit, dlog.fuel, dlog.distance, dlog.data, dlog.isdelivered, dlog.timestamp, division.divisionid, challenge_info.challengeid, challenge.title, dlog.tracker_type FROM dlog \
        LEFT JOIN division ON dlog.logid = division.logid AND division.status = 1 \
        LEFT JOIN (SELECT challengeid, logid FROM challenge_record) challenge_info ON challenge_info.logid = dlog.logid \
        LEFT JOIN challenge ON challenge.challengeid = challenge_info.challengeid \
        WHERE dlog.timestamp >= {after} AND dlog.timestamp <= {before} {limit} AND dlog.logid >= 0")
    d = await app.db.fetchall(dhrid)
    for di in range(len(d)):
        dd = d[di]
        logid = dd[0]

        division_id = dd[11]
        division = ""
        if division_id is None:
            division_id = ""
        else:
            if division_id in app.division_name.keys():
                division = app.division_name[division_id]

        challengeids = dd[12]
        challengenames = dd[13]
        if challengeids is None:
            challengeids = []
            challengenames = []
        else:
            challengeids = [str(dd[12])]
            challengenames = [dd[13]]
            while di + 1 < len(d):
                if d[di + 1][0] == logid: # same log => multiple challenge id
                    challengeids.append(str(d[di+1][12]))
                    challengenames.append(d[di+1][13])
                    di += 1
                else:
                    break
        
        challenge_id = ", ".join(challengeids)
        challenge = ", ".join(challengenames)

        tracker = ""
        tracker_type = dd[14]
        if tracker_type == 1:
            tracker = "navio"
        elif tracker_type == 2:
            tracker = "tracksim"
        trackerid = 0
        game = ""
        if dd[3] == 1:
            game = "ets2"
        elif dd[3] == 2:
            game = "ats"

        time_submitted = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(dd[10]))
        after = "1970-01-01 00:00:00"
        stop_time = "1970-01-01 00:00:00"

        is_delivered = dd[9]

        user_id = dd[1]
        user = await GetUserInfo(request, userid = user_id, tell_deleted = True)
        username = user["name"]
        if "is_deleted" in user.keys():
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
        
        fuel = dd[6]
        avg_fuel = 0
        if logged_distance != 0:
            avg_fuel = round(fuel / logged_distance * 100, 2)
        adblue = 0
        max_speed = dd[2]
        avg_speed = 0

        revenue = 0
        expense = ""
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
                data = json.loads(decompress(dd[8]))["data"]["object"]
                first_event = data["events"][0]
                last_event = data["events"][-1]
                
                trackerid = data["id"]
                
                after = data["start_time"]
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
                    revenue = float(last_event["meta"]["revenue"])
                    if tracker_type == 1:
                        xp = float(last_event["meta"]["earned_xp"])
                        auto_load = last_event["meta"]["auto_load"]
                        auto_park = last_event["meta"]["auto_park"]
                    elif tracker_type == 2:
                        xp = float(last_event["meta"]["earnedXP"])
                        auto_load = first_event["meta"]["autoLoaded"]
                        auto_park = last_event["meta"]["autoParked"]
                else:
                    revenue = -float(last_event["meta"]["penalty"])
                
                expensedict = {"tollgate": 0, "ferry": 0, "train": 0, "total": 0}
                allevents = data["events"]
                for eve in allevents:
                    if eve["type"] == "fine":
                        offence += int(eve["meta"]["amount"])
                    elif eve["type"] in ["tollgate", "ferry", "train"]:
                        expensedict[eve["type"]] += int(eve["meta"]["cost"])
                        expensedict["total"] += int(eve["meta"]["cost"])
                for k, v in expensedict.items():
                    expense += f"{k}: {v}, "
                expense = expense[:-2]

                is_special = int(data["is_special"])
                is_late = int(data["is_late"])
                if "had_police_enabled" in data["game"].keys():
                    has_police_enabled = int(data["game"]["had_police_enabled"])
                elif "has_police_enabled" in data["game"].keys():
                    has_police_enabled = int(data["game"]["has_police_enabled"])
                market = data["market"]
                if data["multiplayer"] is not None:
                    multiplayer = data["multiplayer"]["type"]

            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())

        if not include_ids:
            data = [logid, tracker, trackerid, game, time_submitted, after, stop_time, is_delivered, user_id, username, source_company, source_city, destination_company, destination_city, logged_distance, planned_distance, reported_distance, cargo, cargo_mass, cargo_damage, truck_brand, truck_name, license_plate, license_plate_country, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, challenge, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park]
        else:
            data = [logid, tracker, trackerid, game, time_submitted, after, stop_time, is_delivered, user_id, username, source_company, source_company_id, source_city, source_city_id, destination_company, destination_company_id, destination_city, destination_city_id, logged_distance, planned_distance, reported_distance, cargo, cargo_id, cargo_mass, cargo_damage, truck_brand, truck_brand_id, truck_name, truck_id, license_plate, license_plate_country, license_plate_country_id, fuel, avg_fuel, adblue, max_speed, avg_speed, revenue, expense, offence, net_profit, xp, division, division_id, challenge, challenge_id, is_special, is_late, has_police_enabled, market, multiplayer, auto_load, auto_park]

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
    response.headers["Content-Disposition"] = "attachment; filename=dlog.csv"

    return response