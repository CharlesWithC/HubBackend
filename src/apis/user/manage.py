# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions.main import *

@app.post(f'/{config.abbr}/user/{{uid}}/accept')
async def post_user_accept(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """[Permission Control] Accepts a user as member, assign userid, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /user/accept', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "hrm", "hr", "add_member"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    await aiosql.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "banned_user_cannot_be_accepted", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid, name, discordid, name FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    if t[0][0] != -1:
        response.status_code = 409
        return {"error": ml.tr(request, "already_member", force_lang = au["language"])}
    name = t[0][1]
    discordid = t[0][2]
    username = t[0][3]

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtuserid' FOR UPDATE")
    t = await aiosql.fetchall(dhrid)
    userid = int(t[0][0])

    await aiosql.execute(dhrid, f"UPDATE user SET userid = {userid}, join_timestamp = {int(time.time())} WHERE uid = {uid}")
    await aiosql.execute(dhrid, f"UPDATE settings SET sval = {userid+1} WHERE skey = 'nxtuserid'")
    await AuditLog(dhrid, adminid, f'Added member: `{name}` (User ID: `{userid}` | UID: `{uid}`)')
    await aiosql.commit(dhrid)

    await notification(dhrid, "member", uid, ml.tr(request, "member_accepted", var = {"userid": userid}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
    
    def setvar(msg):
        return msg.replace("{mention}", f"<@{discordid}>").replace("{name}", username).replace("{userid}", str(userid)).replace("{uid}", str(uid))

    if config.member_accept.webhook_url != "" or config.member_accept.channel_id != "":
        meta = config.member_accept
        await AutoMessage(meta, setvar)
    
    if config.member_welcome.webhook_url != "" or config.member_welcome.channel_id != "":
        meta = config.member_welcome
        await AutoMessage(meta, setvar)

    return {"userid": userid}   

@app.patch(f"/{config.abbr}/user/{{uid}}/discord")
async def patch_user_discord(request: Request, response: Response, uid: int,  authorization: str = Header(None)):
    """[Permission Control] Updates Discord account connection for a specific user, returns 204
    
    JSON: `{"discord_id": int}`
    
    [DEPRECATED] This function will be moved or removed when the user system no longer relies on Discord."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PATCH /user/discord', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "update_user_discord"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    data = await request.json()
    try:
        new_discord_id = int(data["discordid"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT uid, name FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    old_uid = t[0][0]
    name = t[0][1]

    await aiosql.execute(dhrid, f"SELECT uid, userid FROM user WHERE discordid = {new_discord_id}")
    t = await aiosql.fetchall(dhrid)
    if len(t) >= 0:
        # delete account of new discord, and both sessions
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {old_uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {old_uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {old_uid}")

        # an account exists with the new discordid
        if len(t) > 0:
            if t[0][1] != -1:
                response.status_code = 409
                return {"error": ml.tr(request, "user_must_not_be_member", force_lang = au["language"])}
            new_uid = t[0][0]

            await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {new_uid}")
            await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {new_uid}")

    # update discord binding
    await aiosql.execute(dhrid, f"UPDATE user SET discordid = {new_discord_id} WHERE uid = {old_uid}")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Updated Discord ID of `{name}` (UID: `{old_uid}`) to `{new_discord_id}`")

    return Response(status_code=204)
    
@app.delete(f"/{config.abbr}/user/{{uid}}/connections")
async def delete_user_connections(request: Request, response: Response, uid: Optional[int] = -1, authorization: str = Header(None)):
    """[Permission Control] Deletes all third-party account connections (except Discord) for a specific user.
    
    [Note] This function will be updated when the user system no longer relies on Discord."""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /user/connections', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "delete_account_connections"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"SELECT userid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
    userid = t[0][0]
    if userid != -1:
        response.status_code = 428
        return {"error": ml.tr(request, "dismiss_before_unbind", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE user SET steamid = NULL, truckersmpid = NULL WHERE uid = {uid}")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
    await AuditLog(dhrid, adminid, f"Deleted connections of `{username}` (UID: `{uid}`)")

    return Response(status_code=204)

@app.put(f'/{config.abbr}/user/{{uid}}/ban')
async def put_user_ban(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Bans a specific user, returns 204
    
    JSON: {"expire": int, "reason": str}"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'PUT /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    data = await request.json()
    try:
        expire = int(data["expire"])
        reason = convertQuotation(data["reason"])
        if len(reason) > 256:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "reason", "limit": "256"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if expire == -1:
        expire = 253402272000

    await aiosql.execute(dhrid, f"SELECT userid, name, email, discordid, steamid, truckersmpid FROM user WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    username = "Unknown User"
    email = ""
    discordid = "NULL"
    steamid = "NULL"
    truckersmpid = "NULL"
    if len(t) > 0:
        userid = t[0][0]
        username = t[0][1]
        email = t[0][2]
        discordid = t[0][3]
        steamid = t[0][4]
        truckersmpid = t[0][5]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_ban", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO banned VALUES ({uid}, '{email}', {discordid}, {steamid}, {truckersmpid}, {expire}, '{reason}')")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        duration = "forever"
        if expire != 253402272000:
            duration = f'until `{time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(expire))}` UTC'
        await AuditLog(dhrid, adminid, f"Banned `{username}` (UID: `{uid}`) {duration}.")
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "user_already_banned", force_lang = au["language"])}

@app.delete(f'/{config.abbr}/user/{{uid}}/ban')
async def delete_user_ban(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Unbans a specific user, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /user/ban', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hr", "hrm", "ban_user"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
    
    await aiosql.execute(dhrid, f"SELECT * FROM banned WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 409
        return {"error": ml.tr(request, "user_not_banned", force_lang = au["language"])}
    else:
        await aiosql.execute(dhrid, f"DELETE FROM banned WHERE uid = {uid}")
        await aiosql.commit(dhrid)
        
        username = (await GetUserInfo(dhrid, request, uid = uid))["name"]
        await AuditLog(dhrid, adminid, f"Unbanned `{username}` (UID: `{uid}`)")
        return Response(status_code=204)
   
@app.delete(f"/{config.abbr}/user/{{uid}}")
async def delete_user(request: Request, response: Response, uid: int, authorization: str = Header(None)):
    """Deletes a specific user, returns 204"""

    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'DELETE /user', 60, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    auth_uid = au["uid"]
    if uid == auth_uid:
        uid = -1

    stoken = authorization.split(" ")[1]
    if stoken.startswith("e"):
        response.status_code = 403
        return {"error": ml.tr(request, "access_sensitive_data", force_lang = au["language"])}

    if uid != -1:
        au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "delete_user"])
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        adminid = au["userid"]

        await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        userid = t[0][0]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "dismiss_before_delete", force_lang = au["language"])}
        username = t[0][1]
        
        await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await aiosql.commit(dhrid)

        await AuditLog(dhrid, adminid, f"Deleted account: `{username}` (UID: `{uid}`)")

        return Response(status_code=204)
    
    else:
        uid = auth_uid
        
        await aiosql.execute(dhrid, f"SELECT userid, name FROM user WHERE uid = {uid}")
        t = await aiosql.fetchall(dhrid)
        userid = t[0][0]
        username = t[0][1]
        if userid != -1:
            response.status_code = 428
            return {"error": ml.tr(request, "leave_company_before_delete", force_lang = au["language"])}
        
        await aiosql.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
        await aiosql.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")
        await aiosql.commit(dhrid)

        await AuditLog(dhrid, -999, f"Deleted account: `{username}` (UID: `{uid}`)")

        return Response(status_code=204)