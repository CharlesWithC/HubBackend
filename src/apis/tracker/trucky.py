# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import hashlib
import hmac
import json
import random
import time
import traceback
from datetime import datetime
from random import randint
from typing import Optional
from urllib.parse import parse_qs

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *
from plugins.challenge import JOB_REQUIREMENT_DEFAULT, JOB_REQUIREMENTS


def convert_format(data):
    job_event_type_mapping = {"job_completed": "job.delivered", "job_canceled": "job.cancelled"}
    if data["event"] not in job_event_type_mapping.keys():
        return None
    job_event_type = job_event_type_mapping[data["event"]]

    d = copy.deepcopy(data["data"])
    # first convert data
    convert_distance = ["driven_distance_km", "planned_distance_km", "max_speed_kmh", "vehicle_odometer_end_km", "vehicle_odometer_start_km"]
    if d["distance_unit"] == "mi":
        for key in convert_distance:
            if d[key] is None:
                if d["_".join(key.split("_")[:-1])] is None:
                    d[key] = 0
                else:
                    d[key] = d["_".join(key.split("_")[:-1])] * 1.609344
    elif d["distance_unit"] == "km":
        for key in convert_distance:
            if d[key] is None:
                d[key] = d["_".join(key.split("_")[:-1])]
    if d["real_driven_distance_km"] is None:
        d["real_driven_distance_km"] = d["driven_distance_km"]
    try:
        d["average_speed_kmh"] = round((d["real_driven_distance_km"] / (d["real_driving_time_seconds"] / 3600)) / d["max_map_scale"])
    except: # in case of division by zero
        d["average_speed_kmh"] = 0
    if d["volume_unit"] == "gal":
        if d["fuel_used_l"] is None:
            if d["fuel_used"] is None:
                d["fuel_used_l"] = 0
            else:
                d["fuel_used_l"] = d["fuel_used"] * 3.785412
    elif d["volume_unit"] == "l":
        if d["fuel_used_l"] is None:
            d["fuel_used_l"] = d["fuel_used"]
    multiplayer = None
    if d["game_mode"] != "sp":
        multiplayer = {"type": d["game_mode"], "meta": {"server": d["server"]}}
    cargo_details = d["cargo_definition"]
    if cargo_details is not None:
        del cargo_details["id"], cargo_details["name"], cargo_details["in_game_id"], cargo_details["game_id"], cargo_details["localized_names"]
    events = []
    event_type_mapping = {"teleport": "teleport", "truck_fixed": "repair", "job_resumed": "job.resumed", "fined": "fine", "tollgate_paid": "tollgate", "collision": "collision", "transport_used": "transport", "refuel": "refuel"}
    # transport needs to be handled manually
    events.append({"location": None, "real_time": d["started_at"].split(".")[0]+"Z", "time": int(datetime.strptime(d["started_at"].split(".")[0]+"Z", "%Y-%m-%dT%H:%M:%SZ").timestamp()), "type": "job.started", "meta": {"autoLoaded": d["auto_load"]}})
    for event in d["events"]:
        et = event_type_mapping[event["event_type"]]
        meta = {}
        if et == "fine":
            meta = event["attributes"]
        elif et == "tollgate":
            meta = {"cost": event["attributes"]["amount"]}
        elif et == "collision":
            meta = {"cargo_damage": round(event["attributes"]["damage"]["cargoDamage"] / 100, 2), "chassis_damage": round(event["attributes"]["damage"]["chassisDamage"] / 100, 2), "trailers_damage": round(event["attributes"]["damage"]["trailersDamage"] / 100, 2), "total_damage_difference": round(event["attributes"]["damage"]["totalDamageDifference"] / 100, 2)}
        elif et == "transport":
            et = event["attributes"]["transport_type"]
            meta = {"cost": event["attributes"]["amount"], "source_id": event["attributes"]["source_id"], "source_name": event["attributes"]["source"], "target_id": event["attributes"]["target_id"], "target_name": event["attributes"]["target"]}
        events.append({"location": {"x": event["x"], "y": event["y"], "z": event["z"]}, "real_time": event["created_at"].split(".")[0]+"Z", "time": int(datetime.strptime(event["created_at"].split(".")[0]+"Z", "%Y-%m-%dT%H:%M:%SZ").timestamp()), "type": et, "meta": meta})
    if job_event_type == "job.delivered":
        events.append({"location": None, "real_time": d["completed_at"].split(".")[0]+"Z", "time": int(datetime.strptime(d["completed_at"].split(".")[0]+"Z", "%Y-%m-%dT%H:%M:%SZ").timestamp()), "type": "job.delivered", "meta": {"revenue": d["income"], "revenue_details": d["income_details"], "earnedXP": None, "cargoDamage": round(d["cargo_damage"] / 100, 2), "distance": d["real_driven_distance_km"], "timeTaken": d["real_driving_time_seconds"], "autoParked": d["auto_park"]}}) # revenue_details is trucky exclusive
    elif job_event_type == "job.cancelled":
        events.append({"location": None, "real_time": d["canceled_at"].split(".")[0]+"Z", "time": int(datetime.strptime(d["canceled_at"].split(".")[0]+"Z", "%Y-%m-%dT%H:%M:%SZ").timestamp()), "type": "job.cancelled", "meta": {"penalty": d["income"]}})
    if d["warp"] is None:
        d["warp"] = 1
    return {
        "object": "event",
        "type": job_event_type,
        "data": {
            "object": {
                "id": d["id"],
                "uuid": None, # not for trucky
                "object": "job",
                "driver": {
                    "steam_id": d["driver"]["steam_profile"]["steam_id"],
                    "username": d["driver"]["name"],
                    "profile_photo_url": d["driver"]["avatar_url"]
                },
                "start_time": d["started_at"].split(".")[0]+"Z",
                "stop_time": d["completed_at"].split(".")[0]+"Z" if d["completed_at"] is not None else d["canceled_at"].split(".")[0]+"Z",
                "time_spent": d["real_driving_time_seconds"],
                "planned_distance": d["planned_distance_km"],
                "driven_distance": d["real_driven_distance_km"],
                "adblue_used": None, # not for trucky
                "fuel_used": d["fuel_used_l"],
                "is_special": d["special_job"],
                "is_late": d["late_delivery"],
                "market": d["market"],
                "cargo": {
                    "unique_id": d["cargo_id"],
                    "name": d["cargo_name"],
                    "mass": d["cargo_unit_count"] * d["cargo_unit_mass"],
                    "damage": round(d["cargo_damage"] / 100, 2),
                    "details": cargo_details
                },
                "game": {
                    "short_name": "eut2" if d["game"]["code"] == "ETS2" else "ats",
                    "language": None, # not for trucky
                    "timezone": d["timezone"], # trucky exclusive
                    "max_map_scale": d["max_map_scale"], # trucky exclusive
                    "had_police_enabled": None, # not for trucky
                    "realistic_settings": d["realistic_settings"] # trucky exclusive
                },
                "multiplayer": multiplayer,
                "source_city": {
                    "unique_id": d["source_city_id"],
                    "name": d["source_city_name"]
                },
                "source_company": {
                    "unique_id": d["source_company_id"],
                    "name": d["source_company_name"]
                },
                "destination_city": {
                    "unique_id": d["destination_city_id"],
                    "name": d["destination_city_name"]
                },
                "destination_company": {
                    "unique_id": d["destination_company_id"],
                    "name": d["destination_company_name"]
                },
                "truck": {
                    "unique_id": d["vehicle_in_game_id"],
                    "name": d["vehicle_model_name"],
                    "brand": {
                        "unique_id": d["vehicle_in_game_brand_id"],
                        "name": d["vehicle_brand_name"]
                    },
                    "odometer": d["vehicle_odometer_end_km"],
                    "initial_odometer": d["vehicle_odometer_start_km"],
                    "wheel_count": None, # not for trucky
                    "license_plate": None, # not for trucky
                    "license_plate_country": None, # not for trucky
                    "current_damage": None, # not for trucky
                    "total_damage": {
                        "all": round(d["vehicle_damage"] / 100, 2)
                    },
                    "top_speed": round(d["max_speed_kmh"] / 3.6, 2),
                    "average_speed": round(d["average_speed_kmh"] / 3.6, 2)
                },
                "trailers": [
                    {
                        "name": d["trailer_name"],
                        "body_type": d["trailer_body_type"],
                        "chain_type": d["trailer_chain_type"],
                        "wheel_count": None, # not for trucky
                        "brand": None, # not for trucky
                        "license_plate": None, # not for trucky
                        "license_plate_country": None, # not for trucky
                        "current_damage": None, # not for trucky
                        "total_damage": {
                            "all": round(d["trailers_damage"] / 100, 2)
                        }
                    }
                ],
                "events": events,
                "mods": [],
                "warp": d["warp"] # trucky exclusive
            }
        }
    }

