# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import traceback

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *
from plugins.division import DIVISIONPNT

@app.patch(f"/{config.abbr}/member/roles/rank")
async def patch_member_roles_rank(request: Request, response: Response, authorization: str = Header(None)):
    """Updates rank role of the authorized user in Discord, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /member/roles/rank', 60, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
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
        return {"error": ml.tr(request, "discord_not_connected", force_lang = au["language"])}
    
    ratio = 1
    if config.distance_unit == "imperial":
        ratio = 0.621371

    # calculate distance
    userdistance = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(distance) FROM dlog WHERE userid = {userid} GROUP BY userid")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        if not tt[0] in userdistance.keys():
            userdistance[tt[0]] = nint(tt[1])
        else:
            userdistance[tt[0]] += nint(tt[1])
        userdistance[tt[0]] = int(userdistance[tt[0]])

    # calculate challenge
    userchallenge = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(points) FROM challenge_completed WHERE userid = {userid} GROUP BY userid")
    o = await aiosql.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userchallenge.keys():
            userchallenge[oo[0]] = 0
        userchallenge[oo[0]] += oo[1]

    # calculate event
    userevent = {}
    await aiosql.execute(dhrid, f"SELECT attendee, points FROM event WHERE attendee LIKE '%,{userid},%'")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        attendees = tt[0].split(",")
        attendees = [int(x) for x in attendees if isint(x)]
        for ttt in attendees:
            attendee = int(ttt)
            if not attendee in userevent.keys():
                userevent[attendee] = tt[1]
            else:
                userevent[attendee] += tt[1]
    
    # calculate division
    userdivision = {}
    await aiosql.execute(dhrid, f"SELECT userid, divisionid, COUNT(*) FROM division WHERE status = 1 AND userid = {userid} GROUP BY divisionid, userid")
    o = await aiosql.fetchall(dhrid)
    for oo in o:
        if not oo[0] in userdivision.keys():
            userdivision[oo[0]] = 0
        if oo[1] in DIVISIONPNT.keys():
            userdivision[oo[0]] += oo[2] * DIVISIONPNT[oo[1]]
    
    # calculate myth
    usermyth = {}
    await aiosql.execute(dhrid, f"SELECT userid, SUM(point) FROM mythpoint WHERE userid = {userid} GROUP BY userid")
    o = await aiosql.fetchall(dhrid)
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
    rankroleid = point2rankroleid(totalpnt)

    if rankroleid == -1:
        response.status_code = 409
        return {"error": ml.tr(request, "already_have_discord_role", force_lang = au["language"])}

    try:
        if config.discord_bot_token == "":
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}

        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver ranks up in Drivers Hub."}
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
        except:
            traceback.print_exc()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}
            
        if r.status_code == 401:
            DisableDiscordIntegration()
            response.status_code = 503
            return {"error": ml.tr(request, "discord_integrations_disabled", force_lang = au["language"])}
        elif r.status_code // 100 != 2:
            response.status_code = 503
            return {"error": ml.tr(request, "discord_api_inaccessible", force_lang = au["language"])}

        d = json.loads(r.text)
        if "roles" in d:
            roles = d["roles"]
            curroles = []
            for role in roles:
                if int(role) in list(RANKROLE.values()):
                    curroles.append(int(role))
            if rankroleid in curroles:
                response.status_code = 409
                return {"error": ml.tr(request, "already_have_discord_role", force_lang = au["language"])}
            else:
                try:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{rankroleid}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{rankroleid}> to <@!{discordid}>: `{err["message"]}`')
                    else:
                        for role in curroles:
                            r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                            if r.status_code // 100 != 2:
                                err = json.loads(r.text)
                                await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()
                
                usermention = f"<@{discordid}>"
                rankmention = f"<@&{rankroleid}>"
                def setvar(msg):
                    return msg.replace("{mention}", usermention).replace("{name}", username).replace("{userid}", str(userid)).replace("{rank}", rankmention)

                if config.rank_up.webhook_url != "" or config.rank_up.channel_id != "":
                    meta = config.rank_up
                    await AutoMessage(meta, setvar)

                rankname = point2rankname(totalpnt)
                await notification(dhrid, "member", uid, ml.tr(request, "new_rank", var = {"rankname": rankname}, force_lang = await GetUserLanguage(dhrid, uid)), discord_embed = {"title": ml.tr(request, "new_rank_title", force_lang = await GetUserLanguage(dhrid, uid)), "description": f"**{rankname}**", "fields": []})
                return Response(status_code=204)
        else:
            response.status_code = 428
            return {"error": ml.tr(request, "must_join_discord", force_lang = au["language"])}

    except:
        traceback.print_exc()

@app.post(f"/{config.abbr}/member/resign")
async def post_member_resign(request: Request, response: Response, authorization: str = Header(None)):
    """Resigns the authorized user, set userid to -1, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /member/resign', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    uid = au["uid"]
    userid = au["userid"]
    discordid = au["discordid"]
    name = convertQuotation(au["name"])

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT mfa_secret, steamid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    mfa_secret = t[0][0]
    steamid = t[0][1]
    if mfa_secret != "":
        data = await request.json()
        try:
            otp = int(data["otp"])
        except:
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}
        if not valid_totp(otp, mfa_secret):
            response.status_code = 400
            return {"error": ml.tr(request, "mfa_invalid_otp", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    await aiosql.commit(dhrid)

    tracker_app_error = ""
    try:
        if config.tracker.lower() == "tracksim":
            r = await arequests.delete(f"https://api.tracksim.app/v1/drivers/remove", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
        elif config.tracker.lower() == "navio":
            r = await arequests.delete(f"https://api.navio.app/v1/drivers/{steamid}", headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
        if r.status_code == 401:
            tracker_app_error = f"{TRACKERAPP} API Error: Invalid API Token"
        elif r.status_code // 100 != 2:
            try:
                resp = json.loads(r.text)
                if "error" in resp.keys() and resp["error"] is not None:
                    tracker_app_error = f"{TRACKERAPP} API Error: `{resp['error']}`"
                elif "message" in resp.keys() and resp["message"] is not None:
                    tracker_app_error = f"{TRACKERAPP} API Error: `" + err["message"] + "`"
                elif len(r.text) <= 64:
                    tracker_app_error = f"{TRACKERAPP} API Error: `" + r.text + "`"
                else:
                    tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
            except:
                traceback.print_exc()
                tracker_app_error = f"{TRACKERAPP} API Error: `Unknown Error`"
    except:
        tracker_app_error = f"{TRACKERAPP} API Timeout"

    if tracker_app_error != "":
        await AuditLog(dhrid, -999, f"Failed to remove `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.  \n"+tracker_app_error)
    else:
        await AuditLog(dhrid, -999, f"Removed `{name}` (User ID: `{userid}`) from {TRACKERAPP} Company.")

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace(f"{uid}", str(uid))

    if config.member_leave.webhook_url != "" or config.member_leave.channel_id != "":
        meta = config.member_leave
        await AutoMessage(meta, setvar)
    
    if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
        for role in config.member_leave.role_change:
            try:
                if int(role) < 0:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                elif int(role) > 0:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
            except:
                traceback.print_exc()
    
    if discordid is not None and config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver resigns."}
        try:
            r = await arequests.get(f"https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}", headers=headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                roles = d["roles"]
                curroles = []
                for role in roles:
                    if int(role) in list(RANKROLE.values()):
                        curroles.append(int(role))
                for role in curroles:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{role}> from <@!{discordid}>: `{err["message"]}`')
        except:
            pass

    await AuditLog(dhrid, -999, f'Member resigned: `{name}` (UID: `{uid}`)')
    await notification(dhrid, "member", uid, ml.tr(request, "member_resigned", force_lang = await GetUserLanguage(dhrid, uid)))
    
    return Response(status_code=204)