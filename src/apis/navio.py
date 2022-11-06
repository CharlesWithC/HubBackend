# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from datetime import datetime
from random import randint
from dateutil import parser
import json, time, requests
import threading

from app import app, config, tconfig
from db import newconn
from functions import *
import multilang as ml

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special"]
JOB_REQUIREMENT_TYPE = {"source_city_id": convert_quotation, "source_company_id": convert_quotation, "destination_city_id": convert_quotation, "destination_company_id": convert_quotation, "minimum_distance": int, "cargo_id": convert_quotation, "minimum_cargo_mass": int, "maximum_cargo_damage": float, "maximum_speed": int, "maximum_fuel": int, "minimum_profit": int, "maximum_profit": int, "maximum_offence": int, "allow_overspeed": int, "allow_auto_park": int, "allow_auto_load": int, "must_not_be_late": int, "must_be_special": int}
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0}

GIFS = config.delivery_post_gifs
if len(GIFS) == 0:
    GIFS = [""]

def UpdateTelemetry(steamid, userid, logid, start_time, end_time):
    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT uuid FROM temptelemetry WHERE steamid = {steamid} AND timestamp > {int(start_time)} AND timestamp < {int(end_time)} LIMIT 1")
    p = cur.fetchall()
    if len(p) > 0:
        jobuuid = p[0][0]
        cur.execute(f"SELECT x, y, z, game, mods, timestamp FROM temptelemetry WHERE uuid = '{jobuuid}'")
        t = cur.fetchall()
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
        for _ in range(3):
            try:
                conn = newconn()
                cur = conn.cursor()
                cur.execute(f"SELECT logid FROM telemetry WHERE logid = {logid}")
                p = cur.fetchall()
                if len(p) > 0:
                    break
                    
                cur.execute(f"INSERT INTO telemetry VALUES ({logid}, '{jobuuid}', {userid}, '{compress(data)}')")
                conn.commit()
                break
            except:
                continue
        for _ in range(5):
            try:
                conn = newconn()
                cur = conn.cursor()
                cur.execute(f"DELETE FROM temptelemetry WHERE uuid = '{jobuuid}'")
                conn.commit()
            except:
                continue

