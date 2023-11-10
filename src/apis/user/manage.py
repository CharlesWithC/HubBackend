# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def post_accept(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """[Permission Control] Accepts a user as member, assign userid, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /user/accept', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "accept_members"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    try:
        try:
            data = await request.json()
        except:
            data = {}
        if "tracker" in data.keys():
            tracker_in_use = data["tracker"].lower()
            if tracker_in_use == "tracksim":
                tracker_in_use = 2
            elif tracker_in_use == "trucky":
                tracker_in_use = 3
            else:
                response.status_code = 400
                return {"error": ml.tr(request, "config_invalid_value", var = {"item": "tracker"}, force_lang = au["language"])}
        else:
            if len(app.config.trackers) > 0:
                # in case tracker_in_use is not provided in json
                # we'll consider the first tracker as tracker_in_use
                if app.config.trackers[0]["type"] == "tracksim":
                    tracker_in_use = 2
                elif app.config.trackers[0]["type"] == "trucky":
                    tracker_in_use = 3
            else:
                response.status_code = 400
                return {"error": ml.tr(request, "config_invalid_value", var = {"item": "tracker"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "banned_user_cannot_be_accepted", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid, name, discordid, name, steamid, truckersmpid, email, avatar FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    if t[0][0] not in [-1, None]:
        response.status_code = 409
        return {"error": ml.tr(request, "user_is_already_member", force_lang = au["language"])}
    name = t[0][1]
    discordid = t[0][2]
    username = t[0][3]
    steamid = t[0][4]
    truckersmpid = t[0][5]
    email = t[0][6]
    avatar = t[0][7]
    if '@' not in email and "email" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Email"}, force_lang = au["language"])}
    if discordid is None and "discord" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Discord"}, force_lang = au["language"])}
    if steamid is None and "steam" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"}, force_lang = au["language"])}
    if truckersmpid is None and "truckersmp" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "TruckersMP"}, force_lang = au["language"])}

    await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
    t = await app.db.fetchall(dhrid)
    userid = int(t[0][0])

    await app.db.execute(dhrid, f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())}, tracker_in_use = {tracker_in_use} WHERE uid = {uid}")
    await app.db.execute(dhrid, f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(request, au["uid"], ml.ctr(request, "accepted_user_as_member", var = {"username": name, "userid": userid, "uid": uid}))
    await app.db.commit(dhrid)

    await notification(request, "member", uid, ml.tr(request, "member_accepted", var = {"userid": userid}, force_lang = await GetUserLanguage(request, uid)))

    def setvar(msg):
        return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid)).replace("{avatar}", validateUrl(avatar)).replace("{staff_mention}", f"<@!{au['discordid']}>").replace("{staff_name}", au["name"]).replace("{staff_userid}", str(au["userid"])).replace("{staff_uid}", str(au["uid"])).replace("{staff_avatar}", validateUrl(au["avatar"]))

    for meta in app.config.member_accept:
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

    return {"userid": userid}

