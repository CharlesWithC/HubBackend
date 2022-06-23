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
    return {"error": False, "response": f"{config.vtcname} Drivers Hub API v1.8.8 | Copyright (C) 2022 CharlesWithC"}

@app.get(f"/{config.vtcprefix}/version")
async def apiGetVersion(request: Request):
    return {"error": False, "response": "v1.8.8"}

@app.get(f"/{config.vtcprefix}/ip")
async def apiGetIP(request: Request):
    return {"error": False, "response": request.client.host}

def ChangeAllIntToStr(tconfig):
    for key, value in tconfig.items():
        if type(tconfig[key]) == dict:
            tconfig[key] = ChangeAllIntToStr(value)
        elif type(tconfig[key]) == int:
            tconfig[key] = str(value)
    return tconfig

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
            "enabled_plugins", "external_plugins"]
    # vtcprefix will affect nginx settings, so it's not allowed to be changed
    # enabled_plugins are paid functions, so it's only changeable by developer
    # navio_token, discord_client_secret, bot_token are sensitive data, so it's only editable but not viewable
    
    if not "division" in tconfig["enabled_plugins"]:
        del tconfig["divisions"]
        
    for i in range(len(tconfig["welcome_roles"])):
        tconfig["welcome_roles"][i] = str(tconfig["welcome_roles"][i])

    tconfig["navio_token"] = ""
    tconfig["discord_client_secret"] = ""
    tconfig["bot_token"] = ""
    for i in toremove:
        if i in tconfig:
            del tconfig[i]
    
    tconfig = ChangeAllIntToStr(tconfig)
    
    return {"error": False, "response": {"config": tconfig}}

def reload():
    time.sleep(5)
    os.system(f"./launcher hub restart atm &")

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
    
    orgconfig = json.loads(config_txt)

    for i in newconfig:
        if i in tconfig:
            if i == "distance_unit":
                if not newconfig[i] in ["metric", "imperial"]:
                    return {"error": True, "descriptor": ml.tr(request, "invalid_distance_unit")}
            
            if i in musthave:
                if newconfig[i] == "" or newconfig[i] == 0:
                    return {"error": True, "descriptor": ml.tr(request, "invalid_value", var = {"key": i})}

            if i == "perms":
                if newconfig[i]["admin"] != tconfig[i]["admin"]:
                    return {"error": True, "descriptor": ml.tr(request, "admin_cannot_be_changed")}

            tconfig[i] = newconfig[i]
            
    try:
        for t in ["intcolor", "navio_company_id"]:
            tconfig[t] = int(tconfig[t])

        if len(tconfig["hexcolor"]) != 6:
            return {"error": True, "descriptor": ml.tr(request, "invalid_value", var = {"key": "hexcolor"})}
        
        for t in tconfig.keys():
            if type(orgconfig[t]) == int:
                tconfig[t] = int(tconfig[t])
            if type(tconfig[t]) != type(orgconfig[t]):
                return {"error": True, "descriptor": ml.tr(request, "invalid_value", var = {"key": t})}
        
        for perm in tconfig["perms"].keys():
            for i in range(len(tconfig["perms"][perm])):
                tconfig["perms"][perm][i] = int(tconfig["perms"][perm][i])
        
        for i in range(len(tconfig["welcome_roles"])):
            tconfig["welcome_roles"][i] = int(tconfig["welcome_roles"][i])
        
        if "divisions" in tconfig.keys():
            for i in range(0,len(tconfig["divisions"])):
                tconfig["divisions"][i]["id"] = int(tconfig["divisions"][i]["id"])
                tconfig["divisions"][i]["roleid"] = int(tconfig["divisions"][i]["roleid"])
                tconfig["divisions"][i]["point"] = int(tconfig["divisions"][i]["point"])
        
        for role in tconfig["roles"].keys():
            tconfig["roles"][role] = str(tconfig["roles"][role])
        
        for ranking in tconfig["ranking"].keys():
            tconfig["ranking"][ranking] = int(tconfig["ranking"][ranking])
        
        for rankname in tconfig["rankname"].keys():
            tconfig["rankname"][rankname] = str(tconfig["rankname"][rankname])
    
    except:
        import traceback
        traceback.print_exc()
        return {"error": True, "descriptor": ml.tr(request, "config_data_type_mismatch")}

    open(config_path, "w").write(json.dumps(tconfig))

    threading.Thread(target=reload).start()

    return {"error": False}

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

    return {"error": False}