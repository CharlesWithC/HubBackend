# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This plugin enables official web client to use dynamic configuration.

import uuid

import pymysql
import redis
from fastapi import Header, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from functions import *


async def get_client_global_config(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid

    config = app.redis.get("client-config:meta")
    if config is not None:
        return json.loads(config)

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'client-config/meta'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 500
        return {"error": "Unable to fetch config."}

    app.redis.set("client-config:meta", t[0][0])
    app.redis.expire("client-config:meta", 86400)

    config = json.loads(t[0][0])
    return config

async def get_client_assets(request: Request, response: Response, key: str):
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'GET /client/assets', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if key not in ["logo", "banner", "bgimage"]:
        response.status_code = 404
        return {"error": "Not Found"}

    # disable decode response
    r = redis.Redis(app.config.redis_host, app.config.redis_port, app.config.redis_db, app.config.redis_password)
    raw = r.get(f"{app.config.abbr}:client-config:{key}")
    if not raw:
        await app.db.new_conn(dhrid, db_name = app.config.db_name)

        await app.db.execute(dhrid, f"SELECT aval FROM ext_assets WHERE akey = 'client-config/{key}'")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0 or t[0][0] == "":
            response.status_code = 404
            return {"error": "Not Found"}
        raw = b64decode(decompress(t[0][0]))
        r.set(f"{app.config.abbr}:client-config:{key}", raw)
        r.expire(f"{app.config.abbr}:client-config:{key}", 86400)

    return Response(content=raw, media_type="image/png")

async def patch_client_global_config(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'PATCH /client/config/global', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["administrator"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'client-config/meta'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 500
        return {"error": "Unable to fetch config."}

    config = json.loads(t[0][0])

    data = await request.json()

    for key in ["logo", "banner", "bgimage"]:
        if key not in data["assets"] or data["assets"][key] == "":
            continue

        val = data["assets"][key]
        raw = b64decode(val.encode())
        if len(raw) > 1024 * 2048:
            response.status_code = 400
            return {"error": "Asset file must not be larger than 2MB."}

        await app.db.execute(dhrid, f"UPDATE ext_assets SET aval = '{compress(val)}' WHERE akey = 'client-config/{key}'")
        await app.db.commit(dhrid)

        app.redis.set(f"client-config:{key}", raw)
        app.redis.expire(f"client-config:{key}", 86400)

        config[key + "_key"] = str(uuid.uuid4())[:8]

    try:
        newconfig = data["config"]
        whitelist = ["abbr", "name", "plan", "color", "name_color", "theme_main_color", "theme_background_color", "theme_darken_ratio", "distance_unit", "use_highest_role_color", "domain", "api_host", "plugins", "logo_key", "banner_key", "bgimage_key", "truckersmp_vtc_id", "gallery"]
        blacklist = ["abbr", "domain", "plan", "api_host", "plugins", "logo_key", "banner_key", "bgimage_key", "gallery"]

        keys = list(newconfig.keys())
        for k in keys:
            if k not in whitelist or k in blacklist:
                del newconfig[k]

        keys = list(config.keys())
        for k in keys:
            if k not in newconfig.keys():
                newconfig[k] = config[k]

        sorted_keys = sorted(newconfig.keys(), key=lambda x: whitelist.index(x))
        newconfig = {key: newconfig[key] for key in sorted_keys}
        newconfig = json.dumps(newconfig)
    except:
        response.status_code = 400
        return {"error": "Unable to parse config."}

    await app.db.execute(dhrid, f"UPDATE settings SET sval = '{convertQuotation(newconfig)}' WHERE skey = 'client-config/meta'")
    await app.db.commit(dhrid)

    app.redis.set("client-config:meta", newconfig)
    app.redis.expire("client-config:meta", 86400)

    return Response(status_code=204)

async def patch_client_global_config_gallery(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'PATCH /client/config/global/gallery', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["manage_gallery"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'client-config/meta'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 500
        return {"error": "Unable to fetch config."}

    config = json.loads(t[0][0])

    data = await request.json()

    try:
        gallery = data["gallery"]
        if len(json.dumps(gallery, indent=4)) >= 100000:
            response.status_code = 400
            return {"error": "Too many URLs or URLs too long"}
        config["gallery"] = gallery
        config = json.dumps(config)

        await app.db.execute(dhrid, f"UPDATE settings SET sval = '{convertQuotation(config)}' WHERE skey = 'client-config/meta'")
        await app.db.commit(dhrid)

        app.redis.set("client-config:meta", config)
        app.redis.expire("client-config:meta", 86400)
    except:
        response.status_code = 400
        return {"error": "Error occurred when saving config"}

    return Response(status_code=204)

async def get_client_user_config(request: Request):
    '''Returns user config for the whole Drivers Hub (not a single user)'''
    app = request.app
    dhrid = request.state.dhrid

    config = app.redis.get("client-config:user")
    if config is not None:
        return json.loads(config)

    ret = {}

    await app.db.new_conn(dhrid, db_name = app.config.db_name)
    await app.db.execute(dhrid, "SELECT uid, sval FROM settings WHERE skey = 'client-config/user'")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        ret[tt[0]] = json.loads(tt[1])

    app.redis.set("client-config:user", json.dumps(ret))
    app.redis.expire("client-config:user", 86400)

    return ret

async def patch_client_user_config(request: Request, response: Response, authorization: str = Header(None)):
    '''Updates the config for an individual user'''
    app = request.app
    dhrid = request.state.dhrid

    rl = await ratelimit(request, 'PATCH /client/config/user', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()

    whitelist = ["name_color", "profile_upper_color", "profile_lower_color", "profile_banner_url"]
    keys = data.keys()
    for k in keys:
        if k not in whitelist:
            del data[k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)
    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'client-config/user' AND uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ({uid}, 'client-config/user', '{convertQuotation(json.dumps(data))}')")
    else:
        await app.db.execute(dhrid, f"UPDATE settings SET sval = '{convertQuotation(json.dumps(data))}' WHERE skey = 'client-config/user' AND uid = {uid}")
    await app.db.commit(dhrid)

    full_config = app.redis.get("client-config:user")
    if full_config is not None:
        full_config = json.loads(full_config)
        full_config[uid] = data
    else:
        full_config = {uid: data}
    app.redis.set("client-config:user", json.dumps(full_config))
    app.redis.expire("client-config:user", 86400)

    return Response(status_code=204)

def init(config: dict, print_log: bool = False):
    # Define routes
    routes = [
        APIRoute("/client/config/global", get_client_global_config, methods=["GET"], response_class=JSONResponse),
        APIRoute("/client/assets/{key}", get_client_assets, methods=["GET"], response_class=JSONResponse),
        APIRoute("/client/config/global", patch_client_global_config, methods=["PATCH"], response_class=JSONResponse),
        APIRoute("/client/config/global/gallery", patch_client_global_config_gallery, methods=["PATCH"], response_class=JSONResponse),
        APIRoute("/client/config/user", get_client_user_config, methods=["GET"], response_class=JSONResponse),
        APIRoute("/client/config/user", patch_client_user_config, methods=["PATCH"], response_class=JSONResponse)
    ]

    # Define additional state
    states = {}

    # Initial setup
    conn = pymysql.connect(host = config["db_host"], user = config["db_user"], passwd = config["db_password"], db = config["db_name"])
    cur = conn.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS ext_assets (akey TEXT, aval MEDIUMTEXT)")
    conn.commit()
    cur.close()
    conn.close()

    # NOTE: Database entries should be created manually. The examples are not provided.

    return (True, routes, states, {})