async def patch_connections(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """[Permission Control] Updates account connections for a specific user, returns 204

    JSON: `{"email": Optional[str], "discordid": Optional[int], "steamid": Optional[int], "truckersmpid": Optional[int]}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/connections', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["administrator", "update_connections"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    userinfo = await GetUserInfo(request, uid = uid)
    connections = [userinfo["email"], userinfo["discordid"], userinfo["steamid"], userinfo["truckersmpid"]]
    new_connections = [None, None, None, None]
    connections_key = ["email", "discordid", "steamid", "truckersmpid"]

    await app.db.execute(dhrid, f"SELECT uid, name FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    data = await request.json()
    try:
        if "email" in data.keys():
            new_connections[0] = data["email"]
        if "discordid" in data.keys():
            new_connections[1] = abs(int(data["discordid"]))
            if new_connections[1] > 18446744073709551615:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "discordid", "limit": "18,446,744,073,709,551,615"}, force_lang = au["language"])}
        if "steamid" in data.keys():
            new_connections[2] = abs(int(data["steamid"]))
            if new_connections[2] > 18446744073709551615:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "steamid", "limit": "18,446,744,073,709,551,615"}, force_lang = au["language"])}
        if "truckersmpid" in data.keys():
            new_connections[3] = abs(int(data["truckersmpid"]))
            if new_connections[3] > 18446744073709551615:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "truckersmpid", "limit": "18,446,744,073,709,551,615"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    for i in range(0,4):
        if new_connections[i] is None:
            continue

        await app.db.execute(dhrid, f"SELECT uid, userid, discordid FROM user WHERE {connections_key[i]} = '{convertQuotation(new_connections[i])}' AND uid != {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) > 0:
            if t[0][1] not in [-1, None]:
                response.status_code = 409
                return {"error": ml.tr(request, "user_exists_with_new_connections", force_lang = au["language"])}

    connections = [new_connections[i] if new_connections[i] is not None else connections[i] for i in range(0,4)]
    connections = [x if x is not None else "NULL" for x in connections]
    connections[0] = f"'{convertQuotation(connections[0])}'" if connections[0] != "NULL" else "NULL"

    # update discord binding
    await app.db.execute(dhrid, f"UPDATE user SET email = {connections[0]}, discordid = {connections[1]}, steamid = {connections[2]}, truckersmpid = {connections[3]} WHERE uid = {uid}")
    await app.db.commit(dhrid)

    if connections[1] is not None:
        await UpdateRoleConnection(request, connections[1])

    await AuditLog(request, au["uid"], ml.ctr(request, "updated_connections", var = {"username": userinfo["name"], "uid": uid}))

    return Response(status_code=204)

async def delete_connections(request: Request, response: Response, uid: int, connection: str, authorization: str = Header(None)):
    """[Permission Control] Deletes connections for a specific user."""
    connections_key = ["email", "discordid", "steamid", "truckersmpid"]
    if connection not in connections_key:
        response.status_code = 404
        return {"error": "Not Found"}
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user/connections', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["administrator", "update_connections"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if uid is None:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT userid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE user SET {connection} = NULL WHERE uid = {uid}")
    await app.db.commit(dhrid)

    username = (await GetUserInfo(request, uid = uid))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_connections", var = {"username": username, "uid": uid}))

    return Response(status_code=204)

async def get_ban_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, after_uid: Optional[int] = None, reason: Optional[str] = "", \
        order_by: Optional[str] = "uid", order: Optional[str] = "asc"):
    """Returns the information of a list of banned users"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/ban/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "ban_users"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    reason = convertQuotation(reason).lower()

    if order_by not in ['uid', 'email', 'discordid', 'steamid', 'truckersmpid']:
        order_by = "uid"
        order = "asc"

    order = order.lower()
    if order not in ['asc', 'desc']:
        order = "asc"

    await app.db.execute(dhrid, f"SELECT uid, email, discordid, steamid, truckersmpid, reason, expire_timestamp FROM banned WHERE reason LIKE '%{reason}%' ORDER BY {order_by} {order}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        userinfo = await GetUserInfo(request, uid = tt[0])
        if userinfo["join_timestamp"] is None:
            userinfo = await GetUserInfo(request, discordid = tt[2])
        if userinfo["join_timestamp"] is None:
            userinfo = None
        discordid = str(tt[2]) if tt[2] is not None else None
        steamid = str(tt[3]) if tt[3] is not None else None
        ret.append({"user": userinfo, "meta": {"uid": tt[0], "email": tt[1], "discordid": discordid, "steamid": steamid, "truckersmpid": tt[4]}, "ban": {"reason": tt[5], "expire": tt[6]}})

    if after_uid is not None:
        while len(ret) > 0 and ret[0]["meta"]["uid"] != after_uid:
            ret = ret[1:]

    return {"list": ret[max(page-1, 0) * page_size : page * page_size], "total_items": len(ret), "total_pages": int(math.ceil(len(ret) / page_size))}

async def get_ban(request: Request, response: Response, authorization: str = Header(None), \
    uid: Optional[int] = None, email: Optional[str] = None, discordid: Optional[int] = None, steamid: Optional[int] = None, truckersmpid: Optional[int] = None):
    """Returns info of specific banned user if exists"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /user/ban', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "ban_users"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    qu = ""
    if uid is not None:
        qu = f"uid = {uid}"
    elif email is not None:
        qu = f"email = '{convertQuotation(email)}'"
    elif discordid is not None:
        qu = f"discordid = {discordid}"
    elif steamid is not None:
        qu = f"steamid = {steamid}"
    elif truckersmpid is not None:
        qu = f"truckersmpid = {truckersmpid}"
    else:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    await app.db.execute(dhrid, f"SELECT uid, email, discordid, steamid, truckersmpid, reason, expire_timestamp FROM banned WHERE {qu}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found")}

    tt = t[0]
    userinfo = await GetUserInfo(request, uid = tt[0])
    if userinfo["join_timestamp"] is None:
        userinfo = await GetUserInfo(request, discordid = tt[2])
    if userinfo["join_timestamp"] is None:
        userinfo = None

    discordid = str(tt[2]) if tt[2] is not None else None
    steamid = str(tt[3]) if tt[3] is not None else None

    return {"user": userinfo, "meta": {"uid": tt[0], "email": tt[1], "discordid": discordid, "steamid": steamid, "truckersmpid": tt[4]}, "ban": {"reason": tt[5], "expire": tt[6]}}

async def put_ban(request: Request, response: Response, authorization: str = Header(None)):
    """Bans user with specific connections, returns 204

    JSON: {"expire": Optional[int], "reason": str}"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PUT /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "ban_users"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    connections = []

    data = await request.json()
    try:
        fields = ["uid", "email", "discordid", "steamid", "truckersmpid"]
        for field in fields:
            if field not in data.keys():
                data[field] = "NULL"
            else:
                if field == "email":
                    data[field] = f"'{convertQuotation(data[field])}'"
                else:
                    data[field] = abs(int(data[field]))
                    if data[field] > 18446744073709551615:
                        response.status_code = 400
                        return {"error": ml.tr(request, "value_too_large", var = {"item": field, "limit": "18,446,744,073,709,551,615"}, force_lang = au["language"])}
            connections.append(data[field])

        expire = 0
        if "expire" in data.keys():
            expire = nint(data["expire"])
        if expire <= 0:
            expire = "NULL"
        else:
            if expire > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "expire", "limit": "2,147,483,647"}, force_lang = au["language"])}
        reason = ""
        if "reason" in data.keys():
            reason = convertQuotation(data["reason"])
            if len(reason) > 256:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "reason", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if connections[1] != "NULL" and '@' not in connections[1]:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT uid, userid, name, email, discordid, steamid, truckersmpid FROM user WHERE uid = {connections[0]} OR email = {connections[1]} OR discordid = {connections[2]} OR steamid = {connections[3]} OR truckersmpid = {connections[4]}")
    t = await app.db.fetchall(dhrid)
    username = ml.ctr(request, "unknown_user")
    if len(t) == 0:
        [uid, email, discordid, steamid, truckersmpid] = connections
    elif len(t) == 1:
        uid = t[0][0]
        userid = t[0][1]
        username = t[0][2]
        email = f"'{convertQuotation(t[0][3])}'" if t[0][3] is not None else "NULL"
        discordid = t[0][4] if t[0][4] is not None else "NULL"
        steamid = t[0][5] if t[0][5] is not None else "NULL"
        truckersmpid = t[0][6] if t[0][6] is not  None else "NULL"
        connections = [uid, email, discordid, steamid, truckersmpid]
        if userid not in [-1, None]:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_ban", force_lang = au["language"])}
    elif len(t) > 1:
        response.status_code = 409
        return {"error": ml.tr(request, "connections_linked_to_multiple_users", force_lang = au["language"])}

    if connections[1] != "NULL" and '@' not in connections[1]:
        connections[1] = "NULL"

    await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {connections[0]} OR email = {connections[1]} OR discordid = {connections[2]} OR steamid = {connections[3]} OR truckersmpid = {connections[4]}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO banned VALUES ({uid}, {email}, {discordid}, {steamid}, {truckersmpid}, {expire}, '{reason}')")
        await app.db.execute(dhrid, f"INSERT INTO ban_history (uid, email, discordid, steamid, truckersmpid, expire_timestamp, reason) VALUES ({uid}, {email}, {discordid}, {steamid}, {truckersmpid}, {expire}, '{reason}')")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.commit(dhrid)
        if uid != "NULL":
            duration = ml.ctr(request, "forever")
            if expire != "NULL":
                duration = ml.ctr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
            await AuditLog(request, au["uid"], ml.ctr(request, "banned_user", var = {"username": username, "uid": uid, "expire": duration}))
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "user_already_banned", force_lang = au["language"])}

