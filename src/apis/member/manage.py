# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time
import traceback

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *

# note that the larger the id is, the lower the role is

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

    staff_highest_role = 99999
    for i in au["roles"]:
        if i < staff_highest_role:
            staff_highest_role = i
            
    data = await request.json()
    try:
        new_roles = data["roles"]
        if type(new_roles) != list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        new_roles = intify(new_roles)
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
    oldroles = str2list(t[0][1])
    steamid = t[0][2]
    discordid = t[0][3]
    uid = t[0][5]
    addedroles = []
    removedroles = []
    for role in new_roles:
        if role not in oldroles:
            addedroles.append(role)
    for role in oldroles:
        if role not in new_roles:
            removedroles.append(role)

    if staff_highest_role != (await getHighestActiveRole(dhrid)): 
        # if staff doesn't have the highest role,
        # then check if the role to add is lower than staff's highest role
        for add in addedroles:
            if add <= staff_highest_role:
                response.status_code = 403
                return {"error": ml.tr(request, "add_role_higher_or_equal", force_lang = au["language"])}
    
        for remove in removedroles:
            if remove <= staff_highest_role:
                response.status_code = 403
                return {"error": ml.tr(request, "remove_role_higher_or_equal", force_lang = au["language"])}

    if len(addedroles) + len(removedroles) == 0:
        return Response(status_code=204)
    
    # division staff are only allowed to update division roles
    # not admin, no role access, have division access
    if not checkPerm(au["roles"], "admin") and not checkPerm(au["roles"], ["hrm", "hr", "update_member_roles"]) and checkPerm(au["roles"], "division"):
        for add in addedroles:
            if add not in DIVISION_ROLES:
                response.status_code = 403
                return {"error": ml.tr(request, "only_division_staff_allowed", force_lang = au["language"])}
        for remove in removedroles:
            if remove not in DIVISION_ROLES:
                response.status_code = 403
                return {"error": ml.tr(request, "only_division_staff_allowed", force_lang = au["language"])}

    if checkPerm(au["roles"], "admin") and au["userid"] == userid: # check if user will lose admin permission
        ok = False
        for role in new_roles:
            if role in config.perms.admin:
                ok = True
        if not ok:
            response.status_code = 400
            return {"error": ml.tr(request, "losing_admin_permission", force_lang = au["language"])}

    if config.perms.driver[0] in addedroles:
        if steamid is None:
            response.status_code = 428
            return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"}, force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE user SET roles = ',{list2str(new_roles)},' WHERE userid = {userid}")
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
            await AuditLog(dhrid, au["uid"], ml.ctr("failed_to_add_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKERAPP, "error": tracker_app_error}))
        else:
            await AuditLog(dhrid, au["uid"], ml.ctr("added_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKERAPP}))
        
        if discordid is not None and config.member_welcome.role_change != [] and config.discord_bot_token != "":
            for role in config.member_welcome.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, ml.ctr("error_removing_discord_role", var = {"code": err["code"], "discord_role": str(-int(role)), "user_discordid": discordid, "message": err["message"]}))
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, ml.ctr("error_adding_discord_role", var = {"code": err["code"], "discord_role": int(role), "user_discordid": discordid, "message": err["message"]}))
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
            await AuditLog(dhrid, au["uid"], ml.ctr("failed_to_add_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKERAPP, "error": tracker_app_error}))
        else:
            await AuditLog(dhrid, au["uid"], ml.ctr("added_user_to_tracker_company", var = {"username": username, "userid": userid, "tracker": TRACKERAPP}))

        if discordid is not None and config.member_leave.role_change != [] and config.discord_bot_token != "":
            for role in config.member_leave.role_change:
                try:
                    if int(role) < 0:
                        r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{str(-int(role))}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, ml.ctr("error_removing_discord_role", var = {"code": err["code"], "discord_role": str(-int(role)), "user_discordid": discordid, "message": err["message"]}))
                    elif int(role) > 0:
                        r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed in Drivers Hub."}, timeout = 3, dhrid = dhrid)
                        if r.status_code // 100 != 2:
                            err = json.loads(r.text)
                            await AuditLog(dhrid, -998, ml.ctr("error_adding_discord_role", var = {"code": err["code"], "discord_role": int(role), "user_discordid": discordid, "message": err["message"]}))
                except:
                    traceback.print_exc()
    
    audit = ml.ctr("updated_user_roles", var = {"username": username, "userid": userid}) + "  \n"
    upd = ""
    for add in addedroles:
        role_name = f"{ml.ctr('role')} #{add}\n"
        if add in ROLES.keys():
            role_name = ROLES[add]
        upd += f"`+ {role_name}`  \n"
        audit += f"`+ {role_name}`  \n"
    for remove in removedroles:
        role_name = f"{ml.ctr('role')} #{remove}\n"
        if remove in ROLES.keys():
            role_name = ROLES[remove]
        upd += f"`- {role_name}`  \n"
        audit += f"`- {role_name}`  \n"
    audit = audit[:-1]
    await AuditLog(dhrid, au["uid"], audit)
    await aiosql.commit(dhrid)

    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "role_updated", var = {"detail": upd}, force_lang = await GetUserLanguage(dhrid, uid)))

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
    await AuditLog(dhrid, au["uid"], ml.ctr("updated_user_points", var = {"username": username, "userid": userid, "distance": distance, "mythpoint": mythpoint}))
    uid = (await GetUserInfo(dhrid, request, userid = userid))["uid"]
    await notification(dhrid, "member", uid, ml.tr(request, "point_updated", var = {"distance": distance, "mythpoint": mythpoint}, force_lang = await GetUserLanguage(dhrid, uid)))

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
    staffroles = au["roles"]

    staff_highest_role = 99999
    for role in staffroles:
        if role < staff_highest_role:
            staff_highest_role = role

    if not (await isSecureAuth(dhrid, authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT userid, steamid, name, roles, discordid, uid FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    steamid = t[0][1]
    name = t[0][2]
    roles = str2list(t[0][3])
    discordid = t[0][4]
    uid = t[0][5]
    user_highest_role = 99999
    for role in roles:
        if role < user_highest_role:
            user_highest_role = role
    # note that the larger the id is, the lower the role is
    if staff_highest_role >= user_highest_role:
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
        await AuditLog(dhrid, au["uid"], ml.ctr("failed_to_add_user_to_tracker_company", var = {"username": name, "userid": userid, "tracker": TRACKERAPP, "error": tracker_app_error}))
    else:
        await AuditLog(dhrid, au["uid"], ml.ctr("added_user_to_tracker_company", var = {"username": name, "userid": userid, "tracker": TRACKERAPP}))

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
                        await AuditLog(dhrid, -998, ml.ctr("error_removing_discord_role", var = {"code": err["code"], "discord_role": str(-int(role)), "user_discordid": discordid, "message": err["message"]}))
                elif int(role) > 0:
                    r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{int(role)}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver is dismissed."}, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, ml.ctr("error_adding_discord_role", var = {"code": err["code"], "discord_role": int(role), "user_discordid": discordid, "message": err["message"]}))
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
                    if role in list(RANKROLE.values()):
                        curroles.append(role)
                for role in curroles:
                    r = await arequests.delete(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{role}', headers=headers, timeout = 3, dhrid = dhrid)
                    if r.status_code // 100 != 2:
                        err = json.loads(r.text)
                        await AuditLog(dhrid, -998, ml.ctr("error_removing_discord_role", var = {"code": err["code"], "discord_role": role, "user_discordid": discordid, "message": err["message"]}))
        except:
            pass   
        
    await AuditLog(dhrid, au["uid"], ml.ctr("dismissed_member", var = {"username": name, "uid": uid}))
    await notification(dhrid, "member", uid, ml.tr(request, "member_dismissed", force_lang = await GetUserLanguage(dhrid, uid)))
    return Response(status_code=204)