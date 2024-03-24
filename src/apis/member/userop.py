# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import traceback
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *

ALGO_OFFSET = 15
# NOTE This offset controls the initial increase rate of the algo


async def patch_roles_rank_default(request: Request, response: Response, authorization: str = Header(None)):
    """Updates rank role of the authorized user in Discord, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /member/roles/rank', 60, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    username = au["name"]
    avatar = au["avatar"]

    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_not_found", var = {"app": "Discord"}, force_lang = au["language"])}

    totalpnt = await GetPoints(request, userid, app.default_rank_type_point_types)
    rankroleid = point2rank(app, "default", totalpnt)
    if rankroleid is None or rankroleid["discord_role_id"] in [None, 0, 1, -1]:
        response.status_code = 409
        return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
    rankroleid = rankroleid["discord_role_id"]

    await UpdateRoleConnection(request, discordid)

    try:
        if app.config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers = headers, dhrid = dhrid)
        except:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        if r.status_code == 401:
            DisableDiscordIntegration(app)
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        elif r.status_code // 100 != 2:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        d = json.loads(r.text)
        if "roles" in d:
            discord_roles = d["roles"]
            current_discord_roles = []
            for role in discord_roles:
                for rank_type in app.config.rank_types:
                    if not rank_type["default"]:
                        continue
                    for rank in rank_type["details"]:
                        if str(role) == str(rank["discord_role_id"]):
                            current_discord_roles.append(role)
            if rankroleid in current_discord_roles:
                response.status_code = 409
                return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
            else:
                try:
                    opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{rankroleid}', None, headers, f"add_role,{rankroleid},{discordid}")
                    for role in current_discord_roles:
                        opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{role}', None, headers, f"remove_role,{role},{discordid}")
                except:
                    pass

                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rankroleid}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar))

                for meta in app.config.rank_up:
                    meta = Dict2Obj(meta)
                    if meta.webhook_url != "" or meta.channel_id != "":
                        await AutoMessage(app, meta, setvar)

                rankname = point2rank(app, "default", totalpnt)["name"]
                await notification(request, "member", uid, ml.tr(request, "new_rank", var = {"rankname": rankname}, force_lang = await GetUserLanguage(request, uid)), discord_embed = {"title": ml.tr(request, "new_rank_title", force_lang = await GetUserLanguage(request, uid)), "description": f"**{rankname}**", "fields": []})
                return Response(status_code=204)
        else:
            response.status_code = 428
            return {"error": ml.tr(request, "current_user_didnt_join_discord", force_lang = au["language"])}

    except Exception as exc:
        return await tracebackHandler(request, exc, traceback.format_exc())

async def patch_roles_rank(request: Request, response: Response, rank_type_id: int, authorization: str = Header(None)):
    """Updates rank role of the authorized user in Discord, returns 204"""
    app = request.app
    if rank_type_id not in app.ranktypes.keys():
        response.status_code = 404
        return {"error": "Not Found"}
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /member/roles/rank', 60, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    username = au["name"]
    avatar = au["avatar"]

    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_not_found", var = {"app": "Discord"}, force_lang = au["language"])}

    totalpnt = await GetPoints(request, userid, app.rank_type_point_types[rank_type_id])
    rankroleid = point2rank(app, rank_type_id, totalpnt)
    if rankroleid is None or rankroleid["discord_role_id"] in [None, 0, 1, -1]:
        response.status_code = 409
        return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
    rankroleid = rankroleid["discord_role_id"]

    await UpdateRoleConnection(request, discordid)

    try:
        if app.config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers = headers, dhrid = dhrid)
        except:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        if r.status_code == 401:
            DisableDiscordIntegration(app)
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        elif r.status_code // 100 != 2:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        d = json.loads(r.text)
        if "roles" in d:
            discord_roles = d["roles"]
            current_discord_roles = []
            for role in discord_roles:
                for rank_type in app.config.rank_types:
                    if rank_type["id"] != rank_type_id:
                        continue
                    for rank in rank_type["details"]:
                        if str(role) == str(rank["discord_role_id"]):
                            current_discord_roles.append(role)
            if rankroleid in current_discord_roles:
                response.status_code = 409
                return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
            else:
                try:
                    opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{rankroleid}', None, headers, f"add_role,{rankroleid},{discordid}")
                    for role in current_discord_roles:
                        opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{role}', None, headers, f"remove_role,{role},{discordid}")
                except:
                    pass

                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rankroleid}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar))

                for meta in app.config.rank_up:
                    meta = Dict2Obj(meta)
                    if meta.webhook_url != "" or meta.channel_id != "":
                        await AutoMessage(app, meta, setvar)

                rankname = point2rank(app, rank_type_id, totalpnt)["name"]
                await notification(request, "member", uid, ml.tr(request, "new_rank", var = {"rankname": rankname}, force_lang = await GetUserLanguage(request, uid)), discord_embed = {"title": ml.tr(request, "new_rank_title", force_lang = await GetUserLanguage(request, uid)), "description": f"**{rankname}**", "fields": []})
                return Response(status_code=204)
        else:
            response.status_code = 428
            return {"error": ml.tr(request, "current_user_didnt_join_discord", force_lang = au["language"])}

    except Exception as exc:
        return await tracebackHandler(request, exc, traceback.format_exc())

async def get_bonus_history(request: Request, response: Response, authorization: str = Header(None), month: Optional[str] = None):
    """Returns bonus history

    `month` must be a 6-digit code, like `202305` refers to May 2023"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /member/bonus/history', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token=True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    userid = au["userid"]
    usertz = await GetUserTimezone(request, au["uid"])
    utcnow = pytz.utc.localize(datetime.utcnow())
    user_dt = utcnow.astimezone(pytz.timezone(usertz)) # to get user's today, may be different from system

    # all use utc time as we store utc timestamp in database
    start_dt = datetime(user_dt.year, user_dt.month, 1, 0, 0, 0, tzinfo = pytz.timezone("UTC"))
    if month is not None:
        try:
            start_dt = datetime(int(month[0:4]), int(month[4:6]), 1, 0, 0, 0, tzinfo = pytz.timezone("UTC"))
        except:
            response.status_Code = 422
            return {"error": "Unprocessable Entity"}

    start_ts = int(start_dt.timestamp())

    if start_dt.month == 12:
        end_dt = datetime(start_dt.year + 1, 1, 1, 0, 0, 0, tzinfo = pytz.timezone("UTC"))
    else:
        end_dt = datetime(start_dt.year, start_dt.month + 1, 1, 0, 0, 0, tzinfo = pytz.timezone("UTC"))
    end_ts = int(end_dt.timestamp())

    await app.db.execute(dhrid, f"SELECT point, streak, timestamp FROM daily_bonus_history WHERE userid = {userid} AND timestamp >= {start_ts} AND timestamp <= {end_ts}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"points": tt[0], "streak": tt[1], "timestamp": tt[2]})

    return ret

async def post_bonus_claim(request: Request, response: Response, authorization: str = Header(None)):
    """Claims "daily_bonus", returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /member/bonus/claim', 60, 5)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    uid = au["uid"]

    usertz = await GetUserTimezone(request, uid)

    streak = 0
    lcts = 0
    await app.db.execute(dhrid, f"SELECT streak, timestamp FROM daily_bonus_history WHERE userid = {userid} ORDER BY timestamp DESC LIMIT 1")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        streak = int(t[0][0])
        lcts = int(t[0][1])

    utcnow = pytz.utc.localize(datetime.utcnow())
    user_date = utcnow.astimezone(pytz.timezone(usertz)).date()

    lcutc = pytz.utc.localize(datetime.utcfromtimestamp(lcts))
    lc_date = lcutc.astimezone(pytz.timezone(usertz)).date()

    timediff = user_date - lc_date

    if timediff == timedelta(days=0):
        response.status_code = 409
        return {"error": ml.tr(request, "already_claimed_todays_bonus", force_lang = au["language"])}

    if timediff == timedelta(days=1):
        streak += 1
    else:
        streak = 0

    totalpnt = await GetPoints(request, userid, app.default_rank_type_point_types)
    bonus = point2rank(app, "default", totalpnt)
    if bonus is None or bonus["daily_bonus"] is None:
        response.status_code = 404
        return {"error": ml.tr(request, "daily_bonus_not_available", force_lang = au["language"])}
    bonus = bonus["daily_bonus"]
    bonuspnt = bonus["base"]

    if bonus["type"] == "streak":
        if bonus["streak_type"] == "fixed":
            bonuspnt += bonus["streak_value"] * streak
        elif bonus["streak_type"] == "algo":
            offset = ALGO_OFFSET
            if "algo_offset" in bonus.keys():
                offset = bonus["algo_offset"]
            bonuspnt = bonuspnt * (1 + math.log(streak + offset, math.e ** (1 / bonus["streak_value"]))) - bonuspnt * math.log(offset, math.e ** (1 / bonus["streak_value"]))
    bonuspnt = round(bonuspnt)
    if abs(bonuspnt) > 2147483647:
        response.status_code = 400
        return {"error": ml.tr(request, "value_too_large", var = {"item": "bonus", "limit": "2,147,483,647"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO bonus_point VALUES ({userid}, {bonuspnt}, {int(time.time())})")
    await app.db.execute(dhrid, f"INSERT INTO daily_bonus_history VALUES ({userid}, {bonuspnt}, {streak}, {int(time.time())})")
    await app.db.commit(dhrid)

    if streak == 0 or bonus["type"] == "fixed":
        await notification(request, "bonus", uid, ml.tr(request, "claimed_daily_bonus", var = {"points": bonuspnt}, force_lang = await GetUserLanguage(request, uid)))
    elif streak == 1 and bonus["type"] == "streak":
        await notification(request, "bonus", uid, ml.tr(request, "claimed_daily_bonus_with_streak", var = {"points": bonuspnt, "streak": streak}, force_lang = await GetUserLanguage(request, uid)))
    elif streak > 1 and bonus["type"] == "streak":
        await notification(request, "bonus", uid, ml.tr(request, "claimed_daily_bonus_with_streak_s", var = {"points": bonuspnt, "streak": streak}, force_lang = await GetUserLanguage(request, uid)))

    return {"bonus": bonuspnt}

async def delete_role_history(request: Request, response: Response, historyid: int, authorization: str = Header(None)):
    """Deletes a specific row of user role history with historyid, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /member/roles/history', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]

    await app.db.execute(dhrid, f"SELECT uid FROM user_role_history WHERE historyid = {historyid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "role_history_not_found", force_lang = au["language"])}
    if t[0][0] != uid and not checkPerm(app, au["roles"], ["administrator", "update_roles"]):
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM user_role_history WHERE historyid = {historyid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_resign(request: Request, response: Response, authorization: str = Header(None)):
    """Resigns the authorized user, set userid to -1, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /member/resign', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    userid = au["userid"]
    discordid = au["discordid"]
    name = convertQuotation(au["name"])

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT mfa_secret, steamid, avatar FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    steamid = t[0][1]
    avatar = t[0][2]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = data["otp"]
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_otp", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    await app.db.execute(dhrid, f"DELETE FROM economy_balance WHERE userid = {userid}")
    await app.db.execute(dhrid, f"DELETE FROM economy_truck WHERE userid = {userid}")
    await app.db.execute(dhrid, f"UPDATE economy_garage SET userid = -1000 WHERE userid = {userid}")
    await app.db.commit(dhrid)

    app.redis.delete(f"umap:userid={userid}")

    await remove_driver(request, steamid, uid, userid, name)

    await UpdateRoleConnection(request, discordid)

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar))

    for meta in app.config.member_leave:
        meta = Dict2Obj(meta)
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

        if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
            for role in meta.role_change:
                try:
                    if int(role) < 0:
                        opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}, f"remove_role,{-int(role)},{discordid}")
                    elif int(role) > 0:
                        opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}, f"add_role,{int(role)},{discordid}")
                except:
                    pass

    if discordid is not None and app.config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when member resigns."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers = headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                discord_roles = d["roles"]
                current_discord_roles = []
                for role in discord_roles:
                    for rank_type in app.config.rank_types:
                        for rank in rank_type["details"]:
                            if str(role) == str(rank["discord_role_id"]):
                                current_discord_roles.append(role)
                for role in current_discord_roles:
                    opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{role}', None, headers, f"remove_role,{role},{discordid}")
        except:
            pass

    await AuditLog(request, uid, ml.ctr(request, "member_resigned_audit"))
    await notification(request, "member", uid, ml.tr(request, "member_resigned", force_lang = await GetUserLanguage(request, uid)))

    return Response(status_code=204)
