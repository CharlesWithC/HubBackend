# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *

@app.patch(f'/{config.abbr}/member/{{userid}}/roles')
async def patch_member_roles(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    """Updates the roles of a specific member, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /member/roles', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "division", "update_member_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]

    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)
            
    isAdmin = False
    isHR = False
    isDS = False
    for i in adminroles:
        if int(i) in config.perms.admin:
            isAdmin = True
        if int(i) in config.perms.hr or int(i) in config.perms.hrm:
            isHR = True
        if int(i) in config.perms.division:
            isDS = True

    data = await request.json()
    try:
        roles = data["roles"]
        if type(roles) != list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        roles = [int(x) for x in roles if isint(x)]
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if userid < 0:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_userid", force_lang = au["language"])}
    await aiosql.execute(dhrid, f"SELECT name, roles, steamid, discordid, truckersmpid, uid FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "member_not_found", force_lang = au["language"])}
    username = t[0][0]
    oldroles = t[0][1].split(",")
    steamid = t[0][2]
    discordid = t[0][3]
    truckersmpid = t[0][4]
    uid = t[0][5]
    oldroles = [int(x) for x in oldroles if isint(x)]
    addedroles = []
    removedroles = []
    for role in roles:
        if role not in oldroles:
            addedroles.append(role)
    for role in oldroles:
        if role not in roles:
            removedroles.append(role)

    highestActiveRole = await getHighestActiveRole(dhrid)
    if adminhighest != highestActiveRole: 
        # if operation user doesn't have the highest role,
        # then check if the role to add is lower than operation user's highest role
        for add in addedroles:
            if add <= adminhighest:
                response.status_code = 403
                return {"error": ml.tr(request, "add_role_higher_or_equal", force_lang = au["language"])}
    
        for remove in removedroles:
            if remove <= adminhighest:
                response.status_code = 403
                return {"error": ml.tr(request, "remove_role_higher_or_equal", force_lang = au["language"])}

    if len(addedroles) + len(removedroles) == 0:
        return Response(status_code=204)
        
    if not isAdmin and not isHR and isDS:
        for add in addedroles:
            if add not in divisionroles:
                response.status_code = 403
                return {"error": "Forbidden"}
        for remove in removedroles:
            if remove not in divisionroles:
                response.status_code = 403
                return {"error": "Forbidden"}

    if isAdmin and adminid == userid: # check if user will lose admin permission
        ok = False
        for role in roles:
            if int(role) in config.perms.admin:
                ok = True
        if not ok:
            response.status_code = 400
            return {"error": ml.tr(request, "losing_admin_permission", force_lang = au["language"])}

    if config.perms.driver[0] in addedroles:
        if steamid is None:
            response.status_code = 428
            return {"error": ml.tr(request, "steam_not_bound", force_lang = au["language"])}
        if truckersmpid is None and config.truckersmp_bind:
            response.status_code = 428
            return {"error": ml.tr(request, "truckersmp_not_bound", force_lang = au["language"])}

    roles = [str(i) for i in roles]
    await aiosql.execute(dhrid, f"UPDATE user SET roles = ',{','.join(roles)},' WHERE userid = {userid}")
    await aiosql.commit(dhrid)

    tracker_app_error = ""
    if config.perms.driver[0] in addedroles:
        try:
            if config.tracker.lower() == "tracksim":
                r = await arequests.post("https://api.tracksim.app/v1/drivers/add", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Api-Key " + config.tracker_api_token}, dhrid = dhrid)
            elif config.tracker.lower() == "navio":
                r = await arequests.post("https://api.navio.app/v1/drivers", data = {"steam_id": str(steamid)}, headers = {"Authorization": "Bearer " + config.tracker_api_token}, dhrid = dhrid)
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
            await AuditLog(dhrid, adminid, f"Failed to add `{username}` (User ID: `{userid}`) to {TRACKERAPP} Company.  \n"+tracker_app_error)
        else:
            await AuditLog(dhrid, adminid, f"Added `{username}` (User ID: `{userid}`) to {TRACKERAPP} Company.")
        
        if discordid is not None and config.member_welcome.role_change != [] and config.discord_bot_token != "":
            for role in config.member_welcome.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()

    if config.perms.driver[0] in removedroles:
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
            await AuditLog(dhrid, adminid, f"Failed to remove `{username}` (User ID: `{userid}`) from {TRACKERAPP} Company.  \n"+tracker_app_error)
        else:
            await AuditLog(dhrid, adminid, f"Removed `{username}` (User ID: `{userid}`) from {TRACKERAPP} Company.")

        if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
            for role in config.member_leave.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
                except:
                    traceback.print_exc()
    
    audit = f"Updated `{username}` (User ID: `{userid}`) roles:  \n"
    upd = ""
    for add in addedroles:
        role_name = f"Role #{add}\n"
        if add in ROLES.keys():
            role_name = ROLES[add]
        upd += f"`+ {role_name}`  \n"
        audit += f"`+ {role_name}`  \n"
    for remove in removedroles:
        role_name = f"Role #{remove}\n"
        if remove in ROLES.keys():
            role_name = ROLES[remove]
        upd += f"`- {role_name}`  \n"
        audit += f"`- {role_name}`  \n"
    audit = audit[:-1]
    await AuditLog(dhrid, adminid, audit)
    await aiosql.commit(dhrid)

    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "role_updated", var = {"detail": upd}, force_lang = await GetUserLanguage(dhrid, uid, "en")))

    if tracker_app_error != "":
        return {"tracker_api_error": tracker_app_error.replace(f"{TRACKERAPP} API Error: ", "")}
    else:
        return Response(status_code=204)

@app.patch(f"/{config.abbr}/member/{{userid}}/points")
async def patch_member_points(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    """Updates the points of a specific member, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /member/point', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "update_member_points"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    data = await request.json()
    try:
        distance = int(data["distance"])
        mythpoint = int(data["mythpoint"])
        if mythpoint > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "mythpoint", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if distance != 0:
        if distance > 0:
            await aiosql.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES (-1, {userid}, '', 0, {int(time.time())}, 1, 0, 1, 0, {distance}, -1, 0, 0)")
        else:
            await aiosql.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES (-1, {userid}, '', 0, {int(time.time())}, 0, 0, 1, 0, {distance}, -1, 0, 0)")
        await aiosql.commit(dhrid)
    if mythpoint != 0:
        await aiosql.execute(dhrid, f"INSERT INTO mythpoint VALUES ({userid}, {mythpoint}, {int(time.time())})")
        await aiosql.commit(dhrid)
    
    if int(distance) > 0:
        distance = "+" + data["distance"]
    
    username = (await GetUserInfo(dhrid, request, userid = userid))["name"]
    await AuditLog(dhrid, adminid, f"Updated points of `{username}` (User ID: `{userid}`):\n  Distance: `{distance}km`\n  Myth Point: `{mythpoint}`")
    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "point_updated", var = {"distance": distance, "mythpoint": mythpoint}, force_lang = await GetUserLanguage(dhrid, uid, "en")))

    return Response(status_code=204)

