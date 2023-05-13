# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import hashlib
import hmac
import json
import time
import traceback
from datetime import datetime
from random import randint

from dateutil import parser
from fastapi import Header, Request, Response

import multilang as ml
from config import validateConfig
from functions import *
from api import tracebackHandler

JOB_REQUIREMENTS = ["source_city_id", "source_company_id", "destination_city_id", "destination_company_id", "minimum_distance", "cargo_id", "minimum_cargo_mass",  "maximum_cargo_damage", "maximum_speed", "maximum_fuel", "minimum_profit", "maximum_profit", "maximum_offence", "allow_overspeed", "allow_auto_park", "allow_auto_load", "must_not_be_late", "must_be_special", "minimum_average_speed", "maximum_average_speed", "minimum_average_fuel", "maximum_average_fuel"]
JOB_REQUIREMENT_DEFAULT = {"source_city_id": "", "source_company_id": "", "destination_city_id": "", "destination_company_id": "", "minimum_distance": -1, "cargo_id": "", "minimum_cargo_mass": -1, "maximum_cargo_damage": -1, "maximum_speed": -1, "maximum_fuel": -1, "minimum_profit": -1, "maximum_profit": -1, "maximum_offence": -1, "allow_overspeed": 1, "allow_auto_park": 1, "allow_auto_load": 1, "must_not_be_late": 0, "must_be_special": 0, "minimum_average_speed": -1, "maximum_average_speed": -1, "minimum_average_fuel": -1, "maximum_average_fuel": -1}

async def FetchRoute(app, gameid, userid, logid, trackerid, request = None, dhrid = None):
    if request is None:
        request = Request(scope={"type":"http", "app": app})
    try:
        r = await arequests.get(app, f"https://api.tracksim.app/v1/jobs/{trackerid}/route", headers = {"Authorization": f"Api-Key {app.config.tracker_api_token}"}, timeout = 15, dhrid = dhrid)
    except:
        return {"error": f"{app.tracker} {ml.ctr(request, 'api_timeout')}"}
    if r.status_code != 200:
        try:
            resp = json.loads(r.text)
            if "error" in resp.keys() and resp["error"] is not None:
                return {"error": app.tracker + " " + resp["error"]}
            elif "message" in resp.keys() and resp["message"] is not None:
                return {"error": app.tracker + " " + resp["message"]}
            elif len(r.text) <= 64:
                return {"error": app.tracker + " " + r.text}
            else:
                return {"error": app.tracker + " " + ml.tr(request, "unknown_error")}
        except Exception as exc:
            await tracebackHandler(request, exc, traceback.format_exc())
            return {"error": app.tracker + " " + ml.tr(request, "unknown_error")}
    d = json.loads(r.text)
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

    if dhrid is None:
        dhrid = genrid()
        await app.db.new_conn(dhrid, extra_time = 5)
    
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
            dhrid = genrid()
            await app.db.new_conn(dhrid, extra_time = 5)
            continue
    
    return True
        
