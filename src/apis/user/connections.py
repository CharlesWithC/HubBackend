# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import traceback

from discord_oauth2 import DiscordAuth
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *

@app.post(f"/user/resendConfirmation")
async def post_user_resend_confirmation(request: Request, response: Response, authorization: str = Header(None)):
    """Resends confirmation email"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /user/resendConfirmation', 60, 1)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    await aiosql.execute(dhrid, f"SELECT operation, expire FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'register/%'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": "Not Found"}
    email = convertQuotation("/".join(t[0][0].split("/")[1:]))
    expire = t[0][1]

    if not emailConfigured():
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    secret = "rg" + gensecret(length = 30)
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'register/%'")
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'update-email/%'")
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'register/{email}', {expire})")
    await aiosql.commit(dhrid)
    
    link = config.frontend_urls.email_confirm.replace("{secret}", secret)
    await aiosql.extend_conn(dhrid, 15)
    ok = (await sendEmail(au["name"], email, "register", link))
    await aiosql.extend_conn(dhrid, 2)
    if not ok:
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
        await aiosql.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    return Response(status_code=204)

@app.patch(f"/user/email")
async def patch_user_email(request: Request, response: Response, authorization: str = Header(None)):
    """Updates email for the authorized user, returns 204
    
    JSON: `{"email": str}`"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/email', 60, 1)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        new_email = convertQuotation(data["email"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND email = '{new_email}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Email"}, force_lang = au["language"])}

    if not emailConfigured():
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    secret = "ue" + gensecret(length = 30)
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'update-email/%'")
    await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await aiosql.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'update-email/{new_email}', {int(time.time() + 3600)})")
    await aiosql.commit(dhrid)
    
    link = config.frontend_urls.email_confirm.replace("{secret}", secret)
    await aiosql.extend_conn(dhrid, 15)
    ok = (await sendEmail(au["name"], new_email, "update_email", link))
    await aiosql.extend_conn(dhrid, 2)
    if not ok:
        await aiosql.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
        await aiosql.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    return Response(status_code=204)

@app.patch(f"/user/discord")
async def patch_user_discord(request: Request, response: Response, authorization: str = Header(None)):
    """Updates Discord account connection for the authorized user, returns 204
    
    JSON: `{"code": str}`"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/discord', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    data = await request.json()
    try:
        code = str(data["code"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    try:
        discord_auth = DiscordAuth(config.discord_client_id, config.discord_client_secret, f"https://{config.apidomain}/{config.abbr}/auth/discord/connect")
        tokens = discord_auth.get_tokens(code)
        if "access_token" in tokens.keys():
            user_data = discord_auth.get_user_data_from_token(tokens["access_token"])
            if not 'id' in user_data:
                response.status_code = 400
                return {"error": "Discord Error: " + user_data['message']}
            discordid = user_data['id']
            tokens = {**tokens, **user_data}

            await aiosql.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND discordid = {discordid}")
            t = await aiosql.fetchall(dhrid)
            if len(t) > 0:
                response.status_code = 409
                return {"error": ml.tr(request, "connection_conflict", var = {"app": "Discord"}, force_lang = au["language"])}

            await aiosql.execute(dhrid, f"UPDATE user SET discordid = {discordid} WHERE uid = {uid}")
            await aiosql.commit(dhrid)

            return Response(status_code=204)
        
        if 'error_description' in tokens.keys():
            response.status_code = 400
            return {"error": tokens['error_description']}
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "unknown_error", force_lang = au["language"])}

    except:
        traceback.print_exc()
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_error", force_lang = au["language"])}
    
@app.patch(f"/user/steam")
async def patch_user_steam(request: Request, response: Response, authorization: str = Header(None)):
    """Updates Steam account connection for the authorized user, returns 204
    
    JSON: `{"callback": str}`"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/steam', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    data = await request.json()
    try:
        openid = str(data["callback"]).replace("openid.mode=id_res", "openid.mode=check_authentication")
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    r = None
    try:
        r = await arequests.get("https://steamcommunity.com/openid/login?" + openid, dhrid = dhrid)
    except:
        traceback.print_exc()
        response.status_code = 503
        return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, "steam_api_error", force_lang = au["language"])}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_steam_auth", force_lang = au["language"])}
    steamid = openid.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    await aiosql.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND steamid = {steamid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Steam"}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT roles, steamid, userid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid is not None and userid >= 0:
        if not (await auth(dhrid, authorization, request, required_permission = ["driver"]))["error"]:
            try:
                if config.tracker.lower() == "tracksim":
                    await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(orgsteamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
                    await arequests.post("https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
            except:
                traceback.print_exc()

    await aiosql.execute(dhrid, f"UPDATE user SET steamid = {steamid} WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    try:
        r = await arequests.get(f"https://api.truckersmp.com/v2/player/{steamid}", dhrid = dhrid)
        if r.status_code == 200:
            d = json.loads(r.text)
            if not d["error"]:
                truckersmpid = d["response"]["id"]
                await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = {uid}")
                await aiosql.commit(dhrid)
                return Response(status_code=204)
    except:
        traceback.print_exc()

    # in case user changed steam
    await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = NULL WHERE uid = {uid}")
    await aiosql.commit(dhrid)
    
    return Response(status_code=204)

@app.patch(f"/user/truckersmp")
async def patch_user_truckersmp(request: Request, response: Response, authorization: str = Header(None)):
    """Updates TruckersMP account connection for the authorized user, returns 204
    
    JSON: `{"truckersmpid": int}`"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/truckersmp', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    
    data = await request.json()
    try:
        truckersmpid = data["truckersmpid"]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    try:
        truckersmpid = int(truckersmpid)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    r = await arequests.get("https://api.truckersmp.com/v2/player/" + str(truckersmpid), dhrid = dhrid)
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, "truckersmp_api_error", force_lang = au["language"])}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT steamid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "must_connect_steam_before_truckersmp", force_lang = au["language"])}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    truckersmp_name = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": ml.tr(request, "truckersmp_steam_mismatch", var = {"truckersmp_name": truckersmp_name, "truckersmpid": str(truckersmpid)}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = {uid}")
    await aiosql.commit(dhrid)
    return Response(status_code=204)