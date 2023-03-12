# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
import sys
import time

from discord import Colour
from fastapi import FastAPI

version = "v2.1.1"

config_path = os.environ["HUB_CONFIG_FILE"]

config_keys_order = ['abbr', 'name', 'language', 'distance_unit', 'truckersmp_bind', 'privacy', 'hex_color', 'logo_url', 'openapi', 'language_dir', 'frontend_urls', 'apidomain', 'domain', 'server_ip', 'server_port', 'server_workers', 'whitelist_ips', 'webhook_error', 'database', 'mysql_host', 'mysql_user', 'mysql_passwd', 'mysql_db', 'mysql_ext', 'mysql_pool_size', 'hcaptcha_secret', 'enabled_plugins', 'external_plugins', 'guild_id', 'in_guild_check', 'use_server_nickname', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules', 'delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_oauth2_url', 'discord_callback_url', 'discord_bot_token', 'team_update', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'perms', 'roles', 'webhook_audit']

config_sample = {
    "abbr": "",
    "name": "",
    "language": "en",
    "distance_unit": "metric",
    "truckersmp_bind": True,
    "privacy": False,
    "hex_color": "FFFFFF",
    "logo_url": "https://{domain}/images/logo.png",

    "openapi": "./openapi.json",
    "language_dir": "./languages",
    "frontend_urls": {
        "steam_callback": "https://{domain}/steam",
        "auth_message": "https://{domain}/auth?message={message}",
        "auth_token": "https://{domain}/auth?token={token}",
        "auth_mfa": "https://{domain}/auth?token={token}&mfa=true",
        "member": "https://{domain}/member?userid={userid}",
        "delivery": "https://{domain}/delivery?logid={logid}"
    },

    "apidomain": "drivershub.charlws.com",
    "domain": "",
    "server_ip": "127.0.0.1",
    "server_port": "7777",
    "server_workers": "1",
    "whitelist_ips": [],
    "webhook_error": "",

    "database": "mysql",
    "mysql_host": "localhost",
    "mysql_user": "",
    "mysql_passwd": "",
    "mysql_db": "_drivershub",
    "mysql_ext": "/var/lib/mysqlext/",
    "mysql_pool_size": "10",
    "hcaptcha_secret": "",

    "enabled_plugins": [],
    "external_plugins": [],

    "guild_id": "",
    "in_guild_check": True,
    "use_server_nickname": False,

    "tracker": "tracksim",
    "tracker_company_id": "",
    "tracker_api_token": "",
    "tracker_webhook_secret": "",
    "allowed_tracker_ips": ["109.106.1.243"],
    "delivery_rules": {
        "max_speed": "180",
        "max_profit": "1000000",
        "action": "block"
    },
    "delivery_log_channel_id": "",
    "delivery_post_gifs": ["https://c.tenor.com/fjTTED8MZxIAAAAC/truck.gif",
        "https://c.tenor.com/QhMgCV8uMvIAAAAC/airtime-weeee.gif",
        "https://c.tenor.com/VYt4iLQJWhcAAAAd/kid-spin.gif",
        "https://c.tenor.com/_aICF_XLbR4AAAAC/ck8car-driving.gif",
        "https://c.tenor.com/jEW-3JELMG4AAAAM/skidding-white-pick-up.gif",
        "https://c.tenor.com/JGw-jxHDAGoAAAAC/truck-lol.gif",
        "https://c.tenor.com/2B9tkbj7CVEAAAAM/explode-truck.gif",
        "https://c.tenor.com/Tl6l934qO70AAAAC/driving-truck.gif",
        "https://c.tenor.com/1SPfoAWWejEAAAAC/chevy-truck.gif",
        "https://c.tenor.com/MfGOJIgU22UAAAAC/ford-f100-truck.gif"],

    "discord_client_id": "",
    "discord_client_secret": "",
    "discord_oauth2_url": "",
    "discord_callback_url": "https://drivershub.charlws.com/{abbr}/auth/discord/callback",
    "discord_bot_token": "",

    "team_update": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "{name} has joined **VTC** as a **Driver**.",
            "image_url": "",
            "footer": {
                "text": "",
                "icon_url": ""
            },
            "timestamp": True
        }
    },

    "member_welcome": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "Welcome {name}.",
            "image_url": "https://{domain}/images/bg.jpg",
            "footer": {
                "text": "You are our #{userid} driver",
                "icon_url": ""
            },
            "timestamp": True
        },
        "role_change": []
    },
    
    "member_leave": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "Welcome {name}.",
            "image_url": "https://{domain}/images/bg.jpg",
            "footer": {
                "text": "You are our #{userid} driver",
                "icon_url": ""
            },
            "timestamp": True
        },
        "role_change": []
    },

    "rank_up": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "GG {mention}! You have ranked up to {rank}!",
            "image_url": "",
            "footer": {
                "text": "",
                "icon_url": ""
            },
            "timestamp": True
        }
    },
    "ranks": [
        {"points": "0", "name": "New Driver", "color": "#CCCCCC", "discord_role_id": ""}
    ],

    "application_types": [
        {"id": "1", "name": "Driver", "discord_role_id": "", "staff_role_id": ["20"], "message": "", "webhook": "", "note": "driver"},
        {"id": "2", "name": "Staff", "discord_role_id": "", "staff_role_id": ["20"], "message": "", "webhook": "", "note": ""},
        {"id": "3", "name": "LOA", "discord_role_id": "", "staff_role_id": ["20"], "message": "", "webhook": "", "note": ""},
        {"id": "4", "name": "Division", "discord_role_id": "", "staff_role_id": ["40"], "message": "", "webhook": "", "note": ""}
    ],

    "webhook_division": "",
    "webhook_division_message": "",
    "divisions": [],

    "perms": {
        "admin": ["0"],
        "config": [],
        "restart": [],

        "hrm": [],
        "disable_user_mfa": [],
        "update_user_discord": [],
        "delete_account_connections": [],
        "delete_user": [],
        "update_application_positions": [],
        "delete_dlog": [],

        "hr": [],
        "patch_username": [],
        "add_member": [],
        "update_member_roles": [],
        "update_member_points": [],
        "dismiss_member": [],
        "get_pending_user_list": [],
        "delete_application": [],
        "ban_user": [],

        "audit": [],
        "announcement": [],
        "challenge": [],
        "division": [],
        "downloads": [],
        "event": [],
        
        "driver": ["100"]
    },

    "roles": [
        {"id": "0", "name": "root", "color": "#000000"}
    ],

    "webhook_audit": ""
}