async def post_setup(response: Response, request: Request, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /tracksim/setup', 60, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin"], allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    latest_config = validateConfig(json.loads(open(app.config_path, "r", encoding="utf-8").read()))
    
    uinfo = await GetUserInfo(request, userid = au["userid"], include_email = True)
    email = uinfo["email"]

    r = await arequests.post(app, "https://api.tracksim.app/oauth/setup/chub-start", data = {"vtc_name": app.config.name, "vtc_logo": app.config.logo_url, "email": email, "webhook": f"https://{app.config.domain}{app.config.prefix}/tracksim/update"}, dhrid = dhrid)
    if r.status_code != 200:
        response.status_code = r.status_code
        try:
            d = json.loads(r.text)
            return {"error": d["error"]}
        except:
            return {"error": r.text}

    d = json.loads(r.text)
    company_id = d["company_id"]
    api_key = d["api_key"]["key"]
    webhook_secret = d["webhook_secret"]

    latest_config["tracker_company_id"] = str(company_id)
    app.config.tracker_company_id = str(company_id)
    latest_config["tracker_api_token"] = api_key
    app.config.tracker_api_token = api_key
    latest_config["tracker_webhook_secret"] = webhook_secret
    app.config.tracker_webhook_secret = webhook_secret
    latest_config["allowed_tracker_ips"] = ["109.106.1.243"]
    app.config.allowed_tracker_ips = ["109.106.1.243"]
    out = json.dumps(latest_config, indent=4, ensure_ascii=False)
    open(app.config_path, "w", encoding="utf-8").write(out)

    return Response(status_code=204)

async def post_update(response: Response, request: Request, TrackSim_Signature: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    if request.client.host not in app.config.allowed_tracker_ips:
        response.status_code = 403
        await AuditLog(request, -999, ml.ctr(request, "rejected_tracksim_webhook_post_ip", var = {"ip": request.client.host}))
        return {"error": "Validation failed"}
    
    if request.headers["Content-Type"] == "application/x-www-form-urlencoded":
        d = await request.form()
    elif request.headers["Content-Type"] == "application/json":
        d = await request.json()
    else:
        response.status_code = 400
        return {"error": "Unsupported content type"}
    sig = hmac.new(app.config.tracker_webhook_secret.encode(), msg=json.dumps(d).encode(), digestmod=hashlib.sha256).hexdigest()
    if sig != TrackSim_Signature:
        response.status_code = 403
        await AuditLog(request, -999, ml.ctr(request, "rejected_tracksim_webhook_post_signature", var = {"ip": request.client.host}))
        return {"error": "Validation failed"}
    
    if d["object"] != "event":
        response.status_code = 400
        return {"error": "Only events are accepted."}
    e = d["type"]
    if e == "company_driver.detached":
        steamid = int(d["data"]["object"]["steam_id"])
        await app.db.execute(dhrid, f"SELECT uid, userid, name, discordid FROM user WHERE steamid = {steamid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": "User not found."}
        uid = t[0][0]
        userid = t[0][1]
        name = t[0][2]
        discordid = t[0][3]
        await AuditLog(request, uid, ml.ctr(request, "member_resigned_audit", var = {"username": name, "uid": uid}))
        
        await app.db.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
        await app.db.commit(dhrid)

        def setvar(msg):
            return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace(f"{uid}", str(uid))
        
        for meta in app.config.member_leave:
            meta = Dict2Obj(meta)
            if meta.webhook_url != "" or meta.channel_id != "":
                await AutoMessage(app, meta, setvar)
            
            if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
                for role in meta.role_change:
                    try:
                        if int(role) < 0:
                            r = await arequests.delete(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}, timeout = 3, dhrid = dhrid)
                            if r.status_code // 100 != 2:
                                err = json.loads(r.text)
                                await AuditLog(request, -998, ml.ctr(request, "error_removing_discord_role", var = {"code": err["code"], "discord_role": str(-int(role)), "user_discordid": discordid, "message": err["message"]}))
                        elif int(role) > 0:
                            r = await arequests.put(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}, timeout = 3, dhrid = dhrid)
                            if r.status_code // 100 != 2:
                                err = json.loads(r.text)
                                await AuditLog(request, -998, ml.ctr(request, "error_adding_discord_role", var = {"code": err["code"], "discord_role": int(role), "user_discordid": discordid, "message": err["message"]}))
                    except:
                        pass

        if discordid is not None:
            headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}
            try:
                r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers = headers, timeout = 3, dhrid = dhrid)
                d = json.loads(r.text)
                if "roles" in d:
                    roles = d["roles"]
                    curroles = []
                    for role in roles:
                        if role in list(app.rankrole.values()):
                            curroles.append(role)
                    for role in curroles:
                        r = await arequests.delete(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{role}', headers = headers, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(request, -998, ml.ctr(request, "error_removing_discord_role", var = {"code": err["code"], "discord_role": role, "user_discordid": discordid, "message": err["message"]}))
            except:
                pass
        
        return {"error": "User resigned."}

    steamid = int(d["data"]["object"]["driver"]["steam_id"])
    await app.db.execute(dhrid, f"SELECT userid, name, uid, discordid FROM user WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": "User not found."}
    userid = t[0][0]
    username = t[0][1]
    uid = t[0][2]
    discordid = t[0][3]
    trackerid = d["data"]["object"]["id"]

    duplicate = False # NOTE only for debugging purpose
    logid = -1
    await app.db.execute(dhrid, f"SELECT logid FROM dlog WHERE trackerid = {trackerid} AND tracker_type = 2")
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
    xp = 0
    isdelivered = 0
    offence = 0
    if e == "job.delivered":
        revenue = float(d["data"]["object"]["events"][-1]["meta"]["revenue"])
        isdelivered = 1
        xp = d["data"]["object"]["events"][-1]["meta"]["earnedXP"]
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
    
    if driven_distance < 0:
        driven_distance = 0
    top_speed = d["data"]["object"]["truck"]["top_speed"] * 3.6 # m/s => km/h
    parser.parse(d["data"]["object"]["start_time"]).timestamp()
    parser.parse(d["data"]["object"]["stop_time"]).timestamp()

    delivery_rule_ok = True
    
    mod_revenue = revenue # modified revenue
    if "action" in app.config.__dict__["delivery_rules"].__dict__.keys() \
            and app.config.__dict__["delivery_rules"].__dict__["action"] != "bypass":
        action = app.config.__dict__["delivery_rules"].__dict__["action"]
        delivery_rules = app.config.__dict__["delivery_rules"].__dict__
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
        await AuditLog(request, uid, ml.ctr(request, "delivery_blocked_due_to_rules", var = {"tracker": app.tracker, "trackerid": trackerid}))
        await notification(request, "dlog", uid, ml.tr(request, "delivery_blocked_due_to_rules", var = {"tracker": app.tracker, "trackerid": trackerid}, force_lang = await GetUserLanguage(request, uid)))
        response.status_code = 403
        return {"error": "Blocked due to delivery rules."}

    if not duplicate:
        await app.db.execute(dhrid, f"INSERT INTO dlog(userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({userid}, '{compress(json.dumps(d,separators=(',', ':')))}', {top_speed}, {int(time.time())}, {isdelivered}, {mod_revenue}, {munitint}, {fuel_used}, {driven_distance}, {trackerid}, 2, 0)")
        await app.db.commit(dhrid)
        await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
        logid = (await app.db.fetchone(dhrid))[0]

        if "tracker" in app.config.plugins:
            asyncio.create_task(FetchRoute(app, munitint, userid, logid, trackerid))

        uid = (await GetUserInfo(request, userid = userid))["uid"]
        await notification(request, "dlog", uid, ml.tr(request, "job_submitted", var = {"logid": logid}, force_lang = await GetUserLanguage(request, uid)), no_discord_notification = True)

    if app.config.delivery_log_channel_id != "" and not duplicate:
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
                    GIFS = app.config.delivery_post_gifs
                    if len(GIFS) == 0:
                        GIFS = [""]
                    k = randint(0, len(GIFS)-1)
                    gifurl = GIFS[k]
                    if not isurl(gifurl):
                        gifurl = ""
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
                                        {"name": ml.ctr(request, "xp_earned"), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": multiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}}]}
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
                                        {"name": ml.ctr(request, "xp_earned"), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": multiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}}]}
                    try:
                        r = await arequests.post(app, f"https://discord.com/api/v10/channels/{app.config.delivery_log_channel_id}/messages", headers = headers, data=json.dumps(data), dhrid = dhrid)
                        if r.status_code == 401:
                            DisableDiscordIntegration(app)
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
                                        {"name": ml.tr(request, "xp_earned", force_lang = language), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}}]}
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
                                        {"name": ml.tr(request, "xp_earned", force_lang = language), "value": f"{tseparator(xp)}", "inline": True}],
                                    "footer": {"text": umultiplayer}, "color": int(app.config.hex_color, 16),\
                                    "timestamp": str(datetime.now()), "image": {"url": gifurl}}]}
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
                    required_roles = str2list(tt[3])[:20]
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
                    if jobreq["source_city_id"] != "" and source_city not in jobreq["source_city_id"].split(","):
                        continue
                    if jobreq["source_company_id"] != "" and source_company not in jobreq["source_company_id"].split(","):
                        continue
                    if jobreq["destination_city_id"] != "" and destination_city not in jobreq["destination_city_id"].split(","):
                        continue
                    if jobreq["destination_company_id"] != "" and destination_company not in jobreq["destination_company_id"].split(","):
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

                    auto_park = d["data"]["object"]["events"][-1]["meta"]["autoParked"]
                    auto_load = d["data"]["object"]["events"][0]["meta"]["autoLoaded"]
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
                                uid = (await GetUserInfo(request, userid = userid))["uid"]
                                await notification(request, "challenge", uid, ml.tr(request, "one_time_personal_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points)}, force_lang = await GetUserLanguage(request, uid)))
                        elif challenge_type == 3:
                            await app.db.execute(dhrid, f"SELECT points FROM challenge_completed WHERE challengeid = {challengeid} AND userid = {userid}")
                            t = await app.db.fetchall(dhrid)
                            if current_delivery_count >= (len(t) + 1) * delivery_count:
                                await app.db.execute(dhrid, f"INSERT INTO challenge_completed VALUES ({userid}, {challengeid}, {reward_points}, {int(time.time())})")
                                await app.db.commit(dhrid)
                                uid = (await GetUserInfo(request, userid = userid))["uid"]
                                await notification(request, "challenge", uid, ml.tr(request, "recurring_challenge_completed_status_added", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward_points), "total_points": tseparator((len(t)+1) * reward_points)}, force_lang = await GetUserLanguage(request, uid)))
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
                                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                                    await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
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
                                    uid = (await GetUserInfo(request, userid = tuserid))["uid"]
                                    await notification(request, "challenge", uid, ml.tr(request, "company_challenge_completed", var = {"title": title, "challengeid": challengeid, "points": tseparator(reward)}, force_lang = await GetUserLanguage(request, uid)))
                                await app.db.commit(dhrid)
                except Exception as exc:
                    await tracebackHandler(request, exc, traceback.format_exc())
                
    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())

    try:
        if "economy" in app.config.plugins and isdelivered and not duplicate:
            economy_revenue = round(revenue)
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

                await app.db.execute(dhrid, f"UPDATE economy_truck SET odometer = odometer + {driven_distance}, damage = damage + {damage}, income = income + {economy_revenue} WHERE vehicleid = {vehicleid}")
                if current_damage + damage > app.config.economy.max_wear_before_service:
                    await app.db.execute(dhrid, f"UPDATE economy_truck SET status = -1 WHERE vehicleid = {vehicleid}")
                if current_odometer + driven_distance > app.config.economy.max_distance_before_scrap:
                    await app.db.execute(dhrid, f"UPDATE economy_truck SET status = -2 WHERE vehicleid = {vehicleid}")
                await app.db.commit(dhrid)
                
    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())

    return Response(status_code=204)
    
async def post_update_route(response: Response, request: Request, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /tracksim/update/route', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

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
        return r