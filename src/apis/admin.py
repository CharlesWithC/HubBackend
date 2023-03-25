# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import json
import math
import os
import threading
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config, config_path, tconfig, validateConfig
from db import aiosql
from functions import *

config_whitelist = ['name', 'language', 'distance_unit', 'privacy', 'hex_color', 'logo_url', 'guild_id', 'must_join_guild', 'use_server_nickname', 'allow_custom_profile', 'avatar_domain_whitelist', 'required_connections', 'register_methods', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules','delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_bot_token', 'steam_api_key', 'smtp_host', 'smtp_port', 'smtp_email', 'smtp_passwd', 'email_template', 'member_accept', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'economy', 'perms', 'roles', 'webhook_audit']

config_plugins = {"application": ["application_types"],
    "division": ["webhook_division", "webhook_division_message", "divisions"],
    "economy": ["economy"]}

config_protected = ["tracker_api_token", "tracker_webhook_secret", "discord_client_secret", "discord_bot_token", "steam_api_key", "smtp_passwd"]

backup_config = copy.deepcopy(tconfig)

@app.get(f"/{config.abbr}/config")
async def get_config(request: Request, response: Response, authorization: str = Header(None)):
    """Returns saved config (config) and loaded config (backup)"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /config', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "config"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    # current config
    try:
        orgcfg = validateConfig(json.loads(open(config_path, "r", encoding="utf-8").read()))
        f = copy.deepcopy(orgcfg)
        ffconfig = {}

        # process whitelist
        for tt in f.keys():
            if tt in config_whitelist:
                ffconfig[tt] = f[tt]

        # remove sensitive data
        for tt in config_protected:
            ffconfig[tt] = ""

        # remove disabled plugins
        for t in config_plugins.keys():
            if not t in tconfig["enabled_plugins"]:
                for tt in config_plugins[t]:
                    if tt in ffconfig.keys():
                        del ffconfig[tt]
    except:
        ffconfig = {}
        traceback.print_exc()
    
    # old config
    t = copy.deepcopy(backup_config)
    ttconfig = {}

    # process whitelist
    for tt in t.keys():
        if tt in config_whitelist:
            ttconfig[tt] = t[tt]

    # remove sensitive data
    for tt in config_protected:
        ttconfig[tt] = ""

    # remove disabled plugins
    for t in config_plugins.keys():
        if not t in tconfig["enabled_plugins"]:
            for tt in config_plugins[t]:
                if tt in ffconfig.keys():
                    del ttconfig[tt]

    return {"config": ffconfig, "backup": ttconfig}

def restart():
    os.system(f"nohup ./launcher tracker restart {config.abbr} > /dev/null")
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {config.abbr} > /dev/null")

@app.patch(f"/{config.abbr}/config")
async def patch_config(request: Request, response: Response, authorization: str = Header(None)):
    """Updates the config, only those specified in `config` will be updated
    
    JSON: `{"config": {}}`"""
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /config', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "config"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffid = au["userid"]
    userroles = au["roles"]

    data = await request.json()
    try:
        new_config = data["config"]
        if type(data["config"]) != dict:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    ttconfig = validateConfig(json.loads(open(config_path, "r", encoding="utf-8").read()))

    tracker = ""
    if "tracker" in new_config.keys():
        tracker = new_config["tracker"]
    elif "tracker" in ttconfig.keys():
        tracker = ttconfig["tracker"]
    else:
        tracker = "tracksim"

    for tt in new_config.keys():
        if tt in config_whitelist:
            if tracker == "tracksim" and tt in ["tracker_webhook_secret", "tracker_api_token"]:
                if new_config[tt].replace(" ", "").replace("\n","").replace("\t","") == "":
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_value", var = {"item": tt}, force_lang = au["language"])}
            elif tracker == "navio" and tt in ["tracker_api_token"]:
                if new_config[tt].replace(" ", "").replace("\n","").replace("\t","") == "":
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_value", var = {"item": tt}, force_lang = au["language"])}

            if tt in config_protected and tt not in ["tracker_webhook_secret", "tracker_api_token"]:
                if new_config[tt].replace(" ", "").replace("\n","").replace("\t","") == "":
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_value", var = {"item": tt}, force_lang = au["language"])}

            if tt == "distance_unit":
                if not new_config[tt] in ["metric", "imperial"]:
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_distance_unit", force_lang = au["language"])}
                
            if tt == "economy":
                if "garages" in tt.keys():
                    garages = tt["garages"]
                    for garage in garages:
                        if "base_slots" in garage.keys() and isint(garage["base_slots"]):
                            if garage["base_slots"] > 10:
                                return {"error": ml.tr(request, "value_too_large", var = {"item": "economy.garages.base_slots", "limit": "10"}, force_lang = au["language"])}
                
            if tt in ["privacy", "must_join_guild", "use_server_nickname"]:
                if type(new_config[tt]) != bool:
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_datatype_boolean", var = {"item": tt}, force_lang = au["language"])}

            if tt in ["guild_id", "tracker_company_id", "delivery_log_channel_id", "discord_client_id", "smtp_port"]:
                try:
                    int(new_config[tt])
                except:
                    if tt in ["delivery_log_channel_id", "tracker_company_id"] and new_config[tt] == "":
                        new_config[tt] = "0"
                    else:
                        response.status_code = 400
                        return {"error": ml.tr(request, "config_invalid_datatype_integer", var = {"item": tt}, force_lang = au["language"])}

            if tt == "hex_color":
                new_config[tt] = new_config[tt][-6:]
                hex_color = new_config[tt]
                try:
                    # validate color
                    tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    int(hex_color, 16)
                except:
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_hex_color", force_lang = au["language"])}

            if tt == "delivery_post_gifs":
                p = []
                for o in new_config[tt]:
                    if isurl(o):
                        p.append(o)
                new_config[tt] = p

            if tt in ["logo_url", "webhook_division", "webhook_audit"]:
                if new_config[tt] != "" and not isurl(new_config[tt]):
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_data_url", var = {"item": tt}, force_lang = au["language"])}

            if tt == "perms":
                newperms = new_config[tt]
                if not "admin" in newperms:
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_permission_admin_not_found", force_lang = au["language"])}
                perm_roles = intify(newperms["admin"])
                ok = False
                for role in userroles:
                    if role in perm_roles:
                        ok = True
                if not ok:
                    response.status_code = 400
                    return {"error": ml.tr(request, "config_invalid_permission_admin_protection", force_lang = au["language"])}

            if type(new_config[tt]) != dict and type(new_config[tt]) != list and type(new_config[tt]) != bool:
                ttconfig[tt] = copy.deepcopy(str(new_config[tt]))
            else:
                ttconfig[tt] = copy.deepcopy(new_config[tt])
    
    ttconfig = validateConfig(ttconfig)
    out = json.dumps(ttconfig, indent=4, ensure_ascii=False)
    if len(out) > 512000:
        response.status_code = 400
        return {"error": ml.tr(request, "content_too_long", var = {"item": "config", "limit": "512,000"}, force_lang = au["language"])}
    open(config_path, "w", encoding="utf-8").write(out)

    await AuditLog(dhrid, staffid, ml.ctr("updated_config"))

    return Response(status_code=204)

@app.post(f"/{config.abbr}/restart")
async def post_restart(request: Request, response: Response, authorization: str = Header(None)):
    """Restarts API service in a thread, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /restart', 600, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "restart"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    staffid = au["userid"]

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE userid = {staffid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret == "":
        response.status_code = 428
        return {"error": ml.tr(request, "mfa_required", force_lang = au["language"])}
    
    data = await request.json()
    try:
        otp = data["otp"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
    if not valid_totp(otp, mfa_secret):
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}

    await AuditLog(dhrid, staffid, ml.ctr("restarted_service"))

    threading.Thread(target=restart).start()

    return Response(status_code=204)

# get audit log (require audit / admin permission)
@app.get(f"/{config.abbr}/audit/list")
async def get_audit_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 30, staff_userid: Optional[int] = None, operation: Optional[str] = ""):
    """Returns a list of audit log"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /audit', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "audit"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    operation = convertQuotation(operation.lower())

    limit = ""
    if staff_userid is not None:
        limit = f"AND userid = {staff_userid}"
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 500:
        page_size = 500

    await aiosql.execute(dhrid, f"SELECT * FROM auditlog WHERE LOWER(operation) LIKE '%{operation}%' {limit} ORDER BY timestamp DESC LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"user": await GetUserInfo(dhrid, request, userid = tt[0]), "operation": tt[1], "timestamp": tt[2]})

    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM auditlog")
    t = await aiosql.fetchall(dhrid)
    tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}