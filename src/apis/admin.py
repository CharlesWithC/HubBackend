# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import Request, Header, Response
from typing import Optional
import json, copy, os, time
import threading

from app import app, config, tconfig, config_path
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.vtc_abbr}/config")
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

    toremove = ["vtc_abbr", "apidoc", "language_dir", "steam_callback_url", \
        "apidomain", "domain", "server_ip", "server_port", "server_workers", \
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "mysql_ext", \
            "enabled_plugins", "external_plugins", "hcaptcha_secret"]
    
    ttconfig = copy.deepcopy(tconfig)
    if not "division" in ttconfig["enabled_plugins"]:
        del ttconfig["divisions"]

    ttconfig["navio_api_token"] = ""
    ttconfig["discord_client_secret"] = ""
    ttconfig["discord_bot_token"] = ""
    
    for i in toremove:
        if i in ttconfig:
            del ttconfig[i]
    
    return {"error": False, "response": {"config": ttconfig}}

def reload():
    os.system(f"./launcher tracker restart {config.vtc_abbr} &")
    time.sleep(5)
    os.system(f"./launcher hub restart {config.vtc_abbr} &")

@app.patch(f"/{config.vtc_abbr}/config")
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

    form = await request.form()
    newconfig = json.loads(form["config"])

    toremove = ["vtc_abbr", "apidoc", "language_dir", "steam_callback_url", \
        "apidomain", "domain", "server_ip", "server_port", "server_workers", \
        "database", "mysql_host", "mysql_user", "mysql_passwd", "mysql_db", "mysql_ext", \
            "enabled_plugins", "external_plugins", "hcaptcha_secret"]
    musthave = ["vtc_name", "vtc_logo_link", "hex_color", \
        "navio_api_token", "navio_company_id", "guild_id", \
        "discord_client_id", "discord_client_secret", "discord_oauth2_url", "discord_callback_url", "discord_bot_token"]
            
    for i in toremove:
        if i in newconfig:
            del newconfig[i]
    
    ttconfig = copy.deepcopy(tconfig)
    orgconfig = copy.deepcopy(tconfig)

    # check must_have and distance_unit
    for i in newconfig:
        if i in ttconfig:
            if i == "distance_unit":
                if not newconfig[i] in ["metric", "imperial"]:
                    response.status_code = 400
                    return {"error": True, "descriptor": ml.tr(request, "invalid_distance_unit")}

            if i == "hex_color":
                newconfig[i] = newconfig[i][-6:]
            
            if i in musthave:
                if newconfig[i] == "":
                    newconfig[i] = orgconfig[i]

            ttconfig[i] = newconfig[i]
    
    # check item value type
    try:
        for t in ttconfig.keys():
            if type(ttconfig[t]) != type(orgconfig[t]):
                response.status_code = 400
                return {"error": True, "descriptor": ml.tr(request, "invalid_value", var = {"key": t})}
    
    except:
        import traceback
        traceback.print_exc()
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "config_data_type_mismatch")}

    # check if all necessary item exists
    for t in orgconfig.keys():
        if not t in ttconfig.keys():
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "invalid_value", var = {"key": t})}

    open(config_path, "w").write(json.dumps(ttconfig, indent=4))

    await AuditLog(adminid, "Updated config")
    await AuditLog(adminid, "Reloaded service")

    threading.Thread(target=reload).start()

    return {"error": False}

@app.post(f"/{config.vtc_abbr}/reload")
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

@app.get(f"/{config.vtc_abbr}/auditlog")
async def getAuditLog(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = -1, userid: Optional[int] = -1, operation: Optional[str] = "", pagelimit: Optional[int] = 30):
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
    
    if pagelimit <= 1:
        pagelimit = 1
    elif pagelimit >= 500:
        pagelimit = 500

    cur.execute(f"SELECT * FROM auditlog WHERE operation LIKE '%{operation}%' {limit} ORDER BY timestamp DESC LIMIT {(page - 1) * pagelimit}, {pagelimit}")
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
        ret.append({"timestamp": str(tt[2]), "user": name, "operation": tt[1]})

    cur.execute(f"SELECT COUNT(*) FROM auditlog")
    t = cur.fetchall()
    tot = t[0][0]

    return {"error": False, "response": {"list": ret, "page": str(page), "tot": str(tot)}}