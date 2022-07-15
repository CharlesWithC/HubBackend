# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
from typing import Optional
import json, os, sys
import threading, time
from sys import exit

from app import app, config, config_txt, config_path
from db import newconn
from functions import *
import multilang as ml

def ChangeAllIntToStr(tconfig):
    for key, value in tconfig.items():
        if type(tconfig[key]) == dict:
            tconfig[key] = ChangeAllIntToStr(value)
        elif type(tconfig[key]) == int:
            tconfig[key] = str(value)
    return tconfig

@app.get(f"/{config.vtcprefix}/config")
async def getConfig(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /config', 30, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    tconfig = json.loads(config_txt)
    toremove = ["vtcprefix", "apidoc", "domain", "dhdomain", "server_ip", "server_port",\
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "telemetry_innodb_dir", "language_dir", \
            "enabled_plugins", "external_plugins", "steam_callback_url"]
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
    os.system(f"./launcher hub restart {config.vtcprefix} &")

@app.patch(f"/{config.vtcprefix}/config")
async def patchConfig(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'PATCH /config', 600, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    conn = newconn()
    cur = conn.cursor()

    tconfig = json.loads(config_txt)

    form = await request.form()
    newconfig = json.loads(form["config"])

    toremove = ["vtcprefix", "apidoc", "domain", "dhdomain", "server_ip", "server_port",\
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "telemetry_innodb_dir", "language_dir", \
            "enabled_plugins", "external_plugins", "steam_callback_url"]
    musthave = ["vtcname", "vtclogo", "hexcolor", \
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
        for t in ["navio_company_id"]:
            tconfig[t] = int(tconfig[t])

        
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

    await AuditLog(adminid, "Updated config")
    await AuditLog(adminid, "Reloaded service")

    threading.Thread(target=reload).start()

    return {"error": False}

@app.post(f"/{config.vtcprefix}/reload")
async def reloadService(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /reload', 600, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]

    await AuditLog(adminid, "Reloaded service")

    threading.Thread(target=reload).start()

    return {"error": False}

@app.get(f"/{config.vtcprefix}/auditlog")
async def getAuditLog(page: int, request: Request, response: Response, authorization: str = Header(None), userid: Optional[int] = -1, operation: Optional[str] = ""):
    rl = ratelimit(request.client.host, 'GET /auditlog', 30, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, required_permission = ["admin", "audit"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    if page <= 0:
        page = 1

    operation = operation.lower().replace("'","''")

    limit = ""
    if userid != -1:
        limit = f"AND userid = {userid}"

    cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%{operation}%' {limit} ORDER BY timestamp DESC LIMIT {(page - 1) * 30}, 30")
    t = cur.fetchall()
    ret = []
    for tt in t:
        cur.execute(f"SELECT name FROM user WHERE userid = {tt[0]}")
        p = cur.fetchall()
        name = "Unknown"
        if len(p) > 0:
            name = p[0][0]
        if tt[0] == -999:
            name = "System"
        ret.append({"timestamp": tt[2], "user": name, "operation": tt[1]})

    cur.execute(f"SELECT COUNT(*) FROM auditlog")
    t = cur.fetchall()
    tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": page, "tot": tot}}