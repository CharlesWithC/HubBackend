# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import random
import traceback
from datetime import datetime, timezone
from random import randint

import multilang as ml
from functions import arequests, gensecret, point2rank
from functions.dataop import *
from functions.notification import *
from functions.userinfo import *
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
                r = await arequests.post(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid), "name": t[0][0], "email": email}, headers = {"X-ACCESS-TOKEN": tracker["api_token"]}, dhrid = dhrid)
            if tracker["type"] == "tracksim":
                if r.status_code != 200:
                    try:
                        resp = r.json()
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
                    resp = r.json()
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
                r = await arequests.delete(app, "https://e.truckyapp.com/api/v1/drivershub/members", data = {"steam_id": str(steamid)}, headers = {"X-ACCESS-TOKEN": tracker["api_token"]}, dhrid = dhrid)
            if tracker["type"] == "tracksim":
                if r.status_code != 200:
                    try:
                        resp = r.json()
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
                    resp = r.json()
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

async def publish_webhook(request, userid, username, discordid, logid, tracker, data, original_data, event_type, driven_distance, revenue, offence):
    app = request.app

    try:
        source_city = data["source_city"]
        source_company = data["source_company"]
        destination_city = data["destination_city"]
        destination_company = data["destination_company"]
        if source_city is None or source_city["name"] is None:
            source_city = "N/A"
        else:
            source_city = source_city["name"]
        if source_company is None or source_company["name"] is None:
            source_company = "N/A"
        else:
            source_company = source_company["name"]
        if destination_city is None or destination_city["name"] is None:
            destination_city = "N/A"
        else:
            destination_city = destination_city["name"]
        if destination_company is None or destination_company["name"] is None:
            destination_company = "N/A"
        else:
            destination_company = destination_company["name"]
        cargo = "N/A"
        cargo_mass = 0
        if data["cargo"] is not None and data["cargo"]["name"] is not None:
            cargo = data["cargo"]["name"]
        if data["cargo"] is not None and data["cargo"]["mass"] is not None:
            cargo_mass = data["cargo"]["mass"]
        omultiplayer = data["multiplayer"]
        multiplayer = ""
        umultiplayer = ""
        if omultiplayer is None:
            multiplayer = ml.ctr(request, "single_player")
        else:
            if omultiplayer["type"] == "truckersmp":
                if omultiplayer["meta"]["server"] is not None:
                    multiplayer = "TruckersMP (" + omultiplayer["meta"]["server"] +")"
                else:
                    multiplayer = "TruckersMP"
            elif omultiplayer["type"] == "multiplayer":
                multiplayer = ml.ctr(request, "scs_convoy")
        uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
        language = await GetUserLanguage(request, uid)
        if omultiplayer is None:
            umultiplayer = ml.tr(request, "single_player", force_lang = language)
        else:
            if omultiplayer["type"] == "truckersmp":
                if omultiplayer["meta"]["server"] is not None:
                    umultiplayer = "TruckersMP (" + omultiplayer["meta"]["server"] +")"
                else:
                    umultiplayer = "TruckersMP"
            elif omultiplayer["type"] == "multiplayer":
                umultiplayer = ml.tr(request, "scs_convoy", force_lang = language)
        truck = data["truck"]
        if truck is not None and truck["brand"]["name"] is not None and truck["name"] is not None:
            truck = truck["brand"]["name"] + " " + truck["name"]
        else:
            truck = "N/A"
        fuel_used = data["fuel_used"]
        xp = 0
        if "earnedXP" in data["events"][-1]["meta"]:
            xp = data["events"][-1]["meta"]["earnedXP"]

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
        munit = "€"
        game = data["game"]["short_name"]
        if not game.startswith("e"):
            munit = "$"
        offence = -offence

        IMGS = app.config.delivery_webhook_image_urls
        if len(IMGS) == 0:
            IMGS = [""]
        k = randint(0, len(IMGS)-1)
        imgurl = IMGS[k]
        if not isurl(imgurl):
            imgurl = ""
        dhulink = app.config.frontend_urls.member.replace("{userid}", str(userid))
        dlglink = app.config.frontend_urls.delivery.replace("{logid}", str(logid))

        if app.config.distance_unit == "imperial":
            dist_val, dist_unit = int(driven_distance * 0.621371), "mi"
            fuel_val, fuel_unit = int(fuel_used * 0.26417205), "gal"
            cargo_val, cargo_unit = int(cargo_mass * 0.00110231), "t" # US Ton
        else:
            dist_val, dist_unit = int(driven_distance), "km"
            fuel_val, fuel_unit = int(fuel_used), "l"
            cargo_val, cargo_unit = int(cargo_mass / 1000), "t" # Metric Tonne

        embed_data = {"embeds": [{
            "title": f"{ml.ctr(request, 'delivery')} #{logid}",
            "url": dlglink,
            "fields": [
                {"name": ml.ctr(request, "driver"), "value": f"[{username}]({dhulink})", "inline": True},
                {"name": ml.ctr(request, "truck"), "value": truck, "inline": True},
                {"name": ml.ctr(request, "cargo"), "value": f"{cargo} ({cargo_val}{cargo_unit})", "inline": True},
                {"name": ml.ctr(request, "from"), "value": f"{source_company}, {source_city}", "inline": True},
                {"name": ml.ctr(request, "to"), "value": f"{destination_company}, {destination_city}", "inline": True},
                {"name": ml.ctr(request, "distance"), "value": f"{tseparator(dist_val)}{dist_unit}", "inline": True},
                {"name": ml.ctr(request, "fuel"), "value": f"{tseparator(fuel_val)} {fuel_unit}", "inline": True},
                {"name": ml.ctr(request, "net_profit"), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                {"name": ml.ctr(request, "xp_earned"), "value": f"{tseparator(xp)}", "inline": True}
                    if tracker != "trucky"
                    else {"name": ml.ctr(request, "time_spent"), "value": original_data["data"]["duration"], "inline": True}
            ],
            "footer": {"text": multiplayer},
            "color": int(app.config.hex_color, 16),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image": {"url": imgurl}
        }]}

        try:
            if app.config.hook_delivery_log.channel_id != "":
                durl = f"https://discord.com/api/v10/channels/{app.config.hook_delivery_log.channel_id}/messages"
                key = app.config.hook_delivery_log.channel_id
            elif app.config.hook_delivery_log.webhook_url != "":
                durl = app.config.hook_delivery_log.webhook_url
                key = app.config.hook_delivery_log.webhook_url
            opqueue.queue(app, "post", key, durl, json.dumps(embed_data), headers, "disable")
        except:
            pass

        uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
        language = await GetUserLanguage(request, uid)
        embed_data = {"embeds": [{
            "title": f"{ml.tr(request, 'delivery', force_lang = language)} #{logid}",
            "url": dlglink,
            "fields": [
                {"name": ml.tr(request, "driver", force_lang = language), "value": f"[{username}]({dhulink})", "inline": True},
                {"name": ml.tr(request, "truck", force_lang = language), "value": truck, "inline": True},
                {"name": ml.tr(request, "cargo", force_lang = language), "value": f"{cargo} ({cargo_val}{cargo_unit})", "inline": True},
                {"name": ml.tr(request, "from", force_lang = language), "value": f"{source_company}, {source_city}", "inline": True},
                {"name": ml.tr(request, "to", force_lang = language), "value": f"{destination_company}, {destination_city}", "inline": True},
                {"name": ml.tr(request, "distance", force_lang = language), "value": f"{tseparator(dist_val)}{dist_unit}", "inline": True},
                {"name": ml.tr(request, "fuel", force_lang = language), "value": f"{tseparator(fuel_val)} {fuel_unit}", "inline": True},
                {"name": ml.tr(request, "net_profit", force_lang = language), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                {"name": ml.tr(request, "xp_earned", force_lang = language), "value": f"{tseparator(xp)}", "inline": True}
                    if tracker != "trucky"
                    else {"name": ml.tr(request, "time_spent", force_lang = language), "value": original_data["data"]["duration"], "inline": True}
            ],
            "footer": {"text": umultiplayer},
            "color": int(app.config.hex_color, 16),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "image": {"url": imgurl}
        }]}
        if await CheckNotificationEnabled(request, "dlog", uid):
            await SendDiscordNotification(request, uid, embed_data)
        await UpdateRoleConnection(request, discordid)

    except Exception as exc:
        from api import tracebackHandler
        await tracebackHandler(request, exc, traceback.format_exc())

async def process_challenge(request, userid, logid, data, driven_distance, offence, has_overspeed, enabled_realistic_settings):
    (app, dhrid) = (request.app, request.state.dhrid)

    from plugins.challenge import JOB_REQUIREMENT_DEFAULT, JOB_REQUIREMENTS

    try:
        await app.db.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
        current_distance = await app.db.fetchone(dhrid)
        current_distance = current_distance[0]
        current_distance = 0 if current_distance is None else int(current_distance)

        userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
        roles = userinfo["roles"]

        await app.db.execute(dhrid, f"SELECT challengeid, challenge_type, delivery_count, required_roles, reward_points, job_requirements, title \
            FROM challenge WHERE challengeid >= 0 AND \
            start_time <= {int(time.time())} AND end_time >= {int(time.time())} AND required_distance <= {current_distance}")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            try:
                challengeid = tt[0]
                challenge_type = tt[1]
                delivery_count = tt[2]
                required_roles = str2list(tt[3])[:100]
                reward_points = tt[4]
                job_requirements = tt[5]
                title = tt[6]

                rolesok = False
                if len(required_roles) == 0:
                    rolesok = True
                for r in required_roles:
                    if r in roles:
                        rolesok = True
                if not rolesok:
                    continue

                p = json.loads(decompress(job_requirements))
                jobreq = copy.deepcopy(JOB_REQUIREMENT_DEFAULT)
                for i in range(0,len(p)):
                    jobreq[JOB_REQUIREMENTS[i]] = p[i]

                if jobreq["minimum_distance"] != -1 and driven_distance < jobreq["minimum_distance"]:
                    continue
                if jobreq["maximum_distance"] != -1 and driven_distance > jobreq["maximum_distance"]:
                    continue

                if int(jobreq["minimum_seconds_spent"]) != -1 and data["time_spent"] < int(jobreq["minimum_seconds_spent"]):
                    continue
                if int(jobreq["maximum_seconds_spent"]) != -1 and data["time_spent"] > int(jobreq["maximum_seconds_spent"]):
                    continue

                planned_distance = data["planned_distance"]
                if jobreq["minimum_detour_percentage"] != -1 and (driven_distance / planned_distance) < float(jobreq["minimum_detour_percentage"]):
                    continue
                if jobreq["maximum_detour_percentage"] != -1 and (driven_distance / planned_distance) > float(jobreq["maximum_detour_percentage"]):
                    continue

                if jobreq["game"] != "" and data["game"]["short_name"] not in jobreq["game"].split(","):
                    continue

                source_city = data["source_city"]
                source_company = data["source_company"]
                destination_city = data["destination_city"]
                destination_company = data["destination_company"]
                if source_city is None or source_city["unique_id"] is None:
                    source_city = "[unknown]"
                else:
                    source_city = source_city["unique_id"]
                if source_company is None or source_company["unique_id"] is None:
                    source_company = "[unknown]"
                else:
                    source_company = source_company["unique_id"]
                if destination_city is None or destination_city["unique_id"] is None:
                    destination_city = "[unknown]"
                else:
                    destination_city = destination_city["unique_id"]
                if destination_company is None or destination_company["unique_id"] is None:
                    destination_company = "[unknown]"
                else:
                    destination_company = destination_company["unique_id"]
                if jobreq["source_city_id"] != "" and source_city not in jobreq["source_city_id"].split(","):
                    continue
                if jobreq["source_company_id"] != "" and source_company not in jobreq["source_company_id"].split(","):
                    continue
                if jobreq["destination_city_id"] != "" and destination_city not in jobreq["destination_city_id"].split(","):
                    continue
                if jobreq["destination_company_id"] != "" and destination_company not in jobreq["destination_company_id"].split(","):
                    continue
                if jobreq["market"] != "" and data["market"] not in jobreq["market"].split(","):
                    continue

                cargo = "[unknown]"
                cargo_mass = 0
                cargo_damage = 0
                if data["cargo"] is not None and data["cargo"]["unique_id"] is not None:
                    cargo = data["cargo"]["unique_id"]
                if data["cargo"] is not None and data["cargo"]["mass"] is not None:
                    cargo_mass = data["cargo"]["mass"]
                if data["cargo"] is not None and data["cargo"]["damage"] is not None:
                    cargo_damage = data["cargo"]["damage"]

                if jobreq["cargo_id"] != "" and cargo not in jobreq["cargo_id"].split(","):
                    continue
                if jobreq["minimum_cargo_mass"] != -1 and cargo_mass < jobreq["minimum_cargo_mass"]:
                    continue
                if jobreq["maximum_cargo_mass"] != -1 and cargo_mass > jobreq["maximum_cargo_mass"]:
                    continue
                if jobreq["minimum_cargo_damage"] != -1 and cargo_damage < jobreq["minimum_cargo_damage"]:
                    continue
                if jobreq["maximum_cargo_damage"] != -1 and cargo_damage > jobreq["maximum_cargo_damage"]:
                    continue

                if data["truck"] is not None:
                    truck_id = data["truck"]["unique_id"]
                    if jobreq["truck_id"] != "" and truck_id not in jobreq["truck_id"].split(","):
                        continue

                top_speed = data["truck"]["top_speed"] * 3.6
                fuel_used = data["fuel_used"]
                if jobreq["maximum_speed"] != -1 and top_speed > jobreq["maximum_speed"]:
                    continue
                if jobreq["minimum_fuel"] != -1 and fuel_used < jobreq["minimum_fuel"]:
                    continue
                if jobreq["maximum_fuel"] != -1 and fuel_used > jobreq["maximum_fuel"]:
                    continue

                adblue_used = data["adblue_used"]
                if jobreq["minimum_adblue"] != -1 and adblue_used < jobreq["minimum_adblue"]:
                    continue
                if jobreq["maximum_adblue"] != -1 and adblue_used > jobreq["maximum_adblue"]:
                    continue

                profit = float(data["events"][-1]["meta"]["revenue"])
                if jobreq["minimum_profit"] != -1 and profit < jobreq["minimum_profit"]:
                    continue
                if jobreq["maximum_profit"] != -1 and profit > jobreq["maximum_profit"]:
                    continue
                if jobreq["minimum_offence"] != -1 and abs(offence) < jobreq["minimum_offence"]:
                    continue
                if jobreq["maximum_offence"] != -1 and abs(offence) > jobreq["maximum_offence"]:
                    continue

                if not jobreq["allow_overspeed"] and has_overspeed:
                    continue

                auto_park = data["events"][-1]["meta"]["autoParked"]
                auto_load = data["events"][0]["meta"]["autoLoaded"]
                if not jobreq["allow_auto_park"] and auto_park:
                    continue
                if not jobreq["allow_auto_load"] and auto_load:
                    continue

                count = {"ferry": 0, "train": 0, "collision": 0, "teleport": 0, "tollgate": 0}
                toll_paid = 0
                for i in range(len(data["events"])):
                    e = data["events"][i]
                    if e["type"] == "tollgate":
                        toll_paid += e["meta"]["cost"]
                    if e["type"] in ["ferry", "train", "collision", "teleport", "tollgate"]:
                        count[e["type"]] += 1
                for k in ["ferry", "train", "collision", "teleport", "tollgate"]:
                    if jobreq[f"minimum_{k}"] != -1 and count[k] < jobreq[f"minimum_{k}"]:
                        continue
                    if jobreq[f"maximum_{k}"] != -1 and count[k] > jobreq[f"maximum_{k}"]:
                        continue
                if jobreq["minimum_toll_paid"] != -1 and toll_paid < jobreq["minimum_toll_paid"]:
                    continue
                if jobreq["maximum_toll_paid"] != -1 and toll_paid > jobreq["maximum_toll_paid"]:
                    continue

                is_late = data["is_late"]
                is_special = data["is_special"]
                if jobreq["must_not_be_late"] and is_late:
                    continue
                if jobreq["must_be_special"] and not is_special:
                    continue

                average_speed = int(data["truck"]["average_speed"])
                if jobreq["minimum_average_speed"] != -1 and jobreq["minimum_average_speed"] > average_speed:
                    continue
                if jobreq["maximum_average_speed"] != -1 and jobreq["maximum_average_speed"] < average_speed:
                    continue

                if data["driven_distance"] != 0:
                    average_fuel = data["fuel_used"] / data["driven_distance"]
                    if int(jobreq["minimum_average_fuel"]) != -1 and jobreq["minimum_average_fuel"] > average_fuel:
                        continue
                    if int(jobreq["maximum_average_fuel"]) != -1 and jobreq["maximum_average_fuel"] < average_fuel:
                        continue

                if jobreq["minimum_warp"] != -1 or jobreq["maximum_warp"] != -1:
                    if "warp" not in data:
                        continue
                    if jobreq["minimum_warp"] != -1 and jobreq["minimum_warp"] > data["warp"]:
                        continue
                    if jobreq["maximum_warp"] != -1 and jobreq["maximum_warp"] < data["warp"]:
                        continue

                if jobreq["enabled_realistic_settings"] != "":
                    required_realistic_settings = jobreq["enabled_realistic_settings"].split(",")
                    for attr in data["game"]["realistic_settings"].keys():
                        if data["game"]["realistic_settings"][attr] is True:
                            enabled_realistic_settings.append(attr)
                    for attr in required_realistic_settings:
                        if attr not in enabled_realistic_settings:
                            continue

                uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
                await notification(request, "challenge", uid, ml.tr(request, "delivery_accepted_by_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(request, uid)))
                await app.db.execute(dhrid, f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {int(time.time())})")
                await app.db.commit(dhrid)

                current_delivery_count = 0
                if challenge_type in [1,3]:
                    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                elif challenge_type == 2:
                    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
                elif challenge_type == 4:
                    await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                        INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                        WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
                elif challenge_type == 5:
                    await app.db.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                        INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                        WHERE challenge_record.challengeid = {challengeid}")
                current_delivery_count = await app.db.fetchone(dhrid)
                current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

                if current_delivery_count >= delivery_count:
                    if challenge_type in [1,4]:
                        await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                        t = await app.db.fetchall(dhrid)
                        if len(t) == 0:
                            await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                            await app.db.commit(dhrid)

                            userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
                            uid = userinfo["uid"]

                            await notification(request, "challenge", uid, ml.tr(request, "one_time_personal_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))

                            def setvar(msg):
                                return msg.replace("{mention}", f"<@{userinfo['discordid']}>").replace("{name}", userinfo['name']).replace("{userid}", str(userinfo['userid'])).replace("{uid}", str(userinfo['uid'])).replace("{avatar}", validateUrl(userinfo['avatar'])).replace("{id}", str(challengeid)).replace("{title}", title).replace("{earned_points}", str(reward_points))

                            for meta in app.config.challenge_completed_forwarding:
                                meta = Dict2Obj(meta)
                                if meta.webhook_url != "" or meta.channel_id != "":
                                    await AutoMessage(app, meta, setvar)

                    elif challenge_type == 3:
                        await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                        t = await app.db.fetchall(dhrid)
                        if current_delivery_count >= (len(t) + 1) * delivery_count:
                            await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                            await app.db.commit(dhrid)

                            userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
                            uid = userinfo["uid"]

                            await notification(request, "challenge", uid, ml.tr(request, "recurring_challenge_completed_status_added", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator((len(t)+1) * reward_points)}, force_lang = await GetUserLanguage(request, uid)))

                            def setvar(msg):
                                return msg.replace("{mention}", f"<@{userinfo['discordid']}>").replace("{name}", userinfo['name']).replace("{userid}", str(userinfo['userid'])).replace("{uid}", str(userinfo['uid'])).replace("{avatar}", validateUrl(userinfo['avatar'])).replace("{id}", str(challengeid)).replace("{title}", title).replace("{earned_points}", str(reward_points))

                            for meta in app.config.challenge_completed_forwarding:
                                meta = Dict2Obj(meta)
                                if meta.webhook_url != "" or meta.channel_id != "":
                                    await AutoMessage(app, meta, setvar)

                    elif challenge_type == 2:
                        await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
                        t = await app.db.fetchall(dhrid)
                        if len(t) == 0:
                            curtime = int(time.time())
                            await app.db.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                            t = await app.db.fetchall(dhrid)
                            usercnt = {}
                            for tt in t:
                                tuserid = tt[0]
                                if tuserid not in usercnt.keys():
                                    usercnt[tuserid] = 1
                                else:
                                    usercnt[tuserid] += 1
                            for tuserid in usercnt.keys():
                                s = usercnt[tuserid]
                                reward = round(reward_points * s / delivery_count)
                                await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")

                                userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
                                uid = userinfo["uid"]

                                await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

                                def setvar(msg):
                                    return msg.replace("{mention}", f"<@{userinfo['discordid']}>").replace("{name}", userinfo['name']).replace("{userid}", str(userinfo['userid'])).replace("{uid}", str(userinfo['uid'])).replace("{avatar}", validateUrl(userinfo['avatar'])).replace("{id}", str(challengeid)).replace("{title}", title).replace("{earned_points}", str(reward_points))

                                for meta in app.config.challenge_completed_forwarding:
                                    meta = Dict2Obj(meta)
                                    if meta.webhook_url != "" or meta.channel_id != "":
                                        await AutoMessage(app, meta, setvar)

                            await app.db.commit(dhrid)

                    elif challenge_type == 5:
                        await app.db.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
                        t = await app.db.fetchall(dhrid)
                        if len(t) == 0:
                            curtime = int(time.time())
                            await app.db.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                                INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                                WHERE challenge_record.challengeid = {challengeid} \
                                GROUP BY dlog.userid, challenge_record.userid")
                            t = await app.db.fetchall(dhrid)
                            usercnt = {}
                            totalcnt = 0
                            for tt in t:
                                totalcnt += tt[1]
                                tuserid = tt[0]
                                if tuserid not in usercnt.keys():
                                    usercnt[tuserid] = tt[1] - max(totalcnt - delivery_count, 0)
                                else:
                                    usercnt[tuserid] += tt[1] - max(totalcnt - delivery_count, 0)
                                if totalcnt >= delivery_count:
                                    break
                            for tuserid in usercnt.keys():
                                s = usercnt[tuserid]
                                reward = round(reward_points * s / delivery_count)
                                await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({tuserid}, {challengeid}, {reward}, {curtime})")

                                userinfo = await GetUserInfo(request, userid = userid, is_internal_function = True)
                                uid = userinfo["uid"]

                                await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))

                                def setvar(msg):
                                    return msg.replace("{mention}", f"<@{userinfo['discordid']}>").replace("{name}", userinfo['name']).replace("{userid}", str(userinfo['userid'])).replace("{uid}", str(userinfo['uid'])).replace("{avatar}", validateUrl(userinfo['avatar'])).replace("{id}", str(challengeid)).replace("{title}", title).replace("{earned_points}", str(reward_points))

                                for meta in app.config.challenge_completed_forwarding:
                                    meta = Dict2Obj(meta)
                                    if meta.webhook_url != "" or meta.channel_id != "":
                                        await AutoMessage(app, meta, setvar)

                            await app.db.commit(dhrid)

            except Exception as exc:
                from api import tracebackHandler
                await tracebackHandler(request, exc, traceback.format_exc())

    except Exception as exc:
        from api import tracebackHandler
        await tracebackHandler(request, exc, traceback.format_exc())

async def process_economy(request, userid, logid, data, driven_distance, revenue):
    (app, dhrid) = (request.app, request.state.dhrid)

    try:
        economy_revenue = round(revenue)
        if economy_revenue > 4294967296:
            economy_revenue = 4294967296
        truckid = convertQuotation(data["truck"]["unique_id"])
        truckid = truckid[len("vehicle."):] if truckid.startswith("vehicle.") else truckid

        isrented = False
        await app.db.execute(dhrid, f"SELECT vehicleid, garageid, slotid, damage, odometer FROM economy_truck WHERE (userid = {userid} OR assigneeid = {userid}) AND truckid = '{truckid}' AND status = 1 LIMIT 1")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            isrented = True
            economy_revenue = max(round(economy_revenue - app.config.economy.truck_rental_cost), 0)
            note = 'rented-truck'
        else:
            vehicleid = t[0][0]
            garageid = t[0][1]
            slotid = t[0][2]
            current_damage = t[0][3]
            current_odometer = t[0][4]
            note = f't{vehicleid}-income'

        driver_revenue = round(economy_revenue * (1 - app.config.economy.revenue_share_to_company))
        company_revenue = round(economy_revenue * app.config.economy.revenue_share_to_company)

        await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid} FOR UPDATE")
        driver_balance = nint(await app.db.fetchone(dhrid))
        await EnsureEconomyBalance(request, userid) if driver_balance == 0 else None
        await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {driver_revenue} WHERE userid = {userid}")
        await app.db.execute(dhrid, "SELECT balance FROM economy_balance WHERE userid = -1000 FOR UPDATE")
        company_balance = nint(await app.db.fetchone(dhrid))
        await EnsureEconomyBalance(request, -1000) if company_balance == 0 else None
        await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {company_revenue} WHERE userid = -1000")
        await app.db.commit(dhrid)

        uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
        user_language = await GetUserLanguage(request, uid)
        message = "  \n" + ml.tr(request, "economy_message_for_delivery", var = {"logid": logid}, force_lang = user_language)
        await notification(request, "economy", uid, ml.tr(request, "economy_received_transaction", var = {"amount": driver_revenue, "currency_name": app.config.economy.currency_name, "from_user": ml.tr(request, "client"), "from_userid": "N/A", "message": message}, force_lang = user_language))

        if not isrented:
            message = convertQuotation(f'dlog-{logid}/garage-{garageid}-{slotid}/revenue-{economy_revenue}')
        else:
            message = convertQuotation(f'dlog-{logid}/rental-{app.config.economy.truck_rental_cost}/revenue-{economy_revenue}')

        await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1003, {userid}, {driver_revenue}, '{note}', '{message}', NULL, {int(driver_balance + driver_revenue)}, {int(time.time())})")
        await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1003, -1000, {company_revenue}, 'c{note}', '{message}', NULL, {int(company_balance + company_revenue)}, {int(time.time())})")
        await app.db.commit(dhrid)

        if not isrented:
            truck_damage = data["truck"]["total_damage"]
            damage = 0
            for item in truck_damage.keys():
                damage += nfloat(truck_damage[item])

            damage = damage * app.config.economy.wear_ratio

            await app.db.execute(dhrid, f"UPDATE economy_truck SET odometer = odometer + {driven_distance}, damage = damage + {damage}, income = income + {economy_revenue} WHERE vehicleid = {vehicleid}")
            if current_damage + damage > app.config.economy.max_wear_before_service:
                await app.db.execute(dhrid, f"UPDATE economy_truck SET status = -1 WHERE vehicleid = {vehicleid}")
            if current_odometer + driven_distance > app.config.economy.max_distance_before_scrap:
                await app.db.execute(dhrid, f"UPDATE economy_truck SET status = -2 WHERE vehicleid = {vehicleid}")
            await app.db.commit(dhrid)

    except Exception as exc:
        from api import tracebackHandler
        await tracebackHandler(request, exc, traceback.format_exc())

