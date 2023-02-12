# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import json
import math
import os
import sys
import threading
import time
from typing import Optional

import psutil
from discord import Colour
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config, config_path, tconfig, validateConfig
from db import aiosql
from functions import *

config_whitelist = ['name', 'language', 'distance_unit', 'truckersmp_bind', 'privacy', 'hex_color', 'logo_url', 'guild_id', 'in_guild_check', 'use_server_nickname', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules','delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_oauth2_url', 'discord_callback_url', 'discord_bot_token', 'team_update', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'perms', 'roles', 'webhook_audit']

config_plugins = {"application": ["application_types"],
    "division": ["webhook_division", "webhook_division_message", "divisions"]}

config_protected = ["tracker_api_token", "tracker_webhook_secret", "discord_client_secret", "discord_bot_token"]

backup_config = copy.deepcopy(tconfig)

# get config
@app.get(f"/{config.abbr}/config")
async def getConfig(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /config', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "config"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    # current config
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

    return {"error": False, "response": {"config": ffconfig, "backup": ttconfig}}

# thread to restart service
def restart():
    os.system(f"nohup ./launcher tracker restart {config.abbr} > /dev/null")
    time.sleep(3)
    os.system(f"nohup ./launcher hub restart {config.abbr} > /dev/null")
    aiosql.shutdown_lock = True
    time.sleep(2)
    aiosql.close_pool()
    time.sleep(5)
    if "HUB_KILLING" in os.environ.keys():
        sys.exit(0)
    os.environ["HUB_KILLING"] = "true"
    pid = os.getpid()
    ppid = os.getppid()
    parent = psutil.Process(ppid)
    children = parent.children(recursive=True)
    for child in children:
        if child.pid != pid:
            child.kill()
    os.kill(ppid, 15)
    sys.exit(1)

# update config
@app.patch(f"/{config.abbr}/config")
async def patchConfig(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /config', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "config"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    userroles = au["roles"]

    form = await request.form()
    try:
        formconfig = json.loads(form["config"])
        if len(form["config"]) > 150000:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "config", "limit": "150,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    ttconfig = validateConfig(json.loads(open(config_path, "r", encoding="utf-8").read()))

    for tt in formconfig.keys():
        if tt in config_whitelist:
            if tt in ["name", "logo_url", "guild_id", "discord_client_id", \
                    "discord_client_secret", "discord_oauth2_url", "discord_callback_url", "discord_bot_token"]:
                if formconfig[tt].replace(" ", "").replace("\n","").replace("\t","") == "":
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_value", var = {"item": tt}, force_lang = au["language"])}

            if tt == "distance_unit":
                if not formconfig[tt] in ["metric", "imperial"]:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_distance_unit", force_lang = au["language"])}
            
            if tt in ["truckersmp_bind", "privacy", "in_guild_check"]:
                if type(formconfig[tt]) != bool:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_datatype_boolean", var = {"item": tt}, force_lang = au["language"])}

            if tt in ["guild_id", "tracker_company_id", "delivery_log_channel_id", "discord_client_id"]:
                try:
                    int(formconfig[tt])
                except:
                    if tt in ["delivery_log_channel_id", "tracker_company_id"] and formconfig[tt] == "":
                        formconfig[tt] = "0"
                    else:
                        response.status_code = 400
                        return {"error": True, "descriptor": ml.tr(request, "config_invalid_datatype_integer", var = {"item": tt}, force_lang = au["language"])}

            if tt == "hex_color":
                formconfig[tt] = formconfig[tt][-6:]
                hex_color = formconfig[tt]
                try:
                    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
                    rgbcolor = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
                    intcolor = int(hex_color, 16)
                except:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_hex_color", force_lang = au["language"])}

            if tt == "delivery_post_gifs":
                p = []
                for o in formconfig[tt]:
                    if isurl(o):
                        p.append(o)
                formconfig[tt] = p

            if tt in ["logo_url", "discord_oauth2_url", "discord_callback_url", "webhook_division", "webhook_audit"]:
                if formconfig[tt] != "" and not isurl(formconfig[tt]):
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_data_url", var = {"item": tt}, force_lang = au["language"])}

            if tt == "perms":
                newperms = formconfig[tt]
                if not "admin" in newperms:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_permission_admin_not_found", force_lang = au["language"])}
                ar = newperms["admin"]
                adminroles = []
                for arr in ar:
                    adminroles.append(int(arr))
                ok = False
                for role in userroles:
                    if int(role) in adminroles:
                        ok = True
                if not ok:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "config_invalid_permission_admin_protection", force_lang = au["language"])}

            if type(formconfig[tt]) != dict and type(formconfig[tt]) != list and type(formconfig[tt]) != bool:
                ttconfig[tt] = copy.deepcopy(str(formconfig[tt]))
            else:
                ttconfig[tt] = copy.deepcopy(formconfig[tt])

    out = json.dumps(ttconfig, indent=4, ensure_ascii=False)
    open(config_path, "w", encoding="utf-8").write(out)

    await AuditLog(dhrid, adminid, "Updated config")

    return {"error": False}

# restart service
@app.post(f"/{config.abbr}/restart")
async def postRestart(request: Request, response: Response, authorization: str = Header(None)):    
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /restart', 600, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "restart"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    await aiosql.execute(dhrid, f"SELECT mfa_secret FROM user WHERE userid = {adminid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    if mfa_secret == "":
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "mfa_required", force_lang = au["language"])}
    
    form = await request.form()
    try:
        otp = int(form["otp"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
    if not valid_totp(otp, mfa_secret):
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await AuditLog(dhrid, adminid, "Restarted service")

    threading.Thread(target=restart).start()

    return {"error": False}

# get audit log (require audit / admin permission)
@app.get(f"/{config.abbr}/audit")
async def getAudit(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 30, staff_userid: Optional[int] = -1, operation: Optional[str] = ""):    
    dhrid = genrid()
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /audit', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "audit"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    if page <= 0:
        page = 1

    operation = convert_quotation(operation.lower())

    limit = ""
    if staff_userid != -1:
        limit = f"AND userid = {staff_userid}"
    
    if page_size <= 1:
        page_size = 1
    elif page_size >= 500:
        page_size = 500

    await aiosql.execute(dhrid, f"SELECT * FROM auditlog WHERE LOWER(operation) LIKE '%{operation}%' {limit} ORDER BY timestamp DESC LIMIT {(page - 1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"user": await getUserInfo(dhrid, userid = tt[0]), "operation": tt[1], "timestamp": str(tt[2])})

    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM auditlog")
    t = await aiosql.fetchall(dhrid)
    tot = t[0][0]

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}