@app.post(f"/{config.abbr}/member/{{userid}}/dismiss")
async def post_member_dismiss(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    """Dismisses member, set userid to -1, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /member/dismiss', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "dismiss_member"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    adminroles = au["roles"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    adminhighest = 99999
    for i in adminroles:
        if int(i) < adminhighest:
            adminhighest = int(i)

    await aiosql.execute(dhrid, f"SELECT userid, steamid, name, roles, discordid, uid FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    steamid = t[0][1]
    name = t[0][2]
    roles = t[0][3].split(",")
    discordid = t[0][4]
    uid = t[0][5]
    roles = [int(x) for x in roles if isint(x)]
    highest = 99999
    for i in roles:
        if int(i) < highest:
            highest = int(i)
    if adminhighest >= highest:
        response.status_code = 403
        return {"error": ml.tr(request, "user_position_higher_or_equal", force_lang = au["language"])}

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
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when removing <@&{str(-int(role))}> from <@!{discordid}>: `{err["message"]}`')
                elif int(role) > 0:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{int(role)}> to <@!{discordid}>: `{err["message"]}`')
            except:
                traceback.print_exc() 
    
    if discordid is not None and config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}
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
        
    await AuditLog(dhrid, adminid, f'Dismissed member: `{name}` (UID: `{uid}`)')
    await notification(dhrid, "member", uid, ml.tr(request, "member_dismissed", force_lang = await GetUserLanguage(dhrid, uid, "en")))
    return Response(status_code=204)