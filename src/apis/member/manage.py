# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import time

from fastapi import Header, Request, Response
from typing import Optional

import multilang as ml
from functions import *

# note that the larger the id is, the lower the role is

async def patch_roles(request: Request, response: Response, userid: int, authorization: str = Header(None), sync_to_discord: Optional[bool] = True, sync_add_only: Optional[bool] = False):
    """Updates the roles of a specific member, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /member/roles', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_divisions", "update_roles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staff_highest_order_id = None
    for role in au["roles"]:
        if role in app.roles.keys():
            if staff_highest_order_id is None or app.roles[role]["order_id"] < staff_highest_order_id:
                staff_highest_order_id = app.roles[role]["order_id"]
    if staff_highest_order_id is None:
        response.status_code = 403
        return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    data = await request.json()
    try:
        new_roles = data["roles"]
        if type(new_roles) != list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        new_roles = deduplicate(intify(new_roles))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if userid < 0:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_userid", force_lang = au["language"])}
    await app.db.execute(dhrid, f"SELECT name, roles, steamid, discordid, truckersmpid, uid, avatar FROM user WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "member_not_found", force_lang = au["language"])}
    username = t[0][0]
    old_roles = str2list(t[0][1])
    steamid = t[0][2]
    discordid = t[0][3]
    uid = t[0][5]
    avatar = t[0][6]
    added_roles = []
    removed_roles = []
    for role in new_roles:
        if role not in old_roles:
            added_roles.append(role)
    for role in old_roles:
        if role not in new_roles:
            removed_roles.append(role)
    for role in new_roles:
        if role not in app.roles.keys():
            response.status_code = 400
            return {"error": ml.tr(request, "role_not_found", force_lang = au["language"])}

    if staff_highest_order_id != app.roles[(await getHighestActiveRole(request))]["order_id"]:
        # if staff doesn't have the highest role,
        # then check if the role to add is lower than staff's highest role

        # NOTE: Added/Removed role may be already gone in config, so we need to check if it still exists
        for add in added_roles:
            if add in app.roles.keys():
                if app.roles[add]["order_id"] <= staff_highest_order_id:
                    response.status_code = 403
                    return {"error": ml.tr(request, "add_role_higher_or_equal", force_lang = au["language"])}

        for remove in removed_roles:
            if remove in app.roles.keys():
                if app.roles[remove]["order_id"] <= staff_highest_order_id:
                    response.status_code = 403
                    return {"error": ml.tr(request, "remove_role_higher_or_equal", force_lang = au["language"])}

    if len(added_roles) + len(removed_roles) == 0:
        return Response(status_code=204)

    # division staff are only allowed to update division roles
    # not administrator, no role access, have division access
    if not checkPerm(app, au["roles"], "administrator") and not checkPerm(app, au["roles"], ["update_roles"]) and checkPerm(app, au["roles"], "manage_divisions"):
        for add in added_roles:
            if add not in app.division_roles:
                response.status_code = 403
                return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}
        for remove in removed_roles:
            if remove not in app.division_roles:
                response.status_code = 403
                return {"error": ml.tr(request, "no_access_to_resource", force_lang = au["language"])}

    if au["userid"] == userid and checkPerm(app, old_roles, "administrator") and \
            not checkPerm(app, new_roles, "administrator"): # check if user will lose administrator permission
        response.status_code = 400
        return {"error": ml.tr(request, "losing_admin_permission", force_lang = au["language"])}

    if checkPerm(app, new_roles, "driver"):
        if steamid is None:
            response.status_code = 428
            return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET roles = ',{list2str(new_roles)},' WHERE userid = {userid}")
    await app.db.commit(dhrid)
    await GetUserInfo(request, userid = userid, nocache = True) # force update cache

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar)).replace("{staff_mention}", f"<@!{au['discordid']}>").replace("{staff_name}", au["name"]).replace("{staff_userid}", str(au["userid"])).replace("{staff_uid}", str(au["uid"])).replace("{staff_avatar}", validateUrl(au["avatar"]))

    tracker_app_error = ""

    if checkPerm(app, old_roles, "driver") and not checkPerm(app, new_roles, "driver"):
        tracker_app_error += await remove_driver(request, steamid, au["uid"], userid, username) + "\n"

        await UpdateRoleConnection(request, discordid)

        for meta in app.config.driver_role_remove:
            meta = Dict2Obj(meta)
            if meta.webhook_url != "" or meta.channel_id != "":
                await AutoMessage(app, meta, setvar)

            if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
                for role in meta.role_change:
                    try:
                        if int(role) < 0:
                            opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed."}, f"remove_role,{-int(role)},{discordid}")
                        elif int(role) > 0:
                            opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is removed."}, f"add_role,{int(role)},{discordid}")
                    except:
                        pass

    if checkPerm(app, new_roles, "driver") and not checkPerm(app, old_roles, "driver"):
        tracker_app_error += await add_driver(request, steamid, au["uid"], userid, username) + "\n"

        await UpdateRoleConnection(request, discordid)

        for meta in app.config.driver_role_add:
            meta = Dict2Obj(meta)
            if meta.webhook_url != "" or meta.channel_id != "":
                await AutoMessage(app, meta, setvar)

            if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
                for role in meta.role_change:
                    try:
                        if int(role) < 0:
                            opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"remove_role,{-int(role)},{discordid}")
                        elif int(role) > 0:
                            opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when driver role is added."}, f"add_role,{int(role)},{discordid}")
                    except:
                        pass

    tracker_app_error = tracker_app_error[:-1]

    if sync_to_discord:
        for role in app.config.roles:
            try:
                if int(role["id"]) in added_roles:
                    if "discord_role_id" in role.keys() and isint(role["discord_role_id"]):
                        opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role["discord_role_id"])}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when role is added on Drivers Hub."}, f"add_role,{int(role['discord_role_id'])},{discordid}")
                elif int(role["id"]) in removed_roles and not sync_add_only:
                    if "discord_role_id" in role.keys() and isint(role["discord_role_id"]):
                        opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role["discord_role_id"])}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when role is removed on Drivers Hub."}, f"add_role,{int(role['discord_role_id'])},{discordid}")
            except:
                pass

    audit = ml.ctr(request, "updated_user_roles", var = {"username": username, "userid": userid}) + "  \n"
    upd = ""
    for add in added_roles:
        role_name = f"{ml.ctr(request, 'role')} #{add}\n"
        if add in app.roles.keys():
            role_name = app.roles[add]["name"]
        upd += f"`+ {role_name}`  \n"
        audit += f"`+ {role_name}`  \n"
    for remove in removed_roles:
        role_name = f"{ml.ctr(request, 'role')} #{remove}\n"
        if remove in app.roles.keys():
            role_name = app.roles[remove]["name"]
        upd += f"`- {role_name}`  \n"
        audit += f"`- {role_name}`  \n"
    audit = audit[:-1]
    await AuditLog(request, au["uid"], "member", audit)
    await app.db.execute(dhrid, f"INSERT INTO user_role_history(uid, added_roles, removed_roles, timestamp) VALUES ({uid}, ',{list2str(added_roles)},', ',{list2str(removed_roles)},', {int(time.time())})")
    await app.db.commit(dhrid)

    uid = (await GetUserInfo(request, userid = userid, nocache = True, is_internal_function = True))["uid"] # purge cache and get uid
    await notification(request, "member", uid, ml.tr(request, "role_updated", var = {"detail": upd}, force_lang = await GetUserLanguage(request, uid)))

    if tracker_app_error != "":
        return {"service_api_error": tracker_app_error}
    else:
        return Response(status_code=204)

async def patch_points(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    """Updates the points of a specific member, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /member/points', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_points"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        distance = int(data["distance"])
        if abs(distance) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "distance", "limit": "2,147,483,647"}, force_lang = au["language"])}
        distance_note = ""
        if "distance_note" in data.keys():
            distance_note = data["distance_note"]
            if len(distance_note) > 256:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "distance_note", "limit": "256"}, force_lang = au["language"])}
        bonus_points = int(data["bonus"])
        if abs(bonus_points) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "bonus", "limit": "2,147,483,647"}, force_lang = au["language"])}
        bonus_note = ""
        if "bonus_note" in data.keys():
            bonus_note = data["bonus_note"]
            if len(bonus_note) > 256:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "bonus_note", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if distance != 0:
        await app.db.execute(dhrid, "SELECT MIN(logid) FROM dlog WHERE logid < 0")
        plogid = nint(await app.db.fetchone(dhrid)) - 1
        dlog_data = json.dumps({"staff_userid": au["userid"], "note": distance_note})
        if distance > 0:
            await app.db.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({plogid}, {userid}, '{convertQuotation(dlog_data)}', 0, {int(time.time())}, 1, 0, 1, 0, {distance}, -1, 0, 0)")
            await app.db.execute(dhrid, f"INSERT INTO dlog_meta(logid, note) VALUES ({plogid}, '{au['userid']},{convertQuotation(distance_note)}')")
        else:
            await app.db.execute(dhrid, f"INSERT INTO dlog(logid, userid, data, topspeed, timestamp, isdelivered, profit, unit, fuel, distance, trackerid, tracker_type, view_count) VALUES ({plogid}, {userid}, '{convertQuotation(dlog_data)}', 0, {int(time.time())}, 0, 0, 1, 0, {distance}, -1, 0, 0)")
            await app.db.execute(dhrid, f"INSERT INTO dlog_meta(logid, note) VALUES ({plogid}, '{au['userid']}, {convertQuotation(distance_note)}')")
        await UpdateRoleConnection(request, (await GetUserInfo(request, userid = userid, is_internal_function = True))["discordid"])
        await app.db.commit(dhrid)
    if bonus_points != 0:
        await app.db.execute(dhrid, f"INSERT INTO bonus_point VALUES ({userid}, {bonus_points}, '{convertQuotation(bonus_note)}', {au['userid']}, {int(time.time())})")
        await app.db.commit(dhrid)

    if int(distance) > 0:
        distance = "+" + str(distance)
    if int(bonus_points) > 0:
        bonus_points = "+" + str(bonus_points)

    username = (await GetUserInfo(request, userid = userid))["name"]
    await AuditLog(request, au["uid"], "member", ml.ctr(request, "updated_user_points", var = {"username": username, "userid": userid, "distance": distance, "distance_note": distance_note if distance_note != "" else "N/A", "bonus_points": bonus_points, "bonus_note": bonus_note if bonus_note != "" else "N/A"}))
    uid = (await GetUserInfo(request, userid = userid, is_internal_function = True))["uid"]
    await notification(request, "member", uid, ml.tr(request, "point_updated", var = {"distance": distance, "bonus_points": bonus_points}, force_lang = await GetUserLanguage(request, uid)))

    return Response(status_code=204)