@app.post(f"/{config.abbr}/navio")
async def navio(request: Request, Navio_Signature: str = Header(None)):
    conn = newconn()
    cur = conn.cursor()

    if request.client.host != "185.233.107.244":
        response.status_code = 403
        await AuditLog(-999, f"Rejected suspicious Navio webhook post from {request.client.host}")
        return {"error": True, "descriptor": "Validation failed"}
    
    d = await request.json()
    if d["object"] != "event":
        return {"error": True, "descriptor": "Only events are accepted."}
    e = d["type"]
    if e == "company_driver.detached":
        steamid = int(d["data"]["object"]["steam_id"])
        cur.execute(f"SELECT userid, name, discordid FROM user WHERE steamid = '{steamid}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "User not found."}
        userid = t[0][0]
        name = convert_quotation(t[0][1])
        discordid = t[0][2]
        await AuditLog(-999, f"Member resigned: `{name}` (Discord ID: `{discordid}`)")
        cur.execute(f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
        conn.commit()
        
        return {"error": False, "response": "User resigned."}

    steamid = int(d["data"]["object"]["driver"]["steam_id"])
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT userid, name FROM user WHERE steamid = '{steamid}'")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "User not found."}
    userid = t[0][0]
    username = t[0][1]
    navioid = d["data"]["object"]["id"]

    duplicate = False
    logid = -1
    cur.execute(f"SELECT logid FROM dlog WHERE navioid = {navioid}")
    o = cur.fetchall()
    if len(o) > 0:
        duplicate = True # only for debugging purpose
        logid = o[0][0]
        return {"error": True, "descriptor": "Already logged"}

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
    if not duplicate:
        cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtlogid'")
        t = cur.fetchall()
        logid = int(t[0][0])

    delivery_rule_ok = True
    try:
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
        if delivery_rule_ok and not duplicate:
            if "tracker" in config.enabled_plugins:
                threading.Thread(target=UpdateTelemetry,args=(steamid, userid, logid, start_time, end_time, )).start()
            
            cur.execute(f"UPDATE settings SET sval = {logid+1} WHERE skey = 'nxtlogid'")
            cur.execute(f"INSERT INTO dlog VALUES ({logid}, {userid}, '{compress(json.dumps(d,separators=(',', ':')))}', {top_speed}, \
                {int(time.time())}, {isdelivered}, {mod_revenue}, {munitint}, {fuel_used}, {driven_distance}, {navioid})")
            conn.commit()

            discordid = getUserInfo(userid = userid)["discordid"]
            notification(discordid, f"New Delivery `#{logid}`")
    except:
        pass

    if config.delivery_log_channel_id != "" and not duplicate:
        try:
            source_city = d["data"]["object"]["source_city"]
            source_company = d["data"]["object"]["source_company"]
            destination_city = d["data"]["object"]["destination_city"]
            destination_company = d["data"]["object"]["destination_company"]
            if source_city is None or source_city["name"] is None:
                source_city = "Unknown City"
            else:
                source_city = source_city["name"]
            if source_company is None or source_company["name"] is None:
                source_company = "Unknown Company"
            else:
                source_company = source_company["name"]
            if destination_city is None or destination_city["name"] is None:
                destination_city = "Unknown City"
            else:
                destination_city = destination_city["name"]
            if destination_company is None or destination_company["name"] is None:
                destination_company = "Unknown Company"
            else:
                destination_company = destination_company["name"]
            cargo = "Unknown Cargo"
            cargo_mass = 0
            if not d["data"]["object"]["cargo"] is None and not d["data"]["object"]["cargo"]["name"] is None:
                cargo = d["data"]["object"]["cargo"]["name"]
            if not d["data"]["object"]["cargo"] is None and not d["data"]["object"]["cargo"]["mass"] is None:
                cargo_mass = d["data"]["object"]["cargo"]["mass"]
            multiplayer = d["data"]["object"]["multiplayer"]
            if multiplayer is None:
                multiplayer = "Single Player"
            else:
                if multiplayer["type"] == "truckersmp":
                    multiplayer = "TruckersMP (" + multiplayer["server"] +")"
                elif multiplayer["type"] == "scs_convoy":
                    multiplayer = "SCS Convoy"
                else:
                    multiplayer = "Unknown Multiplayer Mode"
            truck = d["data"]["object"]["truck"]
            if not truck is None and not truck["brand"]["name"] is None and not truck["name"] is None:
                truck = truck["brand"]["name"] + " " + truck["name"]
            else:
                truck = "Unknown Truck"
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{config.delivery_log_channel_id}/messages"
            munit = "€"
            if not game.startswith("e"):
                munit = "$"
            offence = -offence
            if e == "job.delivered":
                k = randint(0, len(GIFS)-1)
                dhulink = config.frontend_urls.member.replace("{userid}", str(userid))
                dlglink = config.frontend_urls.delivery.replace("{logid}", str(logid))
                if config.distance_unit == "imperial":
                    requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Delivery #{logid}", 
                            "url": dlglink,
                            "fields": [{"name": "Driver", "value": f"[{username}]({dhulink})", "inline": True},
                                    {"name": "Truck", "value": truck, "inline": True},
                                    {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                    {"name": "From", "value": source_company + ", " + source_city, "inline": True},
                                    {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                                    {"name": "Distance", "value": f"{tseparator(int(driven_distance * 0.621371))}mi", "inline": True},
                                    {"name": "Fuel", "value": f"{tseparator(int(fuel_used * 0.26417205))} gal", "inline": True},
                                    {"name": "Net Profit", "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                    {"name": "XP Earned", "value": f"{tseparator(xp)}", "inline": True}],
                                "footer": {"text": multiplayer}, "color": config.intcolor,\
                                "timestamp": str(datetime.now()), "image": {"url": GIFS[k]}, "color": config.intcolor}}), timeout=3)
                elif config.distance_unit == "metric":
                    requests.post(ddurl, headers=headers, data=json.dumps({"embed": {"title": f"Delivery #{logid}", 
                            "url": dlglink,
                            "fields": [{"name": "Driver", "value": f"[{username}]({dhulink})", "inline": True},
                                    {"name": "Truck", "value": truck, "inline": True},
                                    {"name": "Cargo", "value": cargo + f" ({int(cargo_mass/1000)}t)", "inline": True},
                                    {"name": "From", "value": source_company + ", " + source_city, "inline": True},
                                    {"name": "To", "value": destination_company + ", " + destination_city, "inline": True},
                                    {"name": "Distance", "value": f"{tseparator(int(driven_distance))}km", "inline": True},
                                    {"name": "Fuel", "value": f"{tseparator(int(fuel_used))} l", "inline": True},
                                    {"name": "Net Profit", "value": f"{munit}{tseparator(int(revenue))}", "inline": True},
                                    {"name": "XP Earned", "value": f"{tseparator(xp)}", "inline": True}],
                                "footer": {"text": multiplayer}, "color": config.intcolor,\
                                "timestamp": str(datetime.now()), "image": {"url": GIFS[k]}, "color": config.intcolor}}), timeout=3)
                cur.execute(f"SELECT discordid FROM user WHERE userid = {userid}")
                p = cur.fetchall()
                udiscordid = p[0][0]

        except:
            import traceback
            traceback.print_exc()

    try:
        if "challenge" in config.enabled_plugins and delivery_rule_ok and isdelivered and not duplicate:
            cur.execute(f"SELECT SUM(distance) FROM dlog WHERE userid = {userid}")
            current_distance = cur.fetchone()[0]
            current_distance = 0 if current_distance is None else int(current_distance)

            userinfo = getUserInfo(userid = userid)
            roles = userinfo["roles"]

            cur.execute(f"SELECT challengeid, challenge_type, delivery_count, required_roles, reward_points, job_requirements, title \
                FROM challenge \
                WHERE start_time <= {int(time.time())} AND end_time >= {int(time.time())} AND required_distance <= {current_distance}")
            t = cur.fetchall()
            for tt in t:
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
                jobreq = {}
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
                if not d["data"]["object"]["cargo"] is None and not d["data"]["object"]["cargo"]["unique_id"] is None:
                    cargo = d["data"]["object"]["cargo"]["unique_id"]
                if not d["data"]["object"]["cargo"] is None and not d["data"]["object"]["cargo"]["mass"] is None:
                    cargo_mass = d["data"]["object"]["cargo"]["mass"]
                if not d["data"]["object"]["cargo"] is None and not d["data"]["object"]["cargo"]["damage"] is None:
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
                
                discordid = getUserInfo(userid = userid)["discordid"]
                notification(discordid, f"Delivery `#{logid}` accepted by challenge `{title}` (Challenge ID: `{challengeid}`)")
                cur.execute(f"INSERT INTO challenge_record VALUES ({userid}, {challengeid}, {logid}, {int(time.time())})")    
                conn.commit()

                current_delivery_count = 0
                if challenge_type == 1:
                    cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid} AND userid = {userid}")
                    current_delivery_count = cur.fetchone()[0]
                    current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
                elif challenge_type == 2:
                    cur.execute(f"SELECT COUNT(*) FROM challenge_record WHERE challengeid = {challengeid}")
                    current_delivery_count = cur.fetchone()[0]
                    current_delivery_count = 0 if current_delivery_count is None else int(current_delivery_count)
                
                if current_delivery_count >= delivery_count:
                    if challenge_type == 1:
                        cur.execute(f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                        t = cur.fetchall()
                        if len(t) == 0:
                            cur.execute(f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                            conn.commit()
                            discordid = getUserInfo(userid = userid)["discordid"]
                            notification(discordid, f"Ont-time personal challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{tseparator(reward_points)}` points.")
                    elif challenge_type == 3:
                        cur.execute(f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                        t = cur.fetchall()
                        if current_delivery_count >= (len(t) + 1) * delivery_count:
                            cur.execute(f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                            conn.commit()
                            discordid = getUserInfo(userid = userid)["discordid"]
                            notification(discordid, f"1x completed status of recurring personal challenge `{title}` (Challenge ID: `{challengeid}`) added: You received `{tseparator(reward_points)}` points. You got `{tseparator((len(t)+1) * reward_points)}` points from the challenge in total.")
                    elif challenge_type == 2:
                        cur.execute(f"SELECT * FROM challenge_completed WHERE challengeid = {challengeid}")
                        t = cur.fetchall()
                        if len(t) == 0:
                            curtime = int(time.time())
                            cur.execute(f"SELECT userid FROM challenge_record WHERE challengeid = {challengeid} ORDER BY timestamp ASC LIMIT {delivery_count}")
                            t = cur.fetchall()
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
                                cur.execute(f"INSERT INTO challenge_completed VALUES ({uid}, {challengeid}, {reward}, {curtime})")
                                discordid = getUserInfo(userid = uid)["discordid"]
                                notification(discordid, f"Company challenge `{title}` (Challenge ID: `{challengeid}`) completed: You received `{tseparator(reward)}` points.")
                            conn.commit()
                
    except:
        import traceback
        traceback.print_exc()

    return {"error": False, "response": "Logged"}