async def delete_ban(request: Request, response: Response, authorization: str = Header(None)):
    """Unbans a specific user, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "ban_users"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    connections = []

    data = await request.json()
    try:
        fields = ["uid", "email", "discordid", "steamid", "truckersmpid"]
        for field in fields:
            if field not in data.keys():
                data[field] = "NULL"
            else:
                if field == "email":
                    data[field] = f"'{convertQuotation(data[field])}'"
                else:
                    data[field] = abs(int(data[field]))
                    if data[field] > 18446744073709551615:
                        response.status_code = 400
                        return {"error": ml.tr(request, "value_too_large", var = {"item": field, "limit": "18,446,744,073,709,551,615"}, force_lang = au["language"])}
            connections.append(data[field])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if connections[1] != "NULL" and '@' not in connections[1]:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT uid FROM banned WHERE uid = {connections[0]} OR email = {connections[1]} OR discordid = {connections[2]} OR steamid = {connections[3]} OR truckersmpid = {connections[4]}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 409
        return {"error": ml.tr(request, "user_not_banned", force_lang = au["language"])}
    else:
        await app.db.execute(dhrid, f"DELETE FROM banned WHERE uid = {connections[0]} OR email = {connections[1]} OR discordid = {connections[2]} OR steamid = {connections[3]} OR truckersmpid = {connections[4]}")
        await app.db.commit(dhrid)

        for tt in t:
            if tt[0] is not None:
                username = (await GetUserInfo(request, uid = tt[0]))["name"]
                await AuditLog(request, au["uid"], ml.ctr(request, "unbanned_user", var = {"username": username, "uid": tt[0]}))

        return Response(status_code=204)

async def delete_ban_history(request: Request, response: Response, historyid: int, authorization: str = Header(None)):
    """Deletes a specific row of user ban history with historyid, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user/ban/history', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["administrator", "ban_users"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT historyid FROM ban_history WHERE historyid = {historyid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error":  ml.tr(request, "ban_history_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM ban_history WHERE historyid = {historyid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_user(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Deletes a specific user, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    auth_uid = au["uid"]
    if uid == auth_uid:
        uid = -1

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if uid != -1:
        au = await auth(authorization, request, required_permission = ["administrator", "delete_users"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au

        await app.db.execute(dhrid, f"SELECT userid, name, discordid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        (userid, username, discordid) = (t[0][0], t[0][1], t[0][2])
        if userid not in [-1, None]:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_delete", force_lang = au["language"])}

        await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM pending_user_deletion WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await DeleteRoleConnection(request, discordid)
        await AuditLog(request, au["uid"], ml.ctr(request, "deleted_user", var = {"username": username, "uid": uid}))

        return Response(status_code=204)

    else:
        uid = auth_uid

        await app.db.execute(dhrid, f"SELECT userid, name, discordid, mfa_secret FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        (userid, username, discordid, mfa_secret) = (t[0][0], t[0][1], t[0][2], t[0][3])
        if userid not in [-1, None]:
            response.status_code = 428
            return {"error": ml.tr(request, "resign_before_delete", force_lang = au["language"])}

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

        await app.db.execute(dhrid, f"INSERT INTO pending_user_deletion VALUES ({uid}, {int(time.time()+86400*14)}, 1)")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await DeleteRoleConnection(request, discordid)
        await AuditLog(request, uid, ml.ctr(request, "deleted_user_pending", var = {"username": username, "uid": uid}))

        return Response(status_code=204)

async def patch_note_global(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Updates the global note of a user, returns 204

    JSON: `{"note": str}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/{uid}/note/global', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    to_uid = uid

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "update_global_note"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        note = str(data["note"])
        if len(note) > 1000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "bio", "limit": "1,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT name FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    name = t[0][0]

    await app.db.execute(dhrid, f"DELETE FROM user_note WHERE from_uid = -1000 AND to_uid = {to_uid}")
    if note != "":
        await app.db.execute(dhrid, f"INSERT INTO user_note VALUES (-1000, {to_uid}, '{convertQuotation(note)}', {int(time.time())})")
    await app.db.commit(dhrid)
    await AuditLog(request, au["uid"], ml.ctr(request, "updated_global_note", var = {"username": name, "uid": uid, "note": note}))

    return Response(status_code=204)