async def post_dismiss(request: Request, response: Response, userid: int, authorization: str = Header(None)):
    """Dismisses member, set userid to -1, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /member/dismiss', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, required_permission = ["administrator", "dismiss_members"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    staff_highest_order_id = None
    for role in au["roles"]:
        if role in app.roles.keys():
            if staff_highest_order_id is None or app.roles[role]["order_id"] < staff_highest_order_id:
                staff_highest_order_id = app.roles[role]["order_id"]

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid, steamid, name, roles, discordid, uid, avatar FROM user WHERE userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    steamid = t[0][1]
    name = t[0][2]
    roles = str2list(t[0][3])
    discordid = t[0][4]
    uid = t[0][5]
    avatar = t[0][6]

    user_highest_order_id = None
    for role in roles:
        if role in app.roles.keys():
            if user_highest_order_id is None or app.roles[role]["order_id"] < user_highest_order_id:
                user_highest_order_id = app.roles[role]["order_id"]

    # note that the larger the order id is, the lower the role is
    if user_highest_order_id is not None and staff_highest_order_id >= user_highest_order_id or \
            staff_highest_order_id is None and user_highest_order_id is not None:
        response.status_code = 403
        return {"error": ml.tr(request, "user_position_higher_or_equal", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET userid = -1, roles = '' WHERE userid = {userid}")
    await app.db.execute(dhrid, f"DELETE FROM economy_balance WHERE userid = {userid}")
    await app.db.execute(dhrid, f"DELETE FROM economy_truck WHERE userid = {userid}")
    await app.db.execute(dhrid, f"UPDATE economy_garage SET userid = -1000 WHERE userid = {userid}")
    await app.db.commit(dhrid)

    app.redis.delete(f"umap:userid={userid}")
    await GetUserInfo(request, uid = uid, nocache = True) # force update cache

    await remove_driver(request, steamid, au["uid"], userid, name)

    await UpdateRoleConnection(request, discordid)

    def setvar(msg):
        return msg.replace("{mention}", f"<@!{discordid}>").replace("{name}", name).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar)).replace("{staff_mention}", f"<@!{au['discordid']}>").replace("{staff_name}", au["name"]).replace("{staff_userid}", str(au["userid"])).replace("{staff_uid}", str(au["uid"])).replace("{staff_avatar}", validateUrl(au["avatar"]))

    for meta in app.config.member_leave:
        meta = Dict2Obj(meta)
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

        if discordid is not None and meta.role_change != [] and app.config.discord_bot_token != "":
            for role in meta.role_change:
                try:
                    if int(role) < 0:
                        opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{str(-int(role))}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member is dismissed."}, f"remove_role,{-int(role)},{discordid}")
                    elif int(role) > 0:
                        opqueue.queue(app, "put", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{int(role)}', None, {"Authorization": f"Bot {app.config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when member is dismissed."}, f"add_role,{int(role)},{discordid}")
                except:
                    pass

    if discordid is not None and app.config.discord_bot_token != "":
        headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json", "X-Audit-Log-Reason": "Automatic role changes when member is dismissed."}
        try:
            r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}", headers = headers, timeout = 3, dhrid = dhrid)
            d = json.loads(r.text)
            if "roles" in d:
                roles = d["roles"]
                curroles = []
                for role in roles:
                    for rank_type in app.config.rank_types:
                        for rank in rank_type["details"]:
                            if str(role) == str(rank["discord_role_id"]):
                                curroles.append(role)
                for role in curroles:
                    opqueue.queue(app, "delete", app.config.discord_guild_id, f'https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members/{discordid}/roles/{role}', None, headers, f"remove_role,{role},{discordid}")
        except:
            pass

    await AuditLog(request, au["uid"], "member", ml.ctr(request, "dismissed_member", var = {"username": name, "uid": uid}))
    await notification(request, "member", uid, ml.tr(request, "member_dismissed", force_lang = await GetUserLanguage(request, uid)))
    return Response(status_code=204)