TRACKER_MAP = {"tracksim": 2, "trucky": 3, "custom": 4, "unitracker": 5}
async def handle_new_job(request, original_data, converted_data, tracker, bypass_tracker_check = False):
    (app, dhrid) = (request.app, request.state.dhrid)
    await app.db.extend_conn(dhrid, 10)
    data = converted_data["data"]["object"]
    event_type = converted_data["type"]
    tracker_type = TRACKER_MAP[tracker]

    steamid = int(data["driver"]["steam_id"])
    await app.db.execute(dhrid, f"SELECT userid, name, uid, discordid, tracker_in_use, roles FROM user WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return (404, "User not found.")
    if t[0][0] == -1 or not checkPerm(app, str2list(t[0][5]), "driver"):
        return (404, "User not driver.")
    userid = t[0][0]
    username = t[0][1]
    uid = t[0][2]
    discordid = t[0][3]
    tracker_in_use = t[0][4]
    logid_tracker = data["id"] # logid in tracker platform
    if tracker_in_use != tracker_type and not bypass_tracker_check:
        return (403, "User has chosen to use another tracker.")

    duplicate = False # NOTE only for debugging purpose
    logid = -1
    await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {logid_tracker} AND tracker_type = {tracker_type}")
    o = await app.db.fetchall(dhrid)
    if len(o) > 0:
        duplicate = True
        logid = o[0][0]
        return (409, "Already logged.")

    driven_distance = float(data["driven_distance"])
    top_speed = round(data["truck"]["top_speed"] * 3.6, 2) # m/s => km/h
    fuel_used = data["fuel_used"]
    game = data["game"]["short_name"]
    gameid = 1 if game.startswith("e") else 2 # 1: euro, 2: dollar
    revenue = 0
    isdelivered = 0
    offence = 0
    if event_type == "job.delivered":
        revenue = float(data["events"][-1]["meta"]["revenue"])
        isdelivered = 1
        official_distance = float(data["events"][-1]["meta"]["distance"])
        # data differs too much => likely tracker error => garbage data => drop data
        if driven_distance < 0 or driven_distance > official_distance * 1.5:
            driven_distance = 0
    else:
        revenue = 0
        if "penalty" in data["events"][-1]["meta"].keys():
            revenue = -float(data["events"][-1]["meta"]["penalty"])
        driven_distance = 0

    allevents = data["events"]
    totalexpense = 0
    has_overspeed = False
    for eve in allevents:
        if eve["type"] == "fine":
            offence += int(eve["meta"]["amount"])
        elif eve["type"] in ["tollgate", "ferry", "train"]:
            totalexpense += int(eve["meta"]["cost"])
        elif eve["type"] == "speeding":
            if eve["meta"]["max_speed"] > eve["meta"]["speed_limit"]:
                has_overspeed = True
    revenue = revenue - offence - totalexpense

    delivery_rule_ok = True
    delivery_rule_key = ""
    delivery_rule_value = ""

    enabled_realistic_settings = []
    if "realistic_settings" in data["game"] and data["game"]["realistic_settings"] is not None:
        for attr in data["game"]["realistic_settings"].keys():
            if data["game"]["realistic_settings"][attr] is True:
                enabled_realistic_settings.append(attr)

    meta_revenue = revenue # metadata revenue (for aggregation only)
    if "action" in app.config_dict["delivery_rules"].keys() \
            and app.config_dict["delivery_rules"]["action"] != "keep_job":
        action = app.config_dict["delivery_rules"]["action"]
        delivery_rules = app.config_dict["delivery_rules"]

        if "max_speed" in delivery_rules.keys() and isint(delivery_rules["max_speed"]) and \
                top_speed > int(delivery_rules["max_speed"]) and \
                action == "block_job":
            delivery_rule_ok = False
            delivery_rule_key = "max_speed"
            delivery_rule_value = str(top_speed)

        if "max_profit" in delivery_rules.keys() and isint(delivery_rules["max_profit"]) and \
                revenue > int(delivery_rules["max_profit"]):
            if action == "block_job":
                delivery_rule_ok = False
                delivery_rule_key = "profit"
                delivery_rule_value = str(revenue)
            elif action == "drop_data":
                meta_revenue = 0

        if "warp" in data and data["warp"] is not None and \
                "max_warp" in delivery_rules.keys() and isint(delivery_rules["max_warp"]) and \
                data["warp"] > int(delivery_rules["max_warp"]) and action == "block_job":
            delivery_rule_ok = False
            delivery_rule_key = "warp"
            delivery_rule_value = str(data["warp"])

        if "realistic_settings" in data["game"] and data["game"]["realistic_settings"] is not None and \
                "required_realistic_settings" in delivery_rules.keys() and \
                isinstance(delivery_rules["required_realistic_settings"], list) and \
                action == "block_job":
            for attr in delivery_rules["required_realistic_settings"]:
                if attr not in enabled_realistic_settings:
                    delivery_rule_ok = False
                    delivery_rule_key = "required_realistic_settings"
                    delivery_rule_value = ",".join(delivery_rules["required_realistic_settings"])
                    break

    if not delivery_rule_ok:
        await AuditLog(request, uid, "dlog", ml.ctr(request, "delivery_blocked_due_to_rules", var = {"tracker": TRACKER['trucky'], "trackerid": logid_tracker, "rule_key": delivery_rule_key, "rule_value": delivery_rule_value}))
        await notification(request, "dlog", uid, ml.tr(request, "delivery_blocked_due_to_rules", var = {"tracker": TRACKER['trucky'], "trackerid": logid_tracker, "rule_key": delivery_rule_key, "rule_value": delivery_rule_value}, force_lang = await GetUserLanguage(request, uid)))
        return (403, "Blocked due to delivery rules.")

    if not duplicate:
        # check once again
        await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {logid_tracker} AND tracker_type = {tracker_type} FOR UPDATE")
        o = await app.db.fetchall(dhrid)
        if len(o) > 0:
            await app.db.commit(dhrid) # unlock table
            return (409, "Already logged.")

        await app.db.execute(dhrid, f"INSERT INTO dlog(userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({userid}, '{compress(json.dumps(converted_data,separators=(',', ':')))}', {top_speed}, {int(time.time())}, {isdelivered}, {meta_revenue}, {gameid}, {fuel_used}, {driven_distance}, {logid_tracker}, {tracker_type}, 0)")
        await app.db.commit(dhrid)
        await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
        logid = (await app.db.fetchone(dhrid))[0]

        source_city = "N/A"
        source_company = "N/A"
        destination_city = "N/A"
        destination_company = "N/A"
        if data["source_city"] is not None:
            source_city = data["source_city"]["name"]
        if data["source_company"] is not None:
            source_company = data["source_company"]["name"]
        if data["destination_city"] is not None:
            destination_city = data["destination_city"]["name"]
        if data["destination_company"] is not None:
            destination_company = data["destination_company"]["name"]
        cargo_name = "N/A"
        cargo_mass = 0
        if data["cargo"] is not None:
            cargo_name = data["cargo"]["name"]
            cargo_mass = min(data["cargo"]["mass"], 2147483647)
        await app.db.execute(dhrid, f"INSERT INTO dlog_meta(logid, source_city, source_company, destination_city, destination_company, cargo_name, cargo_mass) VALUES ({logid}, '{convertQuotation(source_city)}', '{convertQuotation(source_company)}', '{convertQuotation(destination_city)}', '{convertQuotation(destination_company)}', '{convertQuotation(cargo_name)}', {cargo_mass})")
        await app.db.commit(dhrid)

        uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
        await notification(request, "dlog", uid, ml.tr(request, "job_submitted", var = {"logid": logid}, force_lang = await GetUserLanguage(request, uid)), no_discord_notification = True)

        try:
            totalpnt = await GetPoints(request, userid, app.default_rank_type_point_types)
            if point2rank(app, "default", totalpnt) is not None:
                bonus = point2rank(app, "default", totalpnt)["distance_bonus"]
                rankname = point2rank(app, "default", totalpnt)["name"]

                if bonus is not None and type(bonus) is dict:
                    ok = True
                    if bonus["min_distance"] != -1 and driven_distance < bonus["min_distance"]:
                        ok = False
                    if bonus["max_distance"] != -1 and driven_distance > bonus["max_distance"]:
                        ok = False
                    if ok and random.uniform(0, 1) <= bonus["probability"]:
                        bonuspoint = 0
                        if bonus["type"] == "fixed_value":
                            bonuspoint = bonus["value"]
                        elif bonus["type"] == "fixed_percentage":
                            bonuspoint = round(bonus["value"] * driven_distance)
                        elif bonus["type"] == "random_value":
                            bonuspoint = random.randint(bonus["min"], bonus["max"])
                        elif bonus["type"] == "random_percentage":
                            bonuspoint = round(random.uniform(bonus["min"], bonus["max"]) * driven_distance)
                        if bonuspoint != 0:
                            await app.db.execute(dhrid, f"INSERT INTO bonus_point VALUES ({userid}, {bonuspoint}, 'auto:distance-bonus/{logid}', NULL, {int(time.time())})")
                            await app.db.commit(dhrid)
                            await notification(request, "bonus", uid, ml.tr(request, "earned_bonus_point", var = {"bonus_points": str(bonuspoint), "logid": logid, "rankname": rankname}, force_lang = await GetUserLanguage(request, uid)))

        except Exception as exc:
            from api import tracebackHandler
            await tracebackHandler(request, exc, traceback.format_exc())

    if isdelivered and not duplicate:
        if (app.config.hook_delivery_log.channel_id != "" or app.config.hook_delivery_log.webhook_url != "") \
                and app.config.discord_bot_token != "":
            await publish_webhook(request, userid, username, discordid, logid, tracker, data, original_data, event_type, driven_distance, revenue, offence)

        if "challenge" in app.config.plugins:
            await process_challenge(request, userid, logid, data, driven_distance, offence, has_overspeed, enabled_realistic_settings)

        if "economy" in app.config.plugins:
            await process_economy(request, userid, logid, data, driven_distance, revenue)

    return (logid, userid, gameid, logid_tracker)
