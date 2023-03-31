# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import os
import sys
import time

from fastapi import FastAPI

version = "v2.3.0"

config_path = os.environ["HUB_CONFIG_FILE"]

config_keys_order = ['abbr', 'name', 'language', 'distance_unit', 'privacy', 'hex_color', 'logo_url', 'openapi', 'language_dir', 'frontend_urls', 'apidomain', 'domain', 'server_ip', 'server_port', 'server_workers', 'whitelist_ips', 'webhook_error', 'database', 'mysql_host', 'mysql_user', 'mysql_passwd', 'mysql_db', 'mysql_ext', 'mysql_pool_size', 'hcaptcha_secret', 'enabled_plugins', 'external_plugins', 'guild_id', 'must_join_guild', 'use_server_nickname', 'allow_custom_profile', 'avatar_domain_whitelist', 'required_connections', 'register_methods', 'tracker', 'tracker_company_id', 'tracker_api_token', 'tracker_webhook_secret', 'allowed_tracker_ips', 'delivery_rules', 'delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_bot_token', 'steam_api_key', 'smtp_host', 'smtp_port', 'smtp_email', 'smtp_passwd', 'email_template', 'member_accept', 'member_welcome', 'member_leave', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'economy', 'perms', 'roles', 'webhook_audit']

config_sample = {
    "abbr": "",
    "name": "",
    "language": "en",
    "distance_unit": "metric",
    "privacy": False,
    "hex_color": "FFFFFF",
    "logo_url": "https://{domain}/images/logo.png",

    "openapi": "./openapi.json",
    "language_dir": "./languages",
    "frontend_urls": {
        "steam_callback": "https://{domain}/connectSteam",
        "discord_callback": "https://{domain}/connectDiscord",
        "auth_message": "https://{domain}/auth?message={message}",
        "auth_token": "https://{domain}/auth?token={token}",
        "auth_mfa": "https://{domain}/auth?token={token}&mfa=true",
        "member": "https://{domain}/member?userid={userid}",
        "delivery": "https://{domain}/delivery?logid={logid}",
        "email_confirm": "https://{domain}/emailConfirm?secret={secret}"
    },

    "apidomain": "drivershub.charlws.com",
    "domain": "",
    "server_ip": "127.0.0.1",
    "server_port": 7777,
    "server_workers": 1,
    "whitelist_ips": [],
    "webhook_error": "",

    "database": "mysql",
    "mysql_host": "localhost",
    "mysql_user": "",
    "mysql_passwd": "",
    "mysql_db": "_drivershub",
    "mysql_ext": "/var/lib/mysqlext/",
    "mysql_pool_size": 10,
    "hcaptcha_secret": "",

    "enabled_plugins": [],
    "external_plugins": [],

    "guild_id": "",
    "must_join_guild": True,
    "use_server_nickname": True,
    "allow_custom_profile": True,
    "avatar_domain_whitelist": ["charlws.com", "cdn.discordapp.com", "steamstatic.com"],
    "required_connections": ["discord", "email", "truckersmp"],
    "register_methods": ["email", "discord", "steam"],

    "tracker": "tracksim",
    "tracker_company_id": "",
    "tracker_api_token": "",
    "tracker_webhook_secret": "",
    "allowed_tracker_ips": ["109.106.1.243"],
    "delivery_rules": {
        "max_speed": 180,
        "max_profit": 1000000,
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
    "discord_bot_token": "",
    "steam_api_key": "",
    
    "smtp_host": "",
    "smtp_port": "",
    "smtp_email": "",
    "smtp_passwd": "",
    "email_template": {
        "register": {
            "subject": "Register Acccount",
            "from_email": "VTC <email>",
            "html": "You are registering an account in Drivers Hub. Please click the link below to verify your email.<br>{link}",
            "plain": "You are registering an account in Drivers Hub. Please click the link below to verify your email.\n{link}"
        },
        "update_email": {
            "subject": "Update Email",
            "from_email": "VTC <email>",
            "html": "You are updating your email in Drivers Hub. Please click the link below to verify your email.<br>{link}",
            "plain": "You are updating your email in Drivers Hub. Please click the link below to verify your email.\n{link}"
        },
        "reset_password": {
            "subject": "Reset Password",
            "from_email": "VTC <email>",
            "html": "You are resetting your password in Drivers Hub. Please click the link below to continue.<br>{link}",
            "plain": "You are resetting your password in Drivers Hub. Please click the link below to continue.\n{link}"
        }
    },

    "member_accept": {
        "webhook_url": "",
        "channel_id": "",
        "content": "{mention}",
        "embed": {
            "title": "",
            "description": "{name} has joined **VTC**.",
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
        {"points": 0, "name": "New Driver", "color": "#CCCCCC", "discord_role_id": ""}
    ],

    "application_types": [
        {"id": 1, "name": "Driver", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": "driver"},
        {"id": 2, "name": "Staff", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": ""},
        {"id": 3, "name": "LOA", "discord_role_id": "", "staff_role_id": [20], "message": "", "webhook": "", "note": ""},
        {"id": 4, "name": "Division", "discord_role_id": "", "staff_role_id": [40], "message": "", "webhook": "", "note": ""}
    ],

    "webhook_division": "",
    "webhook_division_message": "",
    "divisions": [],
    
    "economy": {
        "trucks": [{
            "id": "brand.model",
            "brand": "Brand",
            "model": "Model",
            "price": 1000000
        }],
        "garages": [{
            "id": "berlin",
            "name": "Berlin Garage",
            "x": 9682.941,
            "z": -10721.3594,
            "price": 1000000,
            "base_slots": 3,
            "slot_price": 10000
        }],
        "truck_refund": 0.3,
        "scrap_refund": 0.1,
        "garage_refund": 0.5,
        "slot_refund": 0.5,

        "usd_to_coin": 0.5,
        "eur_to_coin": 0.6,
        "wear_ratio": 1,
        "revenue_share_to_company": 0.4,
        "truck_rental_cost": 0.01,

        "max_wear_before_service": 0.1,
        "max_distance_before_scrap": 500000,
        "unit_service_price": 1200,

        "allow_purchase_truck": True,
        "allow_purchase_garage": True,
        "allow_purchase_slot": True,
        "enable_balance_leaderboard": True
    },

    "perms": {
        "admin": [0],
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
        "manage_profile": [],
        "add_member": [],
        "update_member_roles": [],
        "update_member_points": [],
        "dismiss_member": [],
        "get_pending_user_list": [],
        "delete_application": [],
        "ban_user": [],

        "economy_manager": [],
        "balance_manager": [],
        "accountant": [],
        "truck_manager": [],
        "garage_manager": [],

        "audit": [],
        "announcement": [],
        "challenge": [],
        "division": [],
        "downloads": [],
        "event": [],
        
        "driver": [100]
    },

    "roles": [
        {"id": 0, "name": "root", "color": "#000000"}
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

def isfloat(t):
    try:
        float(t)
        return True
    except:
        return False
    
def validateConfig(cfg):
    tcfg = {}
    for key in config_keys_order:
        if key in cfg.keys():
            tcfg[key] = cfg[key]
        else:
            tcfg[key] = config_sample[key]
    cfg = tcfg

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
        try:
            rank["points"] = int(rank["points"])
        except:
            continue
        try:
            int(rank["discord_role_id"])
            # just validation, no need t oconvert, as discord_role_id is not mandatory
        except:
            rank["discord_role_id"] = None
        if "discord_role_id" in rank.keys() and "points" in rank.keys() and "name" in rank.keys():
            newranks.append(rank)
    cfg["ranks"] = newranks

    divisions = cfg["divisions"]
    newdivisions = []
    for i in range(len(divisions)):
        division = divisions[i]
        if "point" in division.keys():
            division["points"] = division["point"]
            del division["point"]
        if "id" in division.keys() and "name" in division.keys() and "role_id" in division.keys() and "points" in division.keys():
            try:
                division["id"] = int(division["id"])
                division["role_id"] = int(division["role_id"])
                division["points"] = int(division["points"])
                newdivisions.append(division)
            except:
                pass
    cfg["divisions"] = newdivisions
    
    economy_trucks = cfg["economy"]["trucks"]
    new_economy_trucks = []
    for i in range(len(economy_trucks)):
        truck = economy_trucks[i]
        if "id" in truck.keys() and "brand" in truck.keys() and "model" in truck.keys() and "price" in truck.keys():
            try:
                truck["price"] = int(truck["price"])
            except:
                pass
            new_economy_trucks.append(truck)
    cfg["economy"]["trucks"] = new_economy_trucks
    
    economy_garages = cfg["economy"]["garages"]
    new_economy_garages = []
    for i in range(len(economy_garages)):
        garage = economy_garages[i]
        if "id" in garage.keys() and "name" in garage.keys() and "x" in garage.keys() and "z" in garage.keys() and "price" in garage.keys() and "base_slots" in garage.keys() and "slot_price" in garage.keys():
            try:
                garage["x"] = float(garage["x"])
                garage["z"] = float(garage["z"])
                garage["price"] = int(garage["price"])
                garage["base_slots"] = min(int(garage["base_slots"]), 10)
                garage["slot_price"] = int(garage["slot_price"])
            except:
                pass
            new_economy_garages.append(garage)
    cfg["economy"]["garages"] = new_economy_garages

    economy_must_float = ['truck_refund', 'scrap_refund', 'garage_refund', 'slot_refund', 'usd_to_coin', 'eur_to_coin', 'wear_ratio', 'revenue_share_to_company', 'truck_rental_cost', 'max_wear_before_service', 'max_distance_before_scrap', 'unit_service_price']
    for item in economy_must_float:
        if not item in cfg["economy"].keys() or not isfloat(cfg["economy"][item]):
            cfg["economy"][item] = config_sample["economy"][item]
        else:
            cfg["economy"][item] = float(cfg["economy"][item])

    economy_must_bool = ['allow_purchase_truck', 'allow_purchase_garage', 'allow_purchase_slot', 'allow_purchase_merch', 'enable_balance_leaderboard']
    for item in economy_must_bool:
        if not item in cfg["economy"].keys() or type(cfg["economy"][item]) != bool:
            cfg["economy"][item] = config_sample["economy"][item]

    roles = cfg["roles"]
    newroles = []
    for i in range(len(roles)):
        role = roles[i]
        try:
            role["id"] = int(role["id"])
        except:
            continue
        if "id" in role.keys() and "name" in role.keys():
            newroles.append(role)
    cfg["roles"] = newroles

    application_types = cfg["application_types"]
    new_application_types = []
    reqs = ["id", "name", "discord_role_id", "staff_role_id", "message", "webhook", "note"]
    for i in range(len(application_types)):
        application_type = application_types[i]
        try:
            application_type["id"] = int(application_type["id"])
            for i in range(len(application_type["staff_role_id"])):
                application_type["staff_role_id"][i] = int(application_type["staff_role_id"][i])
        except:
            continue
        try:
            int(application_type["discord_role_id"])
            # just validation, no need t oconvert, as discord_role_id is not mandatory
        except:
            application_type["discord_role_id"] = None
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

    if not "member_accept" in cfg.keys() and "team_update" in cfg.keys():
        cfg["member_accept"] = cfg["team_update"]
        del cfg["team_update"]
    
    if not "discord_callback" in cfg["frontend_urls"].keys():
        cfg["frontend_urls"]["discord_callback"] = f"https://{cfg['domain']}/connectDiscord"
    
    if not "email_confirm" in cfg["frontend_urls"].keys():
        cfg["frontend_urls"]["email_confirm"] = f"https://{cfg['domain']}/emailConfirm?secret={{secret}}"

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
    # validate color
    tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["int_color"] = int(hex_color, 16)
except:
    hex_color = "2fc1f7"
    config["hex_color"] = "2fc1f7"
    config["int_color"] = int(hex_color, 16)

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