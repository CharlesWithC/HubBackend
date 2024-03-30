# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import traceback
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *
from functions.discord import DiscordAuth


async def post_resend_confirmation(request: Request, response: Response, authorization: str = Header(None)):
    """Resends confirmation email"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /user/resend-confirmation', 60, 1)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    await app.db.execute(dhrid, f"SELECT operation, expire FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'register/%'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "no_pending_email_confirmation", force_lang = au["language"])}
    email = convertQuotation("/".join(t[0][0].split("/")[1:]))
    expire = t[0][1]

    if not emailConfigured(app):
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    secret = "rg" + gensecret(length = 30)
    await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'register/%'")
    await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'update-email/%'")
    await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await app.db.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'register/{email}', {expire})")
    await app.db.commit(dhrid)

    link = app.config.frontend_urls.email_confirm.replace("{secret}", secret)
    await app.db.extend_conn(dhrid, 15)
    ok = (await sendEmail(app, au["name"], email, "register", link))
    await app.db.extend_conn(dhrid, 2)
    if not ok:
        await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
        await app.db.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    return Response(status_code=204)

async def patch_email(request: Request, response: Response, authorization: str = Header(None)):
    """Updates email for the authorized user, returns 204

    JSON: `{"email": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/email', 60, 1)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
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

    await app.db.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND email = '{new_email}'")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Email"}, force_lang = au["language"])}

    if not emailConfigured(app):
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    secret = "ue" + gensecret(length = 30)
    await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND operation LIKE 'update-email/%'")
    await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE expire < {int(time.time())}")
    await app.db.execute(dhrid, f"INSERT INTO email_confirmation VALUES ({uid}, '{secret}', 'update-email/{new_email}', {int(time.time() + 3600)})")
    await app.db.commit(dhrid)

    link = app.config.frontend_urls.email_confirm.replace("{secret}", secret)
    await app.db.extend_conn(dhrid, 15)
    ok = (await sendEmail(app, au["name"], new_email, "update_email", link))
    await app.db.extend_conn(dhrid, 2)
    if not ok:
        await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid} AND secret = '{secret}'")
        await app.db.commit(dhrid)
        response.status_code = 428
        return {"error": ml.tr(request, "smtp_configuration_invalid", force_lang = au["language"])}

    return Response(status_code=204)

async def patch_discord(request: Request, response: Response, authorization: str = Header(None), code: Optional[str] = None, error_description: Optional[str] = None, callback_url: Optional[str] = None):
    """Updates Discord account connection for the authorized user, returns 204

    JSON: `{"code": str}`"""
    app = request.app
    if code is None and error_description is None or callback_url is None:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_params")}

    if code is None and error_description is not None:
        response.status_code = 400
        return {"error": error_description}

    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/discord', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    try:
        discord_auth = DiscordAuth(app.config.discord_client_id, app.config.discord_client_secret, callback_url)
        tokens = await discord_auth.get_tokens(code)
        if "access_token" in tokens.keys():
            await app.db.extend_conn(dhrid, 30)
            user_data = await discord_auth.get_user_data_from_token(tokens["access_token"])
            await app.db.extend_conn(dhrid, 2)
            if 'id' not in user_data:
                response.status_code = 400
                return {"error": user_data['message']}
            discordid = user_data['id']
            email = "NULL"
            if "email" in user_data.keys() and user_data["email"] is not None and "@" in str(user_data["email"]):
                email = "'" + convertQuotation(user_data['email']) + "'"
            tokens = {**tokens, **user_data}

            (access_token, refresh_token, expire_timestamp) = (convertQuotation(tokens["access_token"]), convertQuotation(tokens["refresh_token"]), tokens["expires_in"] + int(time.time()) - 60)
            await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE discordid = {discordid}")
            await app.db.execute(dhrid, f"INSERT INTO discord_access_token VALUES ({discordid}, '{convertQuotation(callback_url)}', '{access_token}', '{refresh_token}', {expire_timestamp})")

            await app.db.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND discordid = {discordid}")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                response.status_code = 409
                return {"error": ml.tr(request, "connection_conflict", var = {"app": "Discord"}, force_lang = au["language"])}

            await app.db.execute(dhrid, f"UPDATE user SET discordid = {discordid} WHERE uid = {uid}")
            await app.db.commit(dhrid)

            app.redis.delete(f"umap:discordid={au['discordid']}")
            app.redis.hset(f"uinfo:{uid}", mapping = {"discordid": discordid})
            app.redis.set(f"umap:discordid={discordid}", uid)
            app.redis.expire(f"umap:discordid={discordid}", 60)

            await app.db.execute(dhrid, f"SELECT email FROM user WHERE uid = {uid}")
            t = await app.db.fetchall(dhrid)
            if t[0][0] is None or "@" not in t[0][0] or app.config.sync_discord_email:
                await app.db.execute(dhrid, f"UPDATE user SET email = {email} WHERE uid = {uid}")
                await app.db.commit(dhrid)
                app.redis.hset(f"uinfo:{uid}", mapping = {"email": email if "@" in email else ""}) # use "" when email is invalid
            # when user already has an email, and the config is set to not sync the latest discord email, then use user's old email for further operations
            if t[0][0] is not None and "@" in t[0][0] and not app.config.sync_discord_email:
                email = "'" + convertQuotation(t[0][0]) + "'"

            await DeleteRoleConnection(request, au["discordid"])
            await UpdateRoleConnection(request, discordid)

            await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE discordid = {discordid}")
            t = await app.db.fetchall(dhrid)
            if len(t) > 0:
                await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
                await app.db.commit(dhrid)
                reason = t[0][0]
                expire = t[0][1]
                if expire != 253402272000:
                    expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
                else:
                    expire = ml.tr(request, "forever")
                response.status_code = 423
                if reason != "":
                    return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
                else:
                    return {"error": ml.tr(request, "ban_with_expire", var = {"expire": expire})}

            return Response(status_code=204)

        elif 'error_description' in tokens.keys():
            response.status_code = 400
            return {"error": tokens['error_description']}
        elif 'error' in tokens.keys():
            response.status_code = 400
            return {"error": tokens['error']}
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "unknown_error", force_lang = au["language"])}

    except Exception as exc:
        await tracebackHandler(request, exc, traceback.format_exc())
        response.status_code = 400
        return {"error": ml.tr(request, "unknown_error", force_lang = au["language"])}

async def patch_steam(request: Request, response: Response, authorization: str = Header(None)):
    """Updates Steam account connection for the authorized user, returns 204

    JSON: `{"callback": str}`"""
    app = request.app
    data = str(request.query_params).replace("openid.mode=id_res", "openid.mode=check_authentication")
    if data == "":
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_params")}

    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/steam', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    r = None
    try:
        r = await arequests.get(app, "https://steamcommunity.com/openid/login?" + data, dhrid = dhrid)
    except:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"}, force_lang = au["language"])}
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': "Steam"}, force_lang = au["language"])}
    if r.text.find("is_valid:true") == -1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_steam_auth", force_lang = au["language"])}
    steamid = data.split("openid.identity=")[1].split("&")[0]
    steamid = int(steamid[steamid.rfind("%2F") + 3 :])

    await app.db.execute(dhrid, f"SELECT * FROM user WHERE uid != '{uid}' AND steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_conflict", var = {"app": "Steam"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT roles, steamid, userid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    orgsteamid = t[0][1]
    userid = t[0][2]
    if orgsteamid is not None and userid >= 0:
        if not (await auth(authorization, request, required_permission = ["driver"]))["error"]:
            try:
                await remove_driver(request, steamid, au["uid"], au["userid"], au["name"])
                await add_driver(request, steamid, au["uid"], au["userid"], au["name"])
            except:
                pass

    await app.db.execute(dhrid, f"UPDATE user SET steamid = {steamid} WHERE uid = {uid}")
    await app.db.commit(dhrid)
    app.redis.hset(f"uinfo:{uid}", mapping = {"steamid": steamid})

    await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE steamid = {steamid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.commit(dhrid)
        reason = t[0][0]
        expire = t[0][1]
        if expire != 253402272000:
            expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        else:
            expire = ml.tr(request, "forever")
        response.status_code = 423
        if reason != "":
            return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
        else:
            return {"error": ml.tr(request, "ban_with_expire", var = {"expire": expire})}

    try:
        r = await arequests.get(app, f"https://api.truckersmp.com/v2/player/{steamid}", dhrid = dhrid)
        if r.status_code == 200:
            d = json.loads(r.text)
            if not d["error"]:
                truckersmpid = d["response"]["id"]
                await app.db.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = {uid}")
                await app.db.commit(dhrid)
                app.redis.hset(f"uinfo:{uid}", mapping = {"truckersmpid": truckersmpid})

                await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE truckersmpid = {truckersmpid}")
                t = await app.db.fetchall(dhrid)
                if len(t) > 0:
                    await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
                    await app.db.commit(dhrid)
                    reason = t[0][0]
                    expire = t[0][1]
                    if expire != 253402272000:
                        expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
                    else:
                        expire = ml.tr(request, "forever")
                    response.status_code = 423
                    if reason != "":
                        return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
                    else:
                        return {"error": ml.tr(request, "ban_with_expire", var = {"expire": expire})}

                return Response(status_code=204)
    except:
        pass

    # in case user changed steam
    await app.db.execute(dhrid, f"UPDATE user SET truckersmpid = NULL WHERE uid = {uid}")
    await app.db.commit(dhrid)
    app.redis.hset(f"uinfo:{uid}", mapping = {"truckersmpid": ""})

    return Response(status_code=204)

async def patch_truckersmp(request: Request, response: Response, authorization: str = Header(None)):
    """Updates TruckersMP account connection for the authorized user, returns 204

    JSON: `{"truckersmpid": int}`"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /user/truckersmp', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, check_member = False)
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

    r = await arequests.get(app, "https://api.truckersmp.com/v2/player/" + str(truckersmpid), dhrid = dhrid)
    if r.status_code // 100 != 2:
        response.status_code = 503
        return {"error": ml.tr(request, 'service_api_error', var = {'service': "TruckersMP"}, force_lang = au["language"])}
    d = json.loads(r.text)
    if d["error"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_truckersmp_id", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT steamid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "must_connect_steam_before_truckersmp", force_lang = au["language"])}
    steamid = t[0][0]

    tmpsteamid = d["response"]["steamID64"]
    truckersmp_name = d["response"]["name"]
    if tmpsteamid != steamid:
        response.status_code = 400
        return {"error": ml.tr(request, "truckersmp_steam_mismatch", var = {"truckersmp_name": truckersmp_name, "truckersmpid": str(truckersmpid)}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET truckersmpid = {truckersmpid} WHERE uid = {uid}")
    await app.db.commit(dhrid)
    app.redis.hset(f"uinfo:{uid}", mapping = {"truckersmpid": truckersmpid})

    await app.db.execute(dhrid, f"SELECT reason, expire_timestamp FROM banned WHERE truckersmpid = {truckersmpid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.commit(dhrid)
        reason = t[0][0]
        expire = t[0][1]
        if expire != 253402272000:
            expire = ml.tr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        else:
            expire = ml.tr(request, "forever")
        response.status_code = 423
        if reason != "":
            return {"error": ml.tr(request, "ban_with_reason_expire", var = {"reason": reason, "expire": expire})}
        else:
            return {"error": ml.tr(request, "ban_with_expire", var = {"expire": expire})}

    return Response(status_code=204)