DH_START_TIME = int(time.time())

for argv in sys.argv:
    if argv.endswith(".py"):
        version += ".rc"

class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

def validateConfig(cfg):
    if not "perms" in cfg.keys():
        perms = config_sample["perms"]
    perms = cfg["perms"]
    for perm in perms.keys():
        roles = perms[perm]
        newroles = []
        try:
            for role in roles:
                try:
                    newroles.append(int(role))
                except:
                    pass
        except:
            pass
        perms[perm] = newroles
    cfg["perms"] = perms

    ranks = cfg["ranks"]
    newranks = []
    for i in range(len(ranks)):
        rank = ranks[i]
        if "distance" in rank.keys():
            rank["points"] = rank["distance"]
            del rank["distance"]
        if "discord_role_id" in rank.keys() and "points" in rank.keys() and "name" in rank.keys():
            newranks.append(rank)
    cfg["ranks"] = newranks

    divisions = cfg["divisions"]
    newdivisions = []
    for i in range(len(divisions)):
        division = divisions[i]
        if "id" in division.keys() and "name" in division.keys() and "role_id" in division.keys() and "point" in division.keys():
            try:
                # ensure they are integer
                int(division["id"])
                int(division["role_id"])
                int(division["point"])
                newdivisions.append(division)
            except:
                pass
    cfg["divisions"] = newdivisions

    roles = cfg["roles"]
    newroles = []
    for i in range(len(roles)):
        role = roles[i]
        if "id" in role.keys() and "name" in role.keys():
            newroles.append(role)
    cfg["roles"] = newroles

    application_types = cfg["application_types"]
    new_application_types = []
    reqs = ["id", "name", "discord_role_id", "staff_role_id", "message", "webhook", "note"]
    for i in range(len(application_types)):
        application_type = application_types[i]
        ok = True
        for req in reqs:
            if not req in application_type.keys():
                ok = False
        if ok:
            new_application_types.append(application_type)
    cfg["application_types"] = new_application_types

    if "apidoc" in cfg.keys():
        cfg["openapi"] = cfg["apidoc"]
        del cfg["apidoc"]
    
    external_plugins = cfg["external_plugins"]
    new_external_plugins = []
    for plugin in external_plugins:
        if plugin.replace(" ","") != "":
            new_external_plugins.append(plugin)
    cfg["external_plugins"] = new_external_plugins

    try:
        cfg["mysql_pool_size"] = int(cfg["mysql_pool_size"])
    except:
        cfg["mysql_pool_size"] = 10

    if "allowed_navio_ips" in cfg.keys():
        cfg["allowed_tracker_ips"] = cfg["allowed_navio_ips"]
        del cfg["allowed_navio_ips"]

    tcfg = {}
    for key in config_keys_order:
        if key in cfg.keys():
            tcfg[key] = cfg[key]
        else:
            tcfg[key] = config_sample[key]

    return tcfg

config_txt = open(config_path, "r", encoding="utf-8").read()
config = validateConfig(json.loads(config_txt))
tconfig = config

if not "hex_color" in config.keys():
    config["hex_color"] = "2fc1f7"
hex_color = config["hex_color"][-6:]
try:
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
except:
    hex_color = "2fc1f7"
    config["hex_color"] = "2fc1f7"
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)

config = Dict2Obj(config)

if os.path.exists(config.openapi):
    app = FastAPI(title="Drivers Hub", version=version[1:], \
            openapi_url=f"/{config.abbr}/openapi.json", docs_url=f"/{config.abbr}/doc", redoc_url=None)
    
    OPENAPI_RESPONSES = '"responses": {"200": {"description": "Success"}, "204": {"description": "Success (No Content)"}, "400": {"description": "Bad Request - You need to correct the json data."}, "401": {"description": "Unauthorized - You need to use a valid token."}, "403": {"description": "Forbidden - You don\'t have permission to access the response."}, "404": {"description": "Not Found - The resource could not be found."}, "429": {"description": "Too Many Requests - You are being ratelimited."}, "500": {"description": "Internal Server Error - Usually caused by a bug or database issue."}, "503": {"description": "Service Unavailable - Database outage or rate limited."}}'
    
    openapi_data = json.loads(open(config.openapi, "r", encoding="utf-8").read()
                            .replace("/abbr", f"/{config.abbr}")
                            .replace('"responses": {}', OPENAPI_RESPONSES))
    def openapi():
        return openapi_data
    app.openapi = openapi
    
else:
    app = FastAPI(title="Drivers Hub", version=version[1:])