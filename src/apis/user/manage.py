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

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "add_member"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "banned_user_cannot_be_accepted", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"SELECT userid, name, discordid, name, steamid, truckersmpid, email FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    if t[0][0] != -1:
        response.status_code = 409
        return {"error": ml.tr(request, "user_is_already_member", force_lang = au["language"])}
    name = t[0][1]
    discordid = t[0][2]
    username = t[0][3]
    steamid = t[0][4]
    truckersmpid = t[0][5]
    email = t[0][6]
    if email == "" and "email" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "email"}, force_lang = au["language"])}
    if discordid is None and "discord" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Discord"}, force_lang = au["language"])}
    if steamid is None and "steam" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "Steam"}, force_lang = au["language"])}
    if truckersmpid is None and "truckersmp" in app.config.required_connections:
        response.status_code = 428
        return {"error": ml.tr(request, "connection_invalid", var = {"app": "TruckersMP"}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
    t = await app.db.fetchall(dhrid)
    userid = int(t[0][0])

    await app.db.execute(dhrid, f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE uid = {uid}")
    await app.db.execute(dhrid, f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(request, au["uid"], ml.ctr(request, "accepted_user_as_member", var = {"username": name, "userid": userid, "uid": uid}))
    await app.db.commit(dhrid)

    await notification(request, "member", uid, ml.tr(request, "member_accepted", var = {"userid": userid}, force_lang = await GetUserLanguage(request, uid)))
    
    def setvar(msg):
        return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid))

    if app.config.member_accept.webhook_url != "" or app.config.member_accept.channel_id != "":
        meta = app.config.member_accept
        await AutoMessage(app, meta, setvar)
    
    if app.config.member_welcome.webhook_url != "" or app.config.member_welcome.channel_id != "":
        meta = app.config.member_welcome
        await AutoMessage(app, meta, setvar)

    return {"userid": userid}   

async def patch_discord(request: Request, response: Response, uid: int,  authorization: str = Header(None)):
    """[Permission Control] Updates Discord account connection for a specific user, returns 204
    
    JSON: `{"discord_id": int}`"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /user/discord', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin", "hrm", "update_user_discord"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if not (await isSecureAuth(authorization, request)):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    data = await request.json()
    try:
        new_discord_id = int(data["discordid"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"SELECT uid, name FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    old_uid = t[0][0]
    name = t[0][1]

    await app.db.execute(dhrid, f"SELECT uid, userid FROM user WHERE discordid = {new_discord_id}")
    t = await app.db.fetchall(dhrid)
    if len(t) >= 0:
        # delete account of new discord, and both sessions
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {old_uid}")
        await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {old_uid}")
        await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {old_uid}")

        # an account exists with the new discordid
        if len(t) > 0:
            if t[0][1] != -1:
                response.status_code = 409
                return {"error": ml.tr(request, "new_discord_user_must_not_be_member", force_lang = au["language"])}
            new_uid = t[0][0]

            await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {new_uid}")
            await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {new_uid}")

    # update discord binding
    await app.db.execute(dhrid, f"UPDATE user SET discordid = {new_discord_id} WHERE uid = {old_uid}")
    await app.db.commit(dhrid)

    await AuditLog(request, au["uid"], ml.ctr(request, "updated_user_discord", var = {"username": name, "uid": old_uid, "discordid": new_discord_id}))

    return Response(status_code=204)
    
async def delete_connections(request: Request, response: Response, uid: Optional[int] = None, authorization: str = Header(None)):
    """[Permission Control] Deletes all Steam & TruckersMP connection for a specific user.
    
    [Note] This function will be updated when the user system no longer relies on Discord."""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user/connections', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin", "hrm", "delete_account_connections"])
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
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": ml.tr(request, "dismiss_before_delete_connections", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"UPDATE user SET steamid = NULL, truckersmpid = NULL WHERE uid = {uid}")
    await app.db.commit(dhrid)

    username = (await GetUserInfo(request, uid = uid))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_connections", var = {"username": username, "uid": uid}))

    return Response(status_code=204)

async def put_ban(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Bans a specific user, returns 204
    
    JSON: {"expire": int, "reason": str}"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PUT /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    data = await request.json()
    try:
        expire = nint(data["expire"])
        reason = convertQuotation(data["reason"])
        if len(reason) > 256:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "reason", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if expire <= 0:
        expire = 253402272000

    await app.db.execute(dhrid, f"SELECT userid, name, email, discordid, steamid, truckersmpid FROM user WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    username = ml.ctr(request, "unknown_user")
    email = ""
    discordid = "NULL"
    steamid = "NULL"
    truckersmpid = "NULL"
    if len(t) > 0:
        userid = t[0][0]
        username = t[0][1]
        email = t[0][2] if t[0][2] is not None else "NULL"
        discordid = t[0][3] if t[0][3] is not None else "NULL"
        steamid = t[0][4] if t[0][4] is not None else "NULL"
        truckersmpid = t[0][5] if t[0][5] is not  None else "NULL"
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_ban", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        await app.db.execute(dhrid, f"INSERT INTO banned VALUES ({uid}, '{email}', {discordid}, {steamid}, {truckersmpid}, {expire}, '{reason}')")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.commit(dhrid)
        duration = ml.ctr(request, "forever")
        if expire != 253402272000:
            duration = ml.ctr(request, "until", var = {"datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))})
        await AuditLog(request, au["uid"], ml.ctr(request, "banned_user", var = {"username": username, "uid": uid, "duration": duration}))
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "user_already_banned", force_lang = au["language"])}

async def delete_ban(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Unbans a specific user, returns 204"""
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    
    await app.db.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 409
        return {"error": ml.tr(request, "user_not_banned", force_lang = au["language"])}
    else:
        await app.db.execute(dhrid, f"DELETE FROM banned WHERE uid = {uid}")
        await app.db.commit(dhrid)
        
        username = (await GetUserInfo(request, uid = uid))["name"]
        await AuditLog(request, au["uid"], ml.ctr(request, "unbanned_user", var = {"username": username, "uid": uid}))
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
        au = await auth(authorization, request, required_permission = ["admin", "hrm", "delete_user"])
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
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_delete", force_lang = au["language"])}
        
        await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await UpdateRoleConnection(request, discordid)
        await AuditLog(request, au["uid"], ml.ctr(request, "deleted_user", var = {"username": username, "uid": uid}))

        return Response(status_code=204)
    
    else:
        uid = auth_uid
        
        await app.db.execute(dhrid, f"SELECT userid, name, discordid FROM user WHERE uid = {uid}")
        t = await app.db.fetchall(dhrid)
        (userid, username, discordid) = (t[0][0], t[0][1], t[0][2])
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "resign_before_delete", force_lang = au["language"])}
        
        await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await app.db.commit(dhrid)

        await UpdateRoleConnection(request, discordid)
        await AuditLog(request, uid, ml.ctr(request, "deleted_user", var = {"username": username, "uid": uid}))

        return Response(status_code=204)