async def handle_new_job(request, response, original_data, data, bypass_tracker_check = False):
    '''Handle new jobs from Trucky.

    NOTE: The data must be processed and converted into TrackSim-like style.'''
    (app, dhrid) = (request.app, request.state.dhrid)
    d = data
    e = d["type"]

    steamid = int(d["data"]["object"]["driver"]["steam_id"])
    await app.db.execute(dhrid, f"SELECT userid, name, uid, discordid, tracker_in_use FROM user WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": "User not found"}
    userid = t[0][0]
    username = t[0][1]
    uid = t[0][2]
    discordid = t[0][3]
    tracker_in_use = t[0][4]
    trackerid = d["data"]["object"]["id"]
    if tracker_in_use != 3 and not bypass_tracker_check:
        response.status_code = 403
        return {"error": "User has chosen to use another tracker."}

    duplicate = False # NOTE only for debugging purpose
    logid = -1
    await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {trackerid} AND tracker_type = 3")
    o = await app.db.fetchall(dhrid)
    if len(o) > 0:
        duplicate = True
        logid = o[0][0]
        response.status_code = 409
        return {"error": "Already logged"}

    driven_distance = float(d["data"]["object"]["driven_distance"])
    fuel_used = d["data"]["object"]["fuel_used"]
    game = d["data"]["object"]["game"]["short_name"]
    munitint = 1 # euro
    if not game.startswith("e"):
        munitint = 2 # dollar
    revenue = 0
    isdelivered = 0
    offence = 0
    if e == "job.delivered":
        revenue = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
        isdelivered = 1
        meta_distance = float(d["data"]["object"]["events"][-1]["meta"]["distance"])
        if driven_distance < 0 or driven_distance > meta_distance * 1.5:
            driven_distance = 0
    else:
        revenue = 0
        if "penalty" in d["data"]["object"]["events"][-1]["meta"].keys():
            revenue = -float(d["data"]["object"]["events"][-1]["meta"]["penalty"])
        driven_distance = 0

    allevents = d["data"]["object"]["events"]
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

    warp = d["data"]["object"]["warp"]

    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"] * 3.6 # m/s => km/h

    delivery_rule_ok = True
    delivery_rule_key = ""
    delivery_rule_value = ""

    mod_revenue = revenue # modified revenue
    if "action" in app.config.__dict__["delivery_rules"].__dict__.keys() \
            and app.config.__dict__["delivery_rules"].__dict__["action"] != "keep_job":
        action = app.config.__dict__["delivery_rules"].__dict__["action"]
        delivery_rules = app.config.__dict__["delivery_rules"].__dict__
        try:
            if "max_speed" in delivery_rules.keys() and top_speed > int(delivery_rules["max_speed"]) and action == "block_job":
                delivery_rule_ok = False
                delivery_rule_key = "max_speed"
                delivery_rule_value = str(top_speed)
        except:
            pass
        try:
            if "max_profit" in delivery_rules.keys() and revenue > int(delivery_rules["max_profit"]):
                if action == "block_job":
                    delivery_rule_ok = False
                    delivery_rule_key = "profit"
                    delivery_rule_value = str(revenue)
                elif action == "drop_data":
                    mod_revenue = 0
        except:
            pass
        try:
            if "max_warp" in delivery_rules.keys() and warp > int(delivery_rules["max_warp"]) and action == "block_job":
                delivery_rule_ok = False
                delivery_rule_key = "warp"
                delivery_rule_value = str(warp)
        except:
            pass
        try:
            if d["data"]["object"]["game"]["realistic_settings"] is not None and "required_realistic_settings" in delivery_rules.keys() and isinstance(delivery_rules["required_realistic_settings"], list) and action == "block_job":
                enabled_realistic_settings = []
                for attr in d["data"]["object"]["game"]["realistic_settings"].keys():
                    if d["data"]["object"]["game"]["realistic_settings"][attr] is True:
                        enabled_realistic_settings.append(attr)
                for attr in delivery_rules["required_realistic_settings"]:
                    if attr not in enabled_realistic_settings:
                        delivery_rule_ok = False
                        delivery_rule_key = "required_realistic_settings"
                        delivery_rule_value = ",".join(delivery_rules["required_realistic_settings"])
                        break
        except:
            pass

    if not delivery_rule_ok:
        await AuditLog(request, uid, ml.ctr(request, "delivery_blocked_due_to_rules", var = {"tracker": TRACKER['trucky'], "trackerid": trackerid, "rule_key": delivery_rule_key, "rule_value": delivery_rule_value}))
        await notification(request, "dlog", uid, ml.tr(request, "delivery_blocked_due_to_rules", var = {"tracker": TRACKER['trucky'], "trackerid": trackerid, "rule_key": delivery_rule_key, "rule_value": delivery_rule_value}, force_lang = await GetUserLanguage(request, uid)))
        response.status_code = 403
        return {"error": "Blocked due to delivery rules"}

    if not duplicate:
        # check once again
        await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {trackerid} AND tracker_type = 3 FOR UPDATE")
        o = await app.db.fetchall(dhrid)
        if len(o) > 0:
            await app.db.commit(dhrid) # unlock table
            response.status_code = 409
            return {"error": "Already logged"}

        await app.db.execute(dhrid, f"INSERT INTO dlog(userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({userid}, '{compress(json.dumps(d,separators=(',', ':')))}', {top_speed}, {int(time.time())}, {isdelivered}, {mod_revenue}, {munitint}, {fuel_used}, {driven_distance}, {trackerid}, 3, 0)")
        await app.db.commit(dhrid)
        await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
        logid = (await app.db.fetchone(dhrid))[0]

        # if "route" in app.config.plugins: # not for trucky
        #     asyncio.create_task(FetchRoute(app, munitint, userid, logid, trackerid, request))

        uid = (await GetUserInfo(request, userid = userid))["uid"]
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
                            await app.db.execute(dhrid, f"INSERT INTO bonus_point VALUES ({userid}, {bonuspoint}, {int(time.time())})")
                            await app.db.commit(dhrid)
                            await notification(request, "bonus", uid, ml.tr(request, "earned_bonus_point", var = {"bonus_points": str(bonuspoint), "logid": logid, "rankname": rankname}, force_lang = await GetUserLanguage(request, uid)))

        except Exception as exc:
            await tracebackHandler(request, exc, traceback.format_exc())

    if (app.config.hook_delivery_log.channel_id != "" or app.config.hook_delivery_log.webhook_url != "") and not duplicate:
        try:
            source_city = d["data"]["object"]["source_city"]
            source_company = d["data"]["object"]["source_company"]
            destination_city = d["data"]["object"]["destination_city"]
            destination_company = d["data"]["object"]["destination_company"]
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
            if d["data"]["object"]["cargo"] is not None and d["data"]["object"]["cargo"]["name"] is not None:
                cargo = d["data"]["object"]["cargo"]["name"]
            if d["data"]["object"]["cargo"] is not None and d["data"]["object"]["cargo"]["mass"] is not None:
                cargo_mass = d["data"]["object"]["cargo"]["mass"]
            omultiplayer = d["data"]["object"]["multiplayer"]
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
            uid = (await GetUserInfo(request, userid = userid))["uid"]
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
            truck = d["data"]["object"]["truck"]
            if truck is not None and truck["brand"]["name"] is not None and truck["name"] is not None:
                truck = truck["brand"]["name"] + " " + truck["name"]
            else:
                truck = "N/A"
            if app.config.discord_bot_token != "":
                headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
                munit = "€"
                if not game.startswith("e"):
                    munit = "$"
                offence = -offence
                if e == "job.delivered":
                    IMGS = app.config.delivery_webhook_image_urls
                    if len(IMGS) == 0:
                        IMGS = [""]
                    k = randint(0, len(IMGS)-1)
                    imgurl = IMGS[k]
                    if not isurl(imgurl):
                        imgurl = ""
                    dhulink = app.config.frontend_urls.member.replace("{userid}", str(userid))
                    dlglink = app.config.frontend_urls.delivery.replace("{logid}", str(logid))
                    data = "{}"
                    if app.config.distance_unit == "imperial":
                        data = {"embeds": [{"title": f"{ml.ctr(request, 'delivery')} #{logid}",
                                "url": dlglink,
                                "fields": [{"name": ml.ctr(request, "driver"), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.ctr(request, "truck"), "value": truck, "inline": True},
                                        {"name": ml.ctr(request, "cargo"), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.ctr(request, "from"), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.ctr(request, "to"), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.ctr(request, "distance"), "value": f"{tseparator(int(driven_distance * 0.621371))}mi", "inline": True},
                                        {"name": ml.ctr(request, "fuel"), "value": f"{tseparator(int(fuel_used * 0.26417205))} gal", "inline": True},
                                        {"name": ml.ctr(request, "net_profit"), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.ctr(request, "time_spent"), "value": original_data["data"]["duration"], "inline": True}],
                                    "footer": {"text": multiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": imgurl}}]}
                    elif app.config.distance_unit == "metric":
                        data = {"embeds": [{"title": f"{ml.ctr(request, 'delivery')} #{logid}",
                                "url": dlglink,
                                "fields": [{"name": ml.ctr(request, "driver"), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.ctr(request, "truck"), "value": truck, "inline": True},
                                        {"name": ml.ctr(request, "cargo"), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.ctr(request, "from"), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.ctr(request, "to"), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.ctr(request, "distance"), "value": f"{tseparator(int(driven_distance))}km", "inline": True},
                                        {"name": ml.ctr(request, "fuel"), "value": f"{tseparator(int(fuel_used))} l", "inline": True},
                                        {"name": ml.ctr(request, "net_profit"), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.ctr(request, "time_spent"), "value": original_data["data"]["duration"], "inline": True}],
                                    "footer": {"text": multiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": imgurl}}]}
                    try:
                        if app.config.hook_delivery_log.channel_id != "":
                            durl = f"https://discord.com/api/v10/channels/{app.config.hook_delivery_log.channel_id}/messages"
                            key = app.config.hook_delivery_log.channel_id
                        elif app.config.hook_delivery_log.webhook_url != "":
                            durl = app.config.hook_delivery_log.webhook_url
                            key = app.config.hook_delivery_log.webhook_url
                        opqueue.queue(app, "post", key, durl, json.dumps(data), headers, "disable")
                    except:
                        pass

                    uid = (await GetUserInfo(request, userid = userid))["uid"]
                    language = await GetUserLanguage(request, uid)
                    data = {}
                    if app.config.distance_unit == "imperial":
                        data = {"embeds": [{"title": f"{ml.tr(request, 'delivery', force_lang = language)} #{logid}",
                                "url": dlglink,
                                "fields": [{"name": ml.tr(request, "driver", force_lang = language), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.tr(request, "truck", force_lang = language), "value": truck, "inline": True},
                                        {"name": ml.tr(request, "cargo", force_lang = language), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.tr(request, "from", force_lang = language), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.tr(request, "to", force_lang = language), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.tr(request, "distance", force_lang = language), "value": f"{tseparator(int(driven_distance * 0.621371))}mi", "inline": True},
                                        {"name": ml.tr(request, "fuel", force_lang = language), "value": f"{tseparator(int(fuel_used * 0.26417205))} gal", "inline": True},
                                        {"name": ml.tr(request, "net_profit", force_lang = language), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.tr(request, "time_spent", force_lang = language), "value": original_data["data"]["duration"], "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": imgurl}}]}
                    elif app.config.distance_unit == "metric":
                        data = {"embeds": [{"title": f"{ml.tr(request, 'delivery', force_lang = language)} #{logid}",
                                "url": dlglink,
                                "fields": [{"name": ml.tr(request, "driver", force_lang = language), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.tr(request, "truck", force_lang = language), "value": truck, "inline": True},
                                        {"name": ml.tr(request, "cargo", force_lang = language), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.tr(request, "from", force_lang = language), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.tr(request, "to", force_lang = language), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.tr(request, "distance", force_lang = language), "value": f"{tseparator(int(driven_distance))}km", "inline": True},
                                        {"name": ml.tr(request, "fuel", force_lang = language), "value": f"{tseparator(int(fuel_used))} l", "inline": True},
                                        {"name": ml.tr(request, "net_profit", force_lang = language), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.tr(request, "time_spent", force_lang = language), "value": original_data["data"]["duration"], "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": imgurl}}]}
                    if await CheckNotificationEnabled(request, "dlog", uid):
                        await SendDiscordNotification(request, uid, data)
                    await UpdateRoleConnection(request, discordid)

        except Exception as exc:
            await tracebackHandler(request, exc, traceback.format_exc())

    try:
        if "challenge" in app.config.plugins and isdelivered and not duplicate:
            await app.db.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
            current_distance = await app.db.fetchone(dhrid)
            current_distance = current_distance[0]
            current_distance = 0 if current_distance is None else int(current_distance)

            userinfo = await GetUserInfo(request, userid = userid)
            roles = userinfo["roles"]

            await app.db.execute(dhrid, f"SELECT challengeid, challenge_type, delivery_count, required_roles, reward_points, job_requirements, title \
                FROM challenge \
                WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())} AND required_distance <= {current_distance}")
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

                    if int(jobreq["minimum_seconds_spent"]) != -1 and d["data"]["object"]["time_spent"] < int(jobreq["minimum_seconds_spent"]):
                        continue
                    if int(jobreq["maximum_seconds_spent"]) != -1 and d["data"]["object"]["time_spent"] > int(jobreq["maximum_seconds_spent"]):
                        continue

                    planned_distance = d["data"]["object"]["planned_distance"]
                    if jobreq["minimum_detour_percentage"] != -1 and (driven_distance / planned_distance) < float(jobreq["minimum_detour_percentage"]):
                        continue
                    if jobreq["maximum_detour_percentage"] != -1 and (driven_distance / planned_distance) > float(jobreq["maximum_detour_percentage"]):
                        continue

                    if jobreq["game"] != "" and d["data"]["object"]["game"]["short_name"] not in jobreq["game"].split(","):
                        continue

                    source_city = d["data"]["object"]["source_city"]
                    source_company = d["data"]["object"]["source_company"]
                    destination_city = d["data"]["object"]["destination_city"]
                    destination_company = d["data"]["object"]["destination_company"]
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
                    if jobreq["market"] != "" and d["data"]["object"]["market"] not in jobreq["market"].split(","):
                        continue

                    cargo = "[unknown]"
                    cargo_mass = 0
                    cargo_damage = 0
                    if d["data"]["object"]["cargo"] is not None and d["data"]["object"]["cargo"]["unique_id"] is not None:
                        cargo = d["data"]["object"]["cargo"]["unique_id"]
                    if d["data"]["object"]["cargo"] is not None and d["data"]["object"]["cargo"]["mass"] is not None:
                        cargo_mass = d["data"]["object"]["cargo"]["mass"]
                    if d["data"]["object"]["cargo"] is not None and d["data"]["object"]["cargo"]["damage"] is not None:
                        cargo_mass = d["data"]["object"]["cargo"]["damage"]

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

                    if d["data"]["object"]["truck"] is not None:
                        truck_id = d["data"]["object"]["truck"]["unique_id"]
                        if jobreq["truck_id"] != "" and truck_id not in jobreq["truck_id"].split(","):
                            continue

                    if jobreq["maximum_speed"] != -1 and top_speed > jobreq["maximum_speed"]:
                        continue
                    if jobreq["minimum_fuel"] != -1 and fuel_used < jobreq["minimum_fuel"]:
                        continue
                    if jobreq["maximum_fuel"] != -1 and fuel_used > jobreq["maximum_fuel"]:
                        continue

                    adblue_used = d["data"]["object"]["adblue_used"]
                    if jobreq["minimum_adblue"] != -1 and adblue_used < jobreq["minimum_adblue"]:
                        continue
                    if jobreq["maximum_adblue"] != -1 and adblue_used > jobreq["maximum_adblue"]:
                        continue

                    profit = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
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

                    auto_park = d["data"]["object"]["events"][-1]["meta"]["autoParked"]
                    auto_load = d["data"]["object"]["events"][0]["meta"]["autoLoaded"]
                    if not jobreq["allow_auto_park"] and auto_park:
                        continue
                    if not jobreq["allow_auto_load"] and auto_load:
                        continue

                    count = {"ferry": 0, "train": 0, "collision": 0, "teleport": 0, "tollgate": 0}
                    toll_paid = 0
                    for i in range(len(d["data"]["object"]["events"])):
                        e = d["data"]["object"]["events"][i]
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

                    is_late = d["data"]["object"]["is_late"]
                    is_special = d["data"]["object"]["is_special"]
                    if jobreq["must_not_be_late"] and is_late:
                        continue
                    if jobreq["must_be_special"] and not is_special:
                        continue

                    average_speed = int(d["data"]["object"]["truck"]["average_speed"])
                    if jobreq["minimum_average_speed"] != -1 and jobreq["minimum_average_speed"] > average_speed:
                        continue
                    if jobreq["maximum_average_speed"] != -1 and jobreq["maximum_average_speed"] < average_speed:
                        continue

                    if d["data"]["object"]["driven_distance"] != 0:
                        average_fuel = d["data"]["object"]["fuel_used"] / d["data"]["object"]["driven_distance"]
                        if int(jobreq["minimum_average_fuel"]) != -1 and jobreq["minimum_average_fuel"] > average_fuel:
                            continue
                        if int(jobreq["maximum_average_fuel"]) != -1 and jobreq["maximum_average_fuel"] < average_fuel:
                            continue

                    if jobreq["minimum_warp"] != -1 and jobreq["minimum_warp"] > warp:
                        continue
                    if jobreq["maximum_warp"] != -1 and jobreq["maximum_warp"] < warp:
                        continue

                    if jobreq["enabled_realistic_settings"] != "":
                        required_realistic_settings = jobreq["enabled_realistic_settings"].split(",")
                        for attr in d["data"]["object"]["game"]["realistic_settings"].keys():
                            if d["data"]["object"]["game"]["realistic_settings"][attr] is True:
                                enabled_realistic_settings.append(attr)
                        for attr in required_realistic_settings:
                            if attr not in enabled_realistic_settings:
                                continue

                    uid = (await GetUserInfo(request, userid = userid))["uid"]
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

                                userinfo = await GetUserInfo(request, userid = userid)
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

                                userinfo = await GetUserInfo(request, userid = userid)
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

                                    userinfo = await GetUserInfo(request, userid = userid)
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

                                    userinfo = await GetUserInfo(request, userid = userid)
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
                    await tracebackHandler(request, exc, traceback.format_exc())

    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())

    try:
        if "economy" in app.config.plugins and isdelivered and not duplicate:
            economy_revenue = round(revenue)
            if economy_revenue > 4294967296:
                economy_revenue = 4294967296
            truckid = convertQuotation(d["data"]["object"]["truck"]["unique_id"])
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

            uid = (await GetUserInfo(request, userid = userid))["uid"]
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
                truck_damage = d["data"]["object"]["truck"]["total_damage"]
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
        await tracebackHandler(request, exc, traceback.format_exc())

    return Response(status_code=204)

async def post_update(response: Response, request: Request):
    app = request.app
    if "trucky" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    webhook_signature = request.headers.get('X-Signature-SHA256')

    ip_ok = False
    needs_validate = False
    for tracker in app.config.trackers:
        if tracker["type"] != "trucky":
            continue
        if type(tracker["ip_whitelist"]) == list and len(tracker["ip_whitelist"]) > 0:
            needs_validate = True
            if request.client.host in tracker["ip_whitelist"]:
                ip_ok = True
    if needs_validate and not ip_ok:
        response.status_code = 403
        await AuditLog(request, -999, ml.ctr(request, "rejected_tracker_webhook_post_ip", var = {"tracker": "Trucky", "ip": request.client.host}))
        return {"error": "Validation failed"}

    raw_body = await request.body()
    raw_body_str = raw_body.decode("utf-8")

    if request.headers.get("Content-Type") == "application/x-www-form-urlencoded":
        d = parse_qs(raw_body_str)
    elif request.headers.get("Content-Type") == "application/json":
        d = json.loads(raw_body_str)
    else:
        response.status_code = 400
        return {"error": "Unsupported content type"}
    sig_ok = False
    needs_validate = False # if at least one tracker has webhook secret, then true (only false when all doesn't have webhook secret)
    for tracker in app.config.trackers:
        if tracker["type"] != "trucky":
            continue
        if tracker["webhook_secret"] is not None and tracker["webhook_secret"] != "":
            needs_validate = True
            sig = hmac.new(tracker["webhook_secret"].encode(), msg=raw_body, digestmod=hashlib.sha256).hexdigest()
            if hmac.compare_digest(sig, webhook_signature):
                sig_ok = True
    if needs_validate and not sig_ok:
        response.status_code = 403
        await AuditLog(request, -999, ml.ctr(request, "rejected_tracker_webhook_post_signature", var = {"tracker": "Trucky", "ip": request.client.host}))
        return {"error": "Validation failed"}

    if d["event"] == "user_joined_company":
        steamid = int(d["data"]["steam_profile"]["steam_id"])
        await app.db.execute(dhrid, f"SELECT uid, userid, roles, discordid FROM user WHERE steamid = {steamid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": "User not found"}
        (uid, userid, roles, discordid) = t[0]
        roles = str2list(roles)
        if userid in [-1, None]:
            await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                response.status_code = 409
                return {"error": ml.tr(request, "banned_user_cannot_be_accepted")}

            await app.db.execute(dhrid, f"SELECT userid, name, discordid, name, steamid, truckersmpid, email, avatar FROM user WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if len(t) == 0:
                response.status_code = 404
                return {"error": ml.tr(request, "user_not_found")}
            if t[0][0] not in [-1, None]:
                response.status_code = 409
                return {"error": ml.tr(request, "user_is_already_member")}
            name = t[0][1]
            discordid = t[0][2]
            username = t[0][3]
            steamid = t[0][4]
            truckersmpid = t[0][5]
            email = t[0][6]
            avatar = t[0][7]
            if (email is None or '@' not in email) and "email" in app.config.required_connections:
                response.status_code = 428
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "Email"})}
            if discordid is None and "discord" in app.config.required_connections:
                response.status_code = 428
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "Discord"})}
            if steamid is None and "steam" in app.config.required_connections:
                response.status_code = 428
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"})}
            if truckersmpid is None and "truckersmp" in app.config.required_connections:
                response.status_code = 428
                return {"error": ml.tr(request, "connection_invalid", var = {"app": "TruckersMP"})}

            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
            t = await app.db.fetchall(dhrid)
            userid = int(t[0][0])

            await app.db.execute(dhrid, f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE uid = {uid}")
            await app.db.execute(dhrid, f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
            await AuditLog(request, -997, ml.ctr(request, "accepted_user_as_member", var = {"username": name, "userid": userid, "uid": uid}))
            await app.db.commit(dhrid)

            app.redis.set(f"umap:userid={userid}", uid)
            app.redis.expire(f"umap:userid={userid}", 60)

            await notification(request, "member", uid, ml.tr(request, "member_accepted", var = {"userid": userid}, force_lang = await GetUserLanguage(request, uid)))

            def setvar(msg):
                return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar)).replace("{staff_mention}", "").replace("{staff_name}", "Trucky").replace("{staff_userid}", "-997").replace("{staff_uid}", "-997").replace("{staff_avatar}", validateUrl(app.config.logo_url))

            for meta in app.config.member_accept:
                meta = Dict2Obj(meta)
                if meta.webhook_url != "" or meta.channel_id != "":
                    await AutoMessage(app, meta, setvar)

                if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
                    for role in meta.role_change:
                        try:
                            if int(role) < 0:
                                opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"remove_role,{-int(role)},{discordid}")
                            elif int(role) > 0:
                                opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"add_role,{int(role)},{discordid}")
                        except:
                            pass

        if not checkPerm(app, roles, "driver"):
            roles.append(app.config.perms.driver[0])
            await app.db.execute(dhrid, f"UPDATE user SET roles = '{list2str(roles)}' WHERE uid = {uid}")
            await app.db.commit(dhrid)

            await UpdateRoleConnection(request, discordid)

            def setvar(msg):
                return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar)).replace("{staff_mention}", "").replace("{staff_name}", "Trucky").replace("{staff_userid}", "-997").replace("{staff_uid}", "-997").replace("{staff_avatar}", validateUrl(app.config.logo_url))

            for meta in app.config.driver_role_add:
                meta = Dict2Obj(meta)
                if meta.webhook_url != "" or meta.channel_id != "":
                    await AutoMessage(app, meta, setvar)

                if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
                    for role in meta.role_change:
                        try:
                            if int(role) < 0:
                                opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"remove_role,{-int(role)},{discordid}")
                            elif int(role) > 0:
                                opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"add_role,{int(role)},{discordid}")
                        except:
                            pass

    original_data = copy.deepcopy(d)
    d = convert_format(d)
    if d is None:
        response.status_code = 400
        return {"error": "Only job_completed, job_canceled and user_joined_company events are accepted"}

    return await handle_new_job(request, response, original_data, d)

async def post_import(response: Response, request: Request, jobid: int, authorization: str = Header(None), bypass_tracker_check: Optional[bool] = False):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /trucky/import', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "import_dlogs"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    try:
        r = await arequests.get(app, f"https://e.truckyapp.com/api/v1/job/{jobid}", headers = {"User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
        if r.status_code != 200:
            d = json.loads(r.text)
            response.status_code = r.status_code
            if "message" in d.keys():
                return {"error": d["message"]}
            else:
                return {"error": ml.tr(request, "unknown_error")}
        job_data = json.loads(r.text)
    except:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': 'Trucky'})}

    try:
        r = await arequests.get(app, f"https://e.truckyapp.com/api/v1/job/{jobid}/events", headers = {"User-Agent": f"CHub Drivers Hub Backend {app.version}"}, dhrid = dhrid)
        if r.status_code != 200:
            d = json.loads(r.text)
            response.status_code = r.status_code
            if "message" in d.keys():
                return {"error": d["message"]}
            else:
                return {"error": ml.tr(request, "unknown_error")}
        events_data = json.loads(r.text)
        job_data["events"] = events_data
    except:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': 'Trucky'})}

    d = {"event": f"job_{job_data['status']}", "data": job_data}
    original_data = copy.deepcopy(d)
    d = convert_format(d)
    if d is None:
        response.status_code = 400
        return {"error": "Only job_completed and job_canceled events are accepted"}

    return await handle_new_job(request, response, original_data, d, bypass_tracker_check = bypass_tracker_check)

async def put_driver(response: Response, request: Request, userid: int, authorization: str = Header(None)):
    app = request.app
    if "trucky" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /trucky/driver', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    userinfo = await GetUserInfo(request, userid = userid)
    if userinfo["uid"] is None:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    tracker_app_error = await add_driver(request, userinfo["steamid"], au["uid"], userid, userinfo["name"], trackers = ["trucky"])

    if tracker_app_error == "":
        return Response(status_code=204)
    else:
        response.status_code = 503
        return {"error": tracker_app_error}

async def delete_driver(response: Response, request: Request, userid: int, authorization: str = Header(None)):
    app = request.app
    if "trucky" not in configured_trackers(app):
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /trucky/driver', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    userinfo = await GetUserInfo(request, userid = userid)
    if userinfo["uid"] is None:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    tracker_app_error = await remove_driver(request, userinfo["steamid"], au["uid"], userid, userinfo["name"], trackers = ["trucky"])

    if tracker_app_error == "":
        return Response(status_code=204)
    else:
        response.status_code = 503
        return {"error": tracker_app_error}
