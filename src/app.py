# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
from discord import Colour
from io import BytesIO
import os, sys, json, requests, time, threading

config_path = os.environ["HUB_CONFIG_FILE"]

config_keys_order = ['abbr', 'name', 'distance_unit', 'truckersmp_bind', 'language', 'privacy', 'hex_color', 'logo_url', 'apidoc', 'language_dir', 'frontend_urls', 'apidomain', 'domain', 'server_ip', 'server_port', 'server_workers', 'database', 'mysql_host', 'mysql_user', 'mysql_passwd', 'mysql_db', 'mysql_ext', 'hcaptcha_secret', 'enabled_plugins', 'external_plugins', 'guild_id', 'in_guild_check', 'navio_api_token', 'navio_company_id', 'allowed_navio_ips', 'delivery_rules', 'delivery_log_channel_id', 'delivery_post_gifs', 'discord_client_id', 'discord_client_secret', 'discord_oauth2_url', 'discord_callback_url', 'discord_bot_token', 'team_update', 'member_welcome', 'rank_up', 'ranks', 'application_types', 'webhook_division', 'webhook_division_message', 'divisions', 'perms', 'roles', 'webhook_audit']

version = "v1.21.4"

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
        perms = {"admin": "0"}
    perms = cfg["perms"]
    for perm in perms.keys():
        roles = perms[perm]
        newroles = []
        for role in roles:
            try:
                newroles.append(int(role))
            except:
                pass
        perms[perm] = newroles
    cfg["perms"] = perms

    if not "server_workers" in cfg.keys():
        cfg["server_workers"] = 1

    if not "language" in cfg.keys():
        cfg["language"] = "en"

    if not "allowed_navio_ips" in cfg.keys():
        cfg["allowed_navio_ips"] = ["185.233.107.244"]

    tcfg = {}
    for key in config_keys_order:
        if key in cfg.keys():
            tcfg[key] = cfg[key]

    return tcfg

config_txt = open(config_path, "r").read()
config = json.loads(config_txt)
config = validateConfig(config)
tconfig = config
if not "hex_color" in config.keys():
    config["hex_color"] = "#2fc1f7"
hex_color = config["hex_color"][-6:]
try:
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
except:
    hex_color = "FFFFFF"
    rgbcolor = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
    config["rgbcolor"] = Colour.from_rgb(rgbcolor[0], rgbcolor[1], rgbcolor[2])
    config["intcolor"] = int(hex_color, 16)
config = Dict2Obj(config)

if os.path.exists(config.apidoc):
    app = FastAPI(openapi_url=f"/{config.abbr}/openapi.json", docs_url=f"/{config.abbr}/doc", redoc_url=None)
    def openapi():
        f = open(config.apidoc, "r")
        d = f.read().replace("/abbr", f"/{config.abbr}")
        return json.loads(d)
    app.openapi = openapi
else:
    app = FastAPI()