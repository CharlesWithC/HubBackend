# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC
# NOTE LEGACY CODE

import asyncio
import json
import time
import traceback
from datetime import datetime
from random import randint

from dateutil import parser
from fastapi import Header, Request, Response

import multilang as ml
from apis.member import RANKROLE
from app import app, config, tconfig
from db import aiosql
from functions import *

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special", "minimum_average_speed", "maximum_average_speed", "minimum_average_fuel", "maximum_average_fuel"]
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0, "minimum_average_speed": -1, "maximum_average_speed": -1, "minimum_average_fuel": -1, "maximum_average_fuel": -1}

GIFS = config.delivery_post_gifs
if len(GIFS) == 0:
    GIFS = [""]

async def UpdateTelemetry(steamid, userid, logid, start_time, end_time):
    dhrid = genrid()
    await aiosql.new_conn(dhrid, extra_time = 5)
    
    await aiosql.execute(dhrid, f"SELECT uuid FROM temptelemetry WHERE steamid = {steamid} AND timestamp > {int(start_time)} AND timestamp < {int(end_time)} LIMIT 1")
    p = await aiosql.fetchall(dhrid)
    if len(p) > 0:
        jobuuid = p[0][0]
        await aiosql.execute(dhrid, f"SELECT x, y, z, game, mods, timestamp FROM temptelemetry WHERE uuid = '{jobuuid}'")
        t = await aiosql.fetchall(dhrid)
        data = f"{t[0][3]},{t[0][4]},v5;"
        lastx = 0
        lastz = 0
        idle = 0
        for tt in t:
            if round(tt[0]) - lastx == 0 and round(tt[2]) - lastz == 0:
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
        await aiosql.close_conn(dhrid)

        for _ in range(3):
            try:
                dhrid = genrid()
                await aiosql.new_conn(dhrid, extra_time = 5)
    
                await aiosql.execute(dhrid, f"SELECT logid FROM telemetry WHERE logid = {logid}")
                p = await aiosql.fetchall(dhrid)
                if len(p) > 0:
                    break
                    
                await aiosql.execute(dhrid, f"INSERT INTO telemetry VALUES ({logid}, '{jobuuid}', {userid}, '{compress(data)}')")
                await aiosql.commit(dhrid)
                await aiosql.close_conn(dhrid)
                break
            except:
                continue

        for _ in range(5):
            try:
                dhrid = genrid()
                await aiosql.new_conn(dhrid, extra_time = 5)
                await aiosql.execute(dhrid, f"DELETE FROM temptelemetry WHERE uuid = '{jobuuid}'")
                await aiosql.commit(dhrid)
                await aiosql.close_conn(dhrid)
                break
            except:
                continue
    else:
        await aiosql.close_conn(dhrid)

@app.post(f"/{config.abbr}/navio")
async def postNavio(response: Response, request: Request):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    if request.client.host not in config.allowed_tracker_ips:
        response.status_code = 403
        await AuditLog(dhrid, -999, f"Rejected Navio webhook update from {request.client.host}")
        return {"error": "Validation failed"}
    
    if request.headers["Content-Type"] == "application/x-www-form-urlencoded":
        d = await request.form()
    elif request.headers["Content-Type"] == "application/json":
        d = await request.json()
    else:
        response.status_code = 400
        return {"error": "Unsupported content type"}
    if d["object"] != "event":
        return {"error": "Only events are accepted."}
    e = d["type"]
    if e == "company_driver.detached":
        steamid = int(d["data"]["object"]["steam_id"])
        await aiosql.execute(dhrid, f"SELECT uid, userid, name, discordid FROM user WHERE steamid = '{steamid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": "User not found."}
        uid = t[0][0]
        userid = t[0][1]
        name = t[0][2]
        discordid = t[0][3]
        await AuditLog(dhrid, -999, f"Member resigned: `{name}` (UID: `{uid}`)")
        
        await aiosql.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
        await aiosql.commit(dhrid)

        def setvar(msg):
            return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace(f"{uid}", str(uid))

        if config.member_leave.webhook_url != "" or config.member_leave.channel_id != "":
            meta = config.member_leave
            await AutoMessage(meta, setvar)
        
        if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
            for role in config.member_leave.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()
        
        if discordid is not None:
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}
            try:
                r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
                d = json.loads(r.text)
                if "roles" in d:
                    roles = d["roles"]
                    curroles = []
                    for role in roles:
                        if int(role) in list(RANKROLE.values()):
                            curroles.append(int(role))
                    for role in curroles:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
            except:
                pass
        
        return {"message": "User resigned."}

    steamid = int(d["data"]["object"]["driver"]["steam_id"])
    await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE steamid = '{steamid}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return {"error": "User not found."}
    userid = t[0][0]
    username = t[0][1]
    trackerid = d["data"]["object"]["id"]

    duplicate = False # NOTE only for debugging purpose
    logid = -1
    await aiosql.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {trackerid} AND tracker_type = 1")
    o = await aiosql.fetchall(dhrid)
    if len(o) > 0:
        duplicate = True
        logid = o[0][0]
        return {"error": "Already logged"}

    driven_distance = float(d["data"]["object"]["driven_distance"])
    fuel_used = d["data"]["object"]["fuel_used"]
    game = d["data"]["object"]["game"]["short_name"]
    munitint = 1 # euro
    if not game.startswith("e"):
        munitint = 2 # dollar
    revenue = 0
    xp = 0
    isdelivered = 0
    offence = 0
    if e == "job.delivered":
        revenue = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
        isdelivered = 1
        xp = d["data"]["object"]["events"][-1]["meta"]["earned_xp"]
        meta_distance = float(d["data"]["object"]["events"][-1]["meta"]["distance"])
        if driven_distance < 0 or driven_distance > meta_distance * 1.5:
            driven_distance = 0
    else:
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
    
    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"] * 3.6 # m/s => km/h
    start_time = parser.parse(d["data"]["object"]["start_time"]).timestamp()
    end_time = parser.parse(d["data"]["object"]["stop_time"]).timestamp()

    delivery_rule_ok = True
    
    mod_revenue = revenue
    if "delivery_rules" in tconfig.keys() and "action" in tconfig["delivery_rules"].keys() \
            and tconfig["delivery_rules"]["action"] != "bypass":
        action = tconfig["delivery_rules"]["action"]
        delivery_rules = tconfig["delivery_rules"]
        try:
            if top_speed > int(delivery_rules["max_speed"]) and action == "block":
                delivery_rule_ok = False
        except:
            pass
        try:
            if revenue > int(delivery_rules["max_profit"]):
                if action == "block":
                    delivery_rule_ok = False
                elif action == "drop":
                    mod_revenue = 0
        except:
            pass
    
    if not delivery_rule_ok:        
        return {"message": "Blocked due to delivery rules."}

    if not duplicate:
        await aiosql.execute(dhrid, f"INSERT INTO dlog(userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({userid}, '{compress(json.dumps(d,separators=(',', ':')))}', {top_speed}, \
            {int(time.time())}, {isdelivered}, {mod_revenue}, {munitint}, {fuel_used}, {driven_distance}, {trackerid}, 1, 0)")
        await aiosql.commit(dhrid)
        await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
        logid = (await aiosql.fetchone(dhrid))[0]

        if "tracker" in config.enabled_plugins:
            asyncio.create_task(UpdateTelemetry(steamid, userid, logid, start_time, end_time))

        uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
        await notification(dhrid, "dlog", uid, ml.tr(None, "job_submitted", var = {"logid": logid}, force_lang = await GetUserLanguage(dhrid, uid, "en")), no_discord_notification = True)

    if config.delivery_log_channel_id != "" and not duplicate:
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
                multiplayer = ml.ctr("single_player")
            else:
                if omultiplayer["type"] == "truckersmp":
                    if omultiplayer["server"] is not None:
                        multiplayer = "TruckersMP (" + omultiplayer["server"] +")"
                    else:
                        multiplayer = "TruckersMP"
                elif omultiplayer["type"] == "scs_convoy":
                    multiplayer = ml.ctr("scs_convoy")
            uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
            language = await GetUserLanguage(dhrid, uid, "en")
            if omultiplayer is None:
                umultiplayer = ml.tr(None, "single_player", force_lang = language)
            else:
                if omultiplayer["type"] == "truckersmp":
                    if omultiplayer["server"] is not None:
                        umultiplayer = "TruckersMP (" + omultiplayer["server"] +")"
                    else:
                        umultiplayer = "TruckersMP"
                elif omultiplayer["type"] == "scs_convoy":
                    umultiplayer = ml.tr(None, "scs_convoy", force_lang = language)
            truck = d["data"]["object"]["truck"]
            if truck is not None and truck["brand"]["name"] is not None and truck["name"] is not None:
                truck = truck["brand"]["name"] + " " + truck["name"]
            else:
                truck = "N/A"
            if config.discord_bot_token != "":
                headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
                munit = "€"
                if not game.startswith("e"):
                    munit = "$"
                offence = -offence
                if e == "job.delivered":
                    k = randint(0, len(GIFS)-1)
                    gifurl = GIFS[k]
                    if not isurl(gifurl):
                        gifurl = ""
                    dhulink = config.frontend_urls.member.replace("{userid}", str(userid))
                    dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
                    data = "{}"
                    if config.distance_unit == "imperial":
                        data = {"embeds": [{"title": f"{ml.ctr('delivery')} #{logid}", 
                                "url": dlglink,
                                "fields": [{"name": ml.ctr("driver"), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.ctr("truck"), "value": truck, "inline": True},
                                        {"name": ml.ctr("cargo"), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.ctr("from"), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.ctr("to"), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.ctr("distance"), "value": f"{tseparator(int(driven_distance * 0.621371))}mi", "inline": True},
                                        {"name": ml.ctr("fuel"), "value": f"{tseparator(int(fuel_used * 0.26417205))} gal", "inline": True},
                                        {"name": ml.ctr("net_profit"), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.ctr("xp_earned"), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": multiplayer}, "color": config.intcolor,\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}, "color": config.intcolor}]}
                    elif config.distance_unit == "metric":
                        data = {"embeds": [{"title": f"{ml.ctr('delivery')} #{logid}", 
                                "url": dlglink,
                                "fields": [{"name": ml.ctr("driver"), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.ctr("truck"), "value": truck, "inline": True},
                                        {"name": ml.ctr("cargo"), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.ctr("from"), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.ctr("to"), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.ctr("distance"), "value": f"{tseparator(int(driven_distance))}km", "inline": True},
                                        {"name": ml.ctr("fuel"), "value": f"{tseparator(int(fuel_used))} l", "inline": True},
                                        {"name": ml.ctr("net_profit"), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.ctr("xp_earned"), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": multiplayer}, "color": config.intcolor,\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}, "color": config.intcolor}]}
                    try:
                        r = await arequests.post(f"https://discord.com/api/v10/channels/{config.delivery_log_channel_id}/messages", headers=headers, data=json.dumps(data), timeout=3, dhrid = dhrid)
                        if r.status_code == 401:
                            DisableDiscordIntegration()
                    except:
                        traceback.print_exc()
                    
                    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
                    language = await GetUserLanguage(dhrid, uid, "en")
                    data = {}
                    if config.distance_unit == "imperial":
                        data = {"embeds": [{"title": f"{ml.tr(None, 'delivery', force_lang = language)} #{logid}", 
                                "url": dlglink,
                                "fields": [{"name": ml.tr(None, "driver", force_lang = language), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.tr(None, "truck", force_lang = language), "value": truck, "inline": True},
                                        {"name": ml.tr(None, "cargo", force_lang = language), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.tr(None, "from", force_lang = language), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.tr(None, "to", force_lang = language), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.tr(None, "distance", force_lang = language), "value": f"{tseparator(int(driven_distance * 0.621371))}mi", "inline": True},
                                        {"name": ml.tr(None, "fuel", force_lang = language), "value": f"{tseparator(int(fuel_used * 0.26417205))} gal", "inline": True},
                                        {"name": ml.tr(None, "net_profit", force_lang = language), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.tr(None, "xp_earned", force_lang = language), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": config.intcolor,\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}, "color": config.intcolor}]}
                    elif config.distance_unit == "metric":
                        data = {"embeds": [{"title": f"{ml.tr(None, 'delivery', force_lang = language)} #{logid}", 
                                "url": dlglink,
                                "fields": [{"name": ml.tr(None, "driver", force_lang = language), "value": f"[{username}]({dhulink})", "inline": True},
                                        {"name": ml.tr(None, "truck", force_lang = language), "value": truck, "inline": True},
                                        {"name": ml.tr(None, "cargo", force_lang = language), "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                        {"name": ml.tr(None, "from", force_lang = language), "value": source_company + ", " + source_city, "inline": True},
                                        {"name": ml.tr(None, "to", force_lang = language), "value": destination_company + ", " + destination_city, "inline": True},
                                        {"name": ml.tr(None, "distance", force_lang = language), "value": f"{tseparator(int(driven_distance))}km", "inline": True},
                                        {"name": ml.tr(None, "fuel", force_lang = language), "value": f"{tseparator(int(fuel_used))} l", "inline": True},
                                        {"name": ml.tr(None, "net_profit", force_lang = language), "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                        {"name": ml.tr(None, "xp_earned", force_lang = language), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": config.intcolor,\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}, "color": config.intcolor}]}
                    if await CheckNotificationEnabled(dhrid, "dlog", uid):
                        await SendDiscordNotification(dhrid, uid, data)
                        
        except:
            traceback.print_exc()

    try:
        if "challenge" in config.enabled_plugins and isdelivered and not duplicate:
            await aiosql.execute(dhrid, f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
            current_distance = await aiosql.fetchone(dhrid)
            current_distance = current_distance[0]
            current_distance = 0 if current_distance is None else int(current_distance)

            userinfo = await GetUserInfo(dhrid, request, userid = userid)
            roles = userinfo["roles"]

            await aiosql.execute(dhrid, f"SELECT challengeid, challenge_type, delivery_count, required_roles, reward_points, job_requirements, title \
                FROM challenge \
                WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())} AND required_distance <= {current_distance}")
            t = await aiosql.fetchall(dhrid)
            for tt in t:
                try:
                    challengeid = tt[0]
                    challenge_type = tt[1]
                    delivery_count = tt[2]
                    required_roles = tt[3].split(",")[:20]
                    reward_points = tt[4]
                    job_requirements = tt[5]
                    title = tt[6]

                    rolesok = False
                    if len(required_roles) == 0:
                        roleok = True
                    for r in required_roles:
                        if r == "":
                            continue
                        if r in roles:
                            rolesok = True
                    if not rolesok:
                        continue

                    p = json.loads(decompress(job_requirements))
                    jobreq = JOB_REQUIREMENT_DEFAULT
                    for i in range(0,len(p)):
                        jobreq[JOB_REQUIREMENTS[i]] = p[i]
                    
                    if jobreq["minimum_distance"] != -1 and driven_distance < jobreq["minimum_distance"]:
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
                    if jobreq["source_city_id"] != "" and not source_city in jobreq["source_city_id"].split(","):
                        continue
                    if jobreq["source_company_id"] != "" and not source_company in jobreq["source_company_id"].split(","):
                        continue
                    if jobreq["destination_city_id"] != "" and not destination_city in jobreq["destination_city_id"].split(","):
                        continue
                    if jobreq["destination_company_id"] != "" and not destination_company in jobreq["destination_company_id"].split(","):
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
                    
                    if jobreq["cargo_id"] != "" and not cargo in jobreq["cargo_id"].split(","):
                        continue
                    if jobreq["minimum_cargo_mass"] != -1 and cargo_mass < jobreq["minimum_cargo_mass"]:
                        continue
                    if jobreq["maximum_cargo_damage"] != -1 and cargo_damage > jobreq["maximum_cargo_damage"]:
                        continue
                    
                    if jobreq["maximum_speed"] != -1 and top_speed > jobreq["maximum_speed"]:
                        continue
                    if jobreq["maximum_fuel"] != -1 and fuel_used > jobreq["maximum_fuel"]:
                        continue
                    
                    profit = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
                    if jobreq["minimum_profit"] != -1 and profit < jobreq["minimum_profit"]:
                        continue
                    if jobreq["maximum_profit"] != -1 and profit > jobreq["maximum_profit"]:
                        continue
                    if jobreq["maximum_offence"] != -1 and abs(offence) > jobreq["maximum_offence"]:
                        continue
                    
                    if not jobreq["allow_overspeed"] and has_overspeed:
                        continue

                    auto_park = d["data"]["object"]["events"][-1]["meta"]["auto_park"]
                    auto_load = d["data"]["object"]["events"][-1]["meta"]["auto_load"]
                    if not jobreq["allow_auto_park"] and auto_park:
                        continue
                    if not jobreq["allow_auto_load"] and auto_load:
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
                    
                    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
                    await notification(dhrid, "challenge", uid, ml.tr(None, "delivery_accepted_by_challenge", var = {"logid": logid, "title": title, "challengeid": challengeid}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
                    await aiosql.execute(dhrid, f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {int(time.time())})")    
                    await aiosql.commit(dhrid)

                    current_delivery_count = 0
                    if challenge_type in [1,3]:
                        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                    elif challenge_type == 2:
                        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
                    elif challenge_type == 4:
                        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                            WHERE challenge_record.challengeid = {challengeid} AND challenge_record.userid = {userid}")
                    elif challenge_type == 5:
                        await aiosql.execute(dhrid, f"SELECT SUM(dlog.distance) FROM challenge_record \
                            INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                            WHERE challenge_record.challengeid = {challengeid}")
                    current_delivery_count = await aiosql.fetchone(dhrid)
                    current_delivery_count = 0 if current_delivery_count is None or current_delivery_count[0] is None else int(current_delivery_count[0])

                    if current_delivery_count >= delivery_count:
                        if challenge_type in [1,4]:
                            await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                            t = await aiosql.fetchall(dhrid)
                            if len(t) == 0:
                                await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                                await aiosql.commit(dhrid)
                                uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
                                await notification(dhrid, "challenge", uid, ml.tr(None, "one_time_personal_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
                        elif challenge_type == 3:
                            await aiosql.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                            t = await aiosql.fetchall(dhrid)
                            if current_delivery_count >= (len(t) + 1) * delivery_count:
                                await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                                await aiosql.commit(dhrid)
                                uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
                                await notification(dhrid, "challenge", uid, ml.tr(None, "recurring_challenge_completed_status_added", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator((len(t)+1) * reward_points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
                        elif challenge_type == 2:
                            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
                            t = await aiosql.fetchall(dhrid)
                            if len(t) == 0:
                                curtime = int(time.time())
                                await aiosql.execute(dhrid, f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                                t = await aiosql.fetchall(dhrid)
                                usercnt = {}
                                for tt in t:
                                    uid = tt[0]
                                    if not uid in usercnt.keys():
                                        usercnt[uid] = 1
                                    else:
                                        usercnt[uid] += 1
                                for uid in usercnt.keys():
                                    s = usercnt[uid]
                                    reward = round(reward_points * s / delivery_count)
                                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                                    uid = (await GetUserInfo(dhrid, request, userid = uid))["uid"]
                                    await notification(dhrid, "challenge", uid, ml.tr(None, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
                                await aiosql.commit(dhrid)
                        elif challenge_type == 5:
                            await aiosql.execute(dhrid, f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
                            t = await aiosql.fetchall(dhrid)
                            if len(t) == 0:
                                curtime = int(time.time())
                                await aiosql.execute(dhrid, f"SELECT challenge_record.userid, SUM(dlog.distance) FROM challenge_record \
                                    INNER JOIN dlog ON dlog.logid = challenge_record.logid \
                                    WHERE challenge_record.challengeid = {challengeid} \
                                    GROUP BY dlog.userid, challenge_record.userid")
                                t = await aiosql.fetchall(dhrid)
                                usercnt = {}
                                totalcnt = 0
                                for tt in t:
                                    totalcnt += tt[1]
                                    uid = tt[0]
                                    if not uid in usercnt.keys():
                                        usercnt[uid] = tt[1] - max(totalcnt - delivery_count, 0)
                                    else:
                                        usercnt[uid] += tt[1] - max(totalcnt - delivery_count, 0)
                                    if totalcnt >= delivery_count:
                                        break
                                for uid in usercnt.keys():
                                    s = usercnt[uid]
                                    reward = round(reward_points * s / delivery_count)
                                    await aiosql.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                                    uid = (await GetUserInfo(dhrid, request, userid = uid))["uid"]
                                    await notification(dhrid, "challenge", uid, ml.tr(None, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
                                await aiosql.commit(dhrid)
                except:
                    traceback.print_exc()
                
    except:
        traceback.print_exc()

    return {"message": "Logged"}