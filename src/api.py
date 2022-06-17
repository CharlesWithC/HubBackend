# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
from captcha.image import ImageCaptcha
import json, base64, uuid
from io import BytesIO
import threading, time
import os
import sys
from sys import exit

from app import app, config, config_txt, config_path
from db import newconn
from functions import *
import multilang as ml

from importlib.machinery import SourceFileLoader

# Load external code before original code to prevent overwrite
for external_plugin in config.external_plugins:
    if os.path.exists(f"./external_plugins/{external_plugin}.py"):
        print("Loading external plugin: " + external_plugin)
        SourceFileLoader(external_plugin, f"./external_plugins/{external_plugin}.py").load_module()

import apis.auth
import apis.dlog
import apis.member
import apis.navio
import apis.user

if "announcement" in config.enabled_plugins:
    import plugins.announcement
if "application" in config.enabled_plugins:
    import plugins.application
if "division" in config.enabled_plugins:
    import plugins.division
if "downloads" in config.enabled_plugins:
    import plugins.downloads
if "event" in config.enabled_plugins:
    import plugins.event

@app.get(f'/{config.vtcprefix}/info')
async def home():
    return {"error": False, "response": f"{config.vtcname} Drivers Hub API v1.8.2 | Copyright (C) 2022 CharlesWithC"}

@app.get(f"/{config.vtcprefix}/version")
async def apiGetVersion(request: Request):
    return {"error": False, "response": "v1.8.2"}

@app.get(f"/{config.vtcprefix}/ip")
async def apiGetIP(request: Request):
    return {"error": False, "response": request.client.host}
    
@app.get(f"/{config.vtcprefix}/config")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")

    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
    
    if not isAdmin:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    tconfig = json.loads(config_txt)
    toremove = ["vtcprefix", "apidoc", "domain", "dhdomain", "server_ip", "server_port",\
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "telemetry_innodb_dir", "language_dir", \
            "enabled_plugins", "external_plugins", "navio_token", "discord_client_secret", "bot_token"]
    # vtcprefix will affect nginx settings, so it's not allowed to be changed
    # enabled_plugins are paid functions, so it's only changeable by developer
    # navio_token, discord_client_secret, bot_token are sensitive data, so it's only editable but not viewable
    
    if not "division" in tconfig["enabled_plugins"]:
        del tconfig["divisions"]

    for i in toremove:
        if i in tconfig:
            del tconfig[i]
    
    return {"error": False, "response": {"config": tconfig}}

def reload():
    time.sleep(5)
    os.system(f"./run hub restart atm &")

@app.patch(f"/{config.vtcprefix}/config")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")

    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
    
    if not isAdmin:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    tconfig = json.loads(config_txt)

    form = await request.form()
    newconfig = json.loads(form["config"])

    toremove = ["vtcprefix", "apidoc", "domain", "dhdomain", "server_ip", "server_port",\
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "telemetry_innodb_dir", "language_dir", \
            "enabled_plugins", "external_plugins"]
    musthave = ["vtcname", "vtclogo", "intcolor", "hexcolor", \
        "navio_token", "navio_company_id", "guild", \
        "discord_client_id", "discord_client_secret", "discord_oauth2_url", "discord_callback_url", "bot_token"]
    # those have to be removed from newconfig to prevent user changing them
            
    for i in toremove:
        if i in newconfig:
            del newconfig[i]
    
    for i in newconfig:
        if i in tconfig:
            if i == "distance_unit":
                if not newconfig[i] in ["metric", "imperial"]:
                    return {"error": True, "descriptor": "Invalid distance unit"}
            
            if i in musthave:
                if newconfig[i] == "" or newconfig[i] == 0:
                    return {"error": True, "descriptor": "Invalid value for " + i}
            
            if i == "perms":
                if newconfig[i]["admin"] != tconfig[i]["admin"]:
                    return {"error": True, "descriptor": "Roles with admin permission cannot be changed, please contact development team."}

            tconfig[i] = newconfig[i]

    open(config_path, "w").write(json.dumps(tconfig))

    threading.Thread(target=reload).start()

    return {"error": False, "response": "Config updated. Service will reload in a short time."}

@app.post(f"/{config.vtcprefix}/reload")
async def getAnnouncement(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "no_authorization_header")}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")

    isAdmin = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
    
    if not isAdmin:
        # response.status_code = 401
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    threading.Thread(target=reload).start()

    return {"error": False, "response": "Service will reload in a short time."}