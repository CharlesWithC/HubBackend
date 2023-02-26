# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import math
import time
import traceback
from datetime import datetime
from typing import Optional

from aiohttp import ClientSession
from discord import Embed, Webhook
from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *

application_types = config.application_types
to_delete = []
for i in range(len(application_types)):
    try:
        application_types[i]["id"] = int(application_types[i]["id"])
    except:
        to_delete.append(i)
for i in to_delete[::-1]:
    application_types.remove(i)

# Basic Info
@app.get(f"/{config.abbr}/application/types")
async def getApplicationTypes(request: Request, response: Response):
    APPLICATIONS_TYPES = []
    for t in application_types:
        APPLICATIONS_TYPES.append({"applicationid": str(t["id"]), "name": t["name"]})
    return {"error": False, "response": APPLICATIONS_TYPES}

@app.get(f"/{config.abbr}/application/positions")
async def getApplicationPositions(request: Request, response: Response):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return {"error": False, "response": []}
    else:
        ret = []
        for tt in t[0][0].split(","):
            ret.append(tt)
        return {"error": False, "response": ret}

# Get Application
@app.get(f"/{config.abbr}/application")
async def getApplication(request: Request, response: Response, authorization: str = Header(None), applicationid: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /application', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found", force_lang = au["language"])}

    application_type = t[0][1]
    
    isAdmin = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True

    if not isAdmin and discordid != t[0][2]:
        ok = False
        for tt in application_types:
            if str(tt["id"]) == str(application_type):
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": "Forbidden"}

    return {"error": False, "response": {"application": {"applicationid": str(t[0][0]), \
        "detail": json.loads(decompress(t[0][3])), "creator": await getUserInfo(dhrid, discordid = t[0][2]), \
        "application_type": str(t[0][1]), "status": str(t[0][4]), "submit_timestamp": str(t[0][5]), \
        "update_timestamp": str(t[0][7]), "last_update_staff": await getUserInfo(dhrid, userid = t[0][6])}}}

@app.get(f"/{config.abbr}/application/list")
async def getApplicationList(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, application_type: Optional[int] = 0, \
        all_user: Optional[bool] = False, status: Optional[int] = -1, order: Optional[str] = "desc"):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /application/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    if page <= 0:
        page = 1

    if not order in ["asc", "desc"]:
        order = "asc"
    order = order.upper()
        
    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    roles = au["roles"]
    await activityUpdate(dhrid, au["discordid"], f"applications")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 100:
        page_size = 100

    t = None
    tot = 0
    if all_user == False:
        limit = ""
        if application_type != 0:
            limit = f" AND application_type = {application_type} "

        if status != -1 and status in [0,1,2]:
            limit += f" AND status = {status} "

        await aiosql.execute(dhrid, f"SELECT applicationid, application_type, discordid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application WHERE discordid = {discordid} {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = await aiosql.fetchall(dhrid)
        
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application WHERE discordid = {discordid} {limit}")
        p = await aiosql.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]
    else:
        isAdmin = False
        for i in roles:
            if int(i) in config.perms.admin:
                isAdmin = True
        
        allowed_application_types = []
        if not isAdmin:
            for tt in application_types:
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        allowed_application_types.append(str(tt["id"]))
                        break
        else:
            for tt in application_types:
                allowed_application_types.append(str(tt["id"]))

        if len(allowed_application_types) == 0:
            response.status_code = 403
            return {"error": True, "descriptor": "Forbidden"}

        limit = ""
        if application_type == 0: # show all type
            limit = " WHERE ("
            for tt in allowed_application_types:
                limit += f"application_type = {tt} OR "
            limit = limit[:-3]
            limit += ")"
        else:
            if not str(application_type) in allowed_application_types:
                response.status_code = 403
                return {"error": True, "descriptor": "Forbidden"}
            limit = f" WHERE application_type = {application_type} "
        
        if status != -1 and status in [0,1,2]:
            if not "WHERE" in limit:
                limit = f" WHERE status = {status} "
            else:
                limit += f" AND status = {status} "

        await aiosql.execute(dhrid, f"SELECT applicationid, application_type, discordid, submit_timestamp, status, update_staff_timestamp, update_staff_userid FROM application {limit} ORDER BY applicationid {order} LIMIT {(page-1) * page_size}, {page_size}")
        t = await aiosql.fetchall(dhrid)
        
        await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM application {limit}")
        p = await aiosql.fetchall(dhrid)
        if len(t) > 0:
            tot = p[0][0]

    ret = []
    for tt in t:
        ret.append({"applicationid": str(tt[0]), "creator": await getUserInfo(dhrid, discordid = tt[2]), "application_type": str(tt[1]), \
                "status": str(tt[4]), "submit_timestamp": str(tt[3]), "update_timestamp": str(tt[5]), \
                    "last_update_staff": await getUserInfo(dhrid, userid = tt[6])})

    return {"error": False, "response": {"list": ret, "total_items": str(tot), "total_pages": str(int(math.ceil(tot / page_size)))}}

# Self-operation
@app.post(f"/{config.abbr}/application")
async def postApplication(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /application', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]

    form = await request.form()
    try:
        application_type = int(form["application_type"])
        data = json.loads(form["data"])
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    application_type_text = ""
    applicantrole = 0
    discord_message_content = ""
    webhookurl = ""
    note = ""
    for o in application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            applicantrole = o["discord_role_id"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
            note = o["note"]
    if application_type_text == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if note == "driver":
        await aiosql.execute(dhrid, f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = await aiosql.fetchall(dhrid)
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        for r in config.perms.driver:
            if str(r) in roles:
                response.status_code = 409
                return {"error": True, "descriptor": ml.tr(request, "already_a_driver", force_lang = au["language"])}
        await aiosql.execute(dhrid, f"SELECT * FROM application WHERE application_type = 1 AND discordid = {discordid} AND status = 0")
        p = await aiosql.fetchall(dhrid)
        if len(p) > 0:
            response.status_code = 409
            return {"error": True, "descriptor": ml.tr(request, "already_driver_application", force_lang = au["language"])}

    if note == "division":
        await aiosql.execute(dhrid, f"SELECT roles FROM user WHERE discordid = '{discordid}'")
        p = await aiosql.fetchall(dhrid)
        roles = p[0][0].split(",")
        while "" in roles:
            roles.remove("")
        ok = False
        for r in config.perms.driver:
            if str(r) in roles:
                ok = True
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": ml.tr(request, "must_be_driver_to_submit_division_application", force_lang = au["language"])}        

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE discordid = {discordid} AND submit_timestamp >= {int(time.time()) - 7200}")
    p = await aiosql.fetchall(dhrid)
    if len(p) > 0:
        response.status_code = 429
        return {"error": True, "descriptor": ml.tr(request, "no_multiple_application_2h", force_lang = au["language"])}

    if userid == -1 and application_type == 3:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "no_loa_application", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    if t[0][4] <= 0:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "must_verify_steam", force_lang = au["language"])}
    if t[0][3] <= 0 and config.truckersmp_bind:
        response.status_code = 428
        return {"error": True, "descriptor": ml.tr(request, "must_verify_truckersmp", force_lang = au["language"])}
    userid = t[0][5]

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtappid' FOR UPDATE")
    t = await aiosql.fetchall(dhrid)
    applicationid = int(t[0][0])
    await aiosql.execute(dhrid, f"UPDATE settings SET sval = {applicationid+1} WHERE skey = 'nxtappid'")
    await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"INSERT INTO application VALUES ({applicationid}, {application_type}, {discordid}, '{compress(json.dumps(data,separators=(',', ':')))}', 0, {int(time.time())}, -1, 0)")
    await aiosql.commit(dhrid)

    if applicantrole != 0 and config.discord_bot_token != "":
        try:
            r = await arequests.put(f'https://discord.com/api/v10/guilds/{config.guild_id}/members/{discordid}/roles/{applicantrole}', headers = {"Authorization": f"Bot {config.discord_bot_token}", "X-Audit-Log-Reason": "Automatic role changes when user submits application."}, dhrid = dhrid)
            if r.status_code == 401:
                DisableDiscordIntegration()
            if r.status_code // 100 != 2:
                err = json.loads(r.text)
                await AuditLog(dhrid, -998, f'Error `{err["code"]}` when adding <@&{applicantrole}> to <@!{discordid}>: `{err["message"]}`')
        except:
            traceback.print_exc()

    language = await GetUserLanguage(dhrid, discordid)
    await notification(dhrid, "application", discordid, ml.tr(request, "application_submitted", \
            var = {"application_type": application_type_text, "applicationid": applicationid}, force_lang = language), \
        discord_embed = {"title": ml.tr(request, "application_submitted_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": ml.tr(request, "pending", force_lang = language), "inline": True}]})

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid, userid FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    for d in data.keys():
        msg += f"**{d}**:\n{data[d]}\n\n"

    if webhookurl != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = Embed(title = f"New {application_type_text} Application", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = Embed(title = f"New {application_type_text} Application", description = "*Message too long, please view application on website.*", color = config.rgbcolor)
                    if t[0][1].startswith("a_"):
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                    else:
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                    embed.set_footer(text = f"Application ID: {applicationid} ")
                    embed.timestamp = datetime.now()
                    await webhook.send(content = discord_message_content, embed = embed)
            except:
                traceback.print_exc()

    return {"error": False, "response": {"applicationid": str(applicationid)}}

@app.patch(f"/{config.abbr}/application")
async def updateApplication(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /application', 180, 10)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    discordid = au["discordid"]
    userid = au["userid"]
    name = au["name"]

    form = await request.form()
    try:
        applicationid = int(form["applicationid"])
        message = str(form["message"])
        if len(form["message"]) > 2000:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT discordid, data, status, application_type FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if discordid != t[0][0]:
        response.status_code = 403
        return {"error": True, "descriptor": ml.tr(request, "not_applicant", force_lang = au["language"])}
    if t[0][2] != 0:
        response.status_code = 409
        if t[0][2] == 1:
            return {"error": True, "descriptor": ml.tr(request, "application_already_accepted", force_lang = au["language"])}
        elif t[0][2] == 2:
            return {"error": True, "descriptor": ml.tr(request, "application_already_declined", force_lang = au["language"])}
        else:
            return {"error": True, "descriptor": ml.tr(request, "application_already_processed", force_lang = au["language"])}

    discordid = t[0][0]
    data = json.loads(decompress(t[0][1]))
    application_type = t[0][3]
    i = 1
    while 1:
        if not f"[Message] {name} ({userid}) #{i}" in data.keys():
            break
        i += 1
        
    data[f"[Message] {name} ({userid}) #{i}"] = message

    await aiosql.execute(dhrid, f"UPDATE application SET data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"SELECT name, avatar, email, truckersmpid, steamid FROM user WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    msg = f"**Applicant**: <@{discordid}> (`{discordid}`)\n**Email**: {t[0][2]}\n**User ID**: {userid}\n**TruckersMP ID**: [{t[0][3]}](https://truckersmp.com/user/{t[0][3]})\n**Steam ID**: [{t[0][4]}](https://steamcommunity.com/profiles/{t[0][4]})\n\n"
    msg += f"**New message**: \n{message}\n\n"

    application_type_text = ""
    discord_message_content = ""
    webhookurl = ""
    for o in application_types:
        if application_type == o["id"]:
            application_type_text = o["name"]
            discord_message_content = o["message"]
            webhookurl = o["webhook"]
    if application_type < 1 and application_type > 4 and application_type_text == "":
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "unknown_application_type", force_lang = au["language"])}

    if webhookurl != "":
        try:
            async with ClientSession() as session:
                webhook = Webhook.from_url(webhookurl, session=session)

                embed = Embed(title = f"Application #{applicationid} - New Message", description = msg, color = config.rgbcolor)
                if t[0][1].startswith("a_"):
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                else:
                    embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                embed.set_footer(text = f"Application ID: {applicationid} ")
                embed.timestamp = datetime.now()
                await webhook.send(content = discord_message_content, embed = embed)

        except:
            try:
                async with ClientSession() as session:
                    webhook = Webhook.from_url(webhookurl, session=session)

                    embed = Embed(title = f"Application #{applicationid} - New Message", description = "*Data too long, please view application on website.*", color = config.rgbcolor)
                    if t[0][1].startswith("a_"):
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.gif")
                    else:
                        embed.set_author(name = t[0][0], icon_url = f"https://cdn.discordapp.com/avatars/{discordid}/{t[0][1]}.png")
                    embed.set_footer(text = f"Application ID: {applicationid} ")
                    embed.timestamp = datetime.now()
                    await webhook.send(content = discord_message_content, embed = embed)
            except:
                traceback.print_exc()

    return {"error": False}

# Management
@app.patch(f"/{config.abbr}/application/status")
async def updateApplicationStatus(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /application/status', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, check_member = False)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    admindiscord = au["discordid"]
    adminid = au["userid"]
    adminname = au["name"]
    roles = au["roles"]

    form = await request.form()
    try:
        applicationid = int(form["applicationid"])
        status = int(form["status"])
        message = str(form["message"])
        if len(form["message"]) > 2000:
            response.status_code = 400
            return {"error": True, "descriptor": ml.tr(request, "content_too_long", var = {"item": "message", "limit": "2,000"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": True, "descriptor": ml.tr(request, "bad_form", force_lang = au["language"])}
    STATUS = {0: "pending", 1: "accepted", 2: "declined"}
    statustxt = f"N/A"
    if int(status) in STATUS.keys():
        statustxt = STATUS[int(status)]

    if int(applicationid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM application WHERE applicationid = {applicationid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "application_not_found", force_lang = au["language"])}
    
    application_type = t[0][1]
    applicant_discordid = t[0][2]

    language = await GetUserLanguage(dhrid, applicant_discordid)
    STATUSTR = {0: ml.tr(request, "pending", force_lang = language), 1: ml.tr(request, "accepted", force_lang = language),
        2: ml.tr(request, "declined", force_lang = language)}
    statustxtTR = STATUSTR[int(status)]

    isAdmin = False
    for i in roles:
        if int(i) in config.perms.admin:
            isAdmin = True

    if not isAdmin:
        ok = False
        for tt in application_types:
            if str(tt["id"]) == str(application_type):
                allowed_roles = tt["staff_role_id"]
                for role in allowed_roles:
                    if str(role) in roles:
                        ok = True
                        break
        if not ok:
            response.status_code = 403
            return {"error": True, "descriptor": "Forbidden"}

    discordid = t[0][2]
    data = json.loads(decompress(t[0][3]))
    i = 1
    while 1:
        if not f"[Message] {adminname} ({adminid}) #{i}" in data.keys():
            break
        i += 1
    if message != "":
        data[f"[Message] {adminname} ({adminid}) #{i}"] = message

    update_timestamp = 0
    if status != 0:
        update_timestamp = int(time.time())

    await aiosql.execute(dhrid, f"UPDATE application SET status = {status}, update_staff_userid = {adminid}, update_staff_timestamp = {update_timestamp}, data = '{compress(json.dumps(data,separators=(',', ':')))}' WHERE applicationid = {applicationid}")
    await AuditLog(dhrid, adminid, f"Updated application `#{applicationid}` status to `{statustxt}`")
    await notification(dhrid, "application", applicant_discordid, ml.tr(request, "application_status_updated", var = {"applicationid": applicationid, "status": statustxtTR.lower()}, force_lang = await GetUserLanguage(dhrid, discordid, "en")), \
        discord_embed = {"title": ml.tr(request, "application_status_updated_title", force_lang = language), "description": "", \
            "fields": [{"name": ml.tr(request, "application_id", force_lang = language), "value": f"{applicationid}", "inline": True}, \
                       {"name": ml.tr(request, "status", force_lang = language), "value": statustxtTR, "inline": True}]})
    await aiosql.commit(dhrid)

    if message == "":
        message = f"*{ml.tr(request, 'no_message')}*"

    return {"error": False}

# Higher-management
@app.patch(f"/{config.abbr}/application/positions")
async def patchApplicationPositions(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /application/positions', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, required_permission = ["admin", "hrm", "update_application_positions"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]

    form = await request.form()
    positions = convert_quotation(form["positions"])

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'applicationpositions'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO settings VALUES (0, 'applicationpositions', '{positions}')")
    else:
        await aiosql.execute(dhrid, f"UPDATE settings SET sval = '{positions}' WHERE skey = 'applicationpositions'")
    await aiosql.commit(dhrid)

    await AuditLog(dhrid, adminid, f"Updated staff positions to: `{positions}`")

    return {"error": False}