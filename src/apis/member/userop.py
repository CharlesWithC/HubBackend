# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import traceback

from fastapi import Header, Request, Response

from datetime import datetime
import multilang as ml
from functions import *
from api import tracebackHandler


async def patch_roles_rank(request: Request, response: Response, authorization: str = Header(None)):
    """Updates rank role of the authorized user in Discord, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /member/roles/rank', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    discordid = au["discordid"]
    userid = au["userid"]
    username = au["name"]
    
    if discordid is None:
        response.status_code = 409
        return {"error": ml.tr(request, "connection_not_found", var = {"app": "Discord"}, force_lang = au["language"])}
    
    ratio = 1
    if app.config.distance_unit == "imperial":
        ratio = 0.621371

    # calculate distance
    userdistance = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(distance) FROM dlog WHERE userid = {userid} GROUP BY userid")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        if not tt[0] in userdistance.keys():
            userdistance[tt[0]] = nint(tt[1])
        else:
            userdistance[tt[0]] += nint(tt[1])
        userdistance[tt[0]] = int(userdistance[tt[0]])

    # calculate challenge
    userchallenge = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid = {userid} GROUP BY userid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userchallenge.keys():
            userchallenge[oo[0]] = 0
        userchallenge[oo[0]] += oo[1]

    # calculate event
    userevent = {}
    await app.db.execute(dhrid, f"SELECT attendee, points FROM event WHERE attendee LIKE '%,{userid},%'")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        attendees = str2list(tt[0])
        for attendee in attendees:
            if not attendee in userevent.keys():
                userevent[attendee] = tt[1]
            else:
                userevent[attendee] += tt[1]
    
    # calculate division
    userdivision = {}
    await app.db.execute(dhrid, f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 AND userid = {userid} GROUP BY divisionid, userid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in app.division_points.keys():
            userdivision[oo[0]] += oo[2] * app.division_points[oo[1]]
    
    # calculate myth
    usermyth = {}
    await app.db.execute(dhrid, f"SELECT userid, SUM(point) FROM mythpoint WHERE userid = {userid} GROUP BY userid")
    o = await app.db.fetchall(dhrid)
    for oo in o:
        if not oo[0] in usermyth.keys():
            usermyth[oo[0]] = 0
        usermyth[oo[0]] += oo[1]
    
    distance = 0
    challengepnt = 0
    eventpnt = 0
    divisionpnt = 0
    mythpnt = 0
    if userid in userdistance.keys():
        distance = userdistance[userid]
    if userid in userchallenge.keys():
        challengepnt = userchallenge[userid]
    if userid in userevent.keys():
        eventpnt = userevent[userid]
    if userid in userdivision.keys():
        divisionpnt = userdivision[userid]
    if userid in usermyth.keys():
        mythpnt = usermyth[userid]

    totalpnt = distance * ratio + challengepnt + eventpnt + divisionpnt + mythpnt
    rankroleid = point2rankroleid(app, totalpnt)

    if rankroleid == -1:
        response.status_code = 409
        return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
    
    await UpdateRoleConnection(request, discordid)

    try:
        if app.config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers = headers, dhrid = dhrid)
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
                if role in list(app.rankrole.values()):
                    current_discord_roles.append(role)
            if rankroleid in current_discord_roles:
                response.status_code = 409
                return {"error": ml.tr(request, "already_have_rank_role", force_lang = au["language"])}
            else:
                try:
                    r = await arequests.put(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{rankroleid}', headers = headers, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(request, -998, ml.ctr(request, "error_adding_discord_role", var = {"code": err["code"], "discord_role": rankroleid, "user_discordid": discordid, "message": err["message"]}))
                    else:
                        for role in current_discord_roles:
                            r = await arequests.delete(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{role}', headers = headers, dhrid = dhrid)
                            if r.status_code // 100 != 2:
                                err = json.loads(r.text)
                                await AuditLog(request, -998, ml.ctr(request, "error_removing_discord_role", var = {"code": err["code"], "discord_role": role, "user_discordid": discordid, "message": err["message"]}))
                except:
                    pass
                
                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rankroleid}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention)

                if app.config.rank_up.webhook_url != "" or app.config.rank_up.channel_id != "":
                    meta = app.config.rank_up
                    await AutoMessage(app, meta, setvar)

                rankname = point2rankname(app, totalpnt)
                await notification(request, "member", uid, ml.tr(request, "new_rank", var = {"rankname": rankname}, force_lang = await GetUserLanguage(request, uid)), discord_embed = {"title": ml.tr(request, "new_rank_title", force_lang = await GetUserLanguage(request, uid)), "description": f"**{rankname}**", "fields": []})
                return Response(status_code=204)
        else:
            response.status_code = 428
            return {"error": ml.tr(request, "current_user_didnt_join_discord", force_lang = au["language"])}

    except Exception as exc:
        return await tracebackHandler(request, exc, traceback.format_exc())

async def post_resign(request: Request, response: Response, authorization: str = Header(None)):
    """Resigns the authorized user, set userid to -1, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /member/resign', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

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
    
    await app.db.execute(dhrid, f"SELECT mfa_secret, steamid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    mfa_secret = t[0][0]
    steamid = t[0][1]
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

    tracker_app_error = ""
    try:
        if app.config.tracker == "tracksim":
            r = await arequests.delete(app, f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + app.config.tracker_api_token}, dhrid = dhrid)
        if r.status_code == 401:
            tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: {ml.ctr(request, 'invalid_api_token')}"
        elif r.status_code // 100 != 2:
            try:
                resp = json.loads(r.text)
                if "error" in resp.keys() and resp["error"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{resp['error']}`"
                elif "message" in resp.keys() and resp["message"] is not None:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + err["message"] + "`"
                elif len(r.text) <= 64:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `" + r.text + "`"
                else:
                    tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())
                tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_error')}: `{ml.ctr(request, 'unknown_error')}`"
    except:
        tracker_app_error = f"{app.tracker} {ml.ctr(request, 'api_timeout')}"

    if tracker_app_error != "":
        await AuditLog(request, uid, ml.ctr(request, "failed_remove_user_from_tracker_company", var = {"username": name, "userid": userid, "tracker": app.tracker, "error": tracker_app_error}))
    else:
        await AuditLog(request, uid, ml.ctr(request, "removed_user_from_tracker_company", var = {"username": name, "userid": userid, "tracker": app.tracker}))
        
    await UpdateRoleConnection(request, discordid)

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace(f"{uid}", str(uid))

    if app.config.member_leave.webhook_url != "" or app.config.member_leave.channel_id != "":
        meta = app.config.member_leave
        await AutoMessage(app, meta, setvar)
    
    if discordid is not None and app.config.member_leave.role_change != [] and app.config.discord_bot_token != "":
        for role in app.config.member_leave.role_change:
            try:
                if int(role) < 0:
                    r = await arequests.delete(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(request, -998, ml.ctr(request, "error_removing_discord_role", var = {"code": err["code"], "discord_role": str(-int(role)), "user_discordid": discordid, "message": err["message"]}))
                elif int(role) > 0:
                    r = await arequests.put(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(request, -998, ml.ctr(request, "error_adding_discord_role", var = {"code": err["code"], "discord_role": int(role), "user_discordid": discordid, "message": err["message"]}))
            except:
                pass
    
    if discordid is not None and app.config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}", headers = headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                discord_roles = d["roles"]
                current_discord_roles = []
                for role in discord_roles:
                    if role in list(app.rankrole.values()):
                        current_discord_roles.append(role)
                for role in current_discord_roles:
                    r = await arequests.delete(app, f'https://discord.com/api/v10/guilds/{app.config.guild_id}/members/{discordid}/roles/{role}', headers = headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(request, -998, ml.ctr(request, "error_removing_discord_role", var = {"code": err["code"], "discord_role": role, "user_discordid": discordid, "message": err["message"]}))
        except:
            pass

    await AuditLog(request, uid, ml.ctr(request, "member_resigned_audit"))
    await notification(request, "member", uid, ml.tr(request, "member_resigned", force_lang = await GetUserLanguage(request, uid)))
    
    return Response(status_code=204)