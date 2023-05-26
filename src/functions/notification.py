# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import json
import time
from datetime import datetime

import requests

import multilang as ml
from functions.arequests import *
from functions.dataop import *
from functions.general import *
from functions.userinfo import *
from static import *

# app.state.discord_message_queue = []
# app.state.discord_retry_after = {}

def QueueDiscordMessage(app, channelid, data):
    if app.config.discord_bot_token == "":
        return
    app.state.discord_message_queue.append((channelid, data))

async def ProcessDiscordMessage(app): # thread
    headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
    while 1:
        try:
            if app.config.discord_bot_token == "":
                return
            if len(app.state.discord_message_queue) == 0:
                try:
                    await asyncio.sleep(1)
                except:
                    return
                continue

            # get an available one in queue
            ok = False
            for i in range(len(app.state.discord_message_queue)):
                (channelid, data) = app.state.discord_message_queue[i]
                if channelid not in app.state.discord_retry_after.keys() or\
                    app.state.discord_retry_after[channelid] < time.time():
                    ok = True
                    break

            if not ok:
                try:
                    await asyncio.sleep(1)
                except:
                    return
                continue

            # see if there's any more embed to send to the channel
            to_delete = [0]
            for i in range(1, len(app.state.discord_message_queue)):
                (chnid, d) = app.state.discord_message_queue[i]
                if chnid == channelid and \
                        "content" not in d.keys() and "embeds" in d.keys():
                    # not a text message but a rich embed
                    if len(str(data["embeds"])) + len(str(d["embeds"])) > 5000:
                        break # make sure this will not exceed character limit
                    for j in range(len(d["embeds"])):
                        data["embeds"].append(d["embeds"][j])
                    to_delete.append(i)

            try:
                r = requests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", \
                    headers = headers, data=json.dumps(data))
            except:
                try:
                    await asyncio.sleep(5)
                except:
                    return
                continue

            if r.status_code == 429:
                d = json.loads(r.text)
                if d["global"]:
                    try:
                        await asyncio.sleep(d["retry_after"])
                    except:
                        return
                    continue
                app.state.discord_retry_after[channelid] = time.time() + float(d["retry_after"])

            elif r.status_code == 403:
                dhrid = genrid()
                await app.db.new_conn(dhrid)
                await app.db.execute(dhrid, f"SELECT uid FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")
                t = await app.db.fetchall(dhrid)
                if len(t) != 0:
                    uid = t[0][0]
                    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")

                    settings = NOTIFICATION_SETTINGS
                    settingsok = False

                    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
                    t = await app.db.fetchall(dhrid)
                    if len(t) != 0:
                        settingsok = True
                        d = t[0][0].split(",")
                        for dd in d:
                            if dd in settings.keys():
                                settings[dd] = True
                    settings["discord"] = False

                    res = ""
                    for tt in settings.keys():
                        if settings[tt]:
                            res += tt + ","
                    res = res[:-1]
                    if settingsok:
                        await app.db.execute(dhrid, f"UPDATE settings SET sval = '{res}' WHERE uid = {uid} AND skey = 'notification'")
                    else:
                        await app.db.execute(dhrid, f"INSERT INTO settings VALUES ('{uid}', 'notification', '{res}')")

                await app.db.commit(dhrid)
                await app.db.close_conn(dhrid)

                for i in to_delete[::-1]:
                    app.state.discord_message_queue.pop(i)
            elif r.status_code == 401:
                DisableDiscordIntegration(app)
                return
            elif r.status_code == 200 or r.status_code >= 400 and r.status_code <= 499:
                for i in to_delete[::-1]:
                    app.state.discord_message_queue.pop(i)

        except:
            pass

        try:
            await asyncio.sleep(0.1)
        except:
            return

async def CheckDiscordNotification(request, uid):
    (app, dhrid) = (request.app, request.state.dhrid)
    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'discord-notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return False
    ret = t[0][0]
    if ret == "disabled":
        return False
    return ret

async def SendDiscordNotification(request, uid, data, channelid = None):
    if channelid is False:
        return
    if channelid is None:
        channelid = await CheckDiscordNotification(request, uid)
        if channelid is False:
            return
    QueueDiscordMessage(request.app, channelid, data)

async def CheckNotificationEnabled(request, notification_type, uid):
    if uid is None:
        return False

    (app, dhrid) = (request.app, request.state.dhrid)
    settings = NOTIFICATION_SETTINGS

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return False
    return True

async def notification(request, notification_type, uid, content, no_drivershub_notification = False, \
        no_discord_notification = False, discord_embed = {}, force = False):
    if uid is None or int(uid) < 0 or not notification_type in NOTIFICATION_SETTINGS.keys():
        return

    dhrid = request.state.dhrid
    app = request.app
    settings = NOTIFICATION_SETTINGS

    if not force:
        await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            d = t[0][0].split(",")
            for dd in d:
                if dd in settings.keys():
                    settings[dd] = True

        if not settings[notification_type]:
            return

    if settings["drivershub"] and not no_drivershub_notification:
        await app.db.execute(dhrid, f"INSERT INTO user_notification(uid, content, timestamp, status) VALUES ({uid}, '{convertQuotation(content)}', {int(time.time())}, 0)")
        await app.db.commit(dhrid)

    if settings["discord"] and not no_discord_notification:
        if discord_embed != {}:
            await SendDiscordNotification(request, uid, {"embeds": [{"title": discord_embed["title"], "url": discord_embed["url"] if "url" in discord_embed.keys() else "", "description": discord_embed["description"], "fields": discord_embed["fields"], "footer": {"text": app.config.name, "icon_url": app.config.logo_url} if "footer" not in discord_embed.keys() else discord_embed["footer"], "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]})
        else:
            await SendDiscordNotification(request, uid, {"embeds": [{"title": ml.tr(request, "notification", force_lang = await GetUserLanguage(request, uid)),
                "description": content, "footer": {"text": app.config.name, "icon_url": app.config.logo_url}, \
                "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]})

async def notification_to_everyone(request, notification_type, content, no_drivershub_notification = False, \
        no_discord_notification = False, discord_embed = {}, only_to_members = False):
    if not notification_type in NOTIFICATION_SETTINGS.keys():
        return
    
    dhrid = request.state.dhrid
    app = request.app

    # ensure members get notifications first
    await app.db.execute(dhrid, f"SELECT uid FROM user WHERE userid >= 0")
    t = await app.db.fetchall(dhrid)
    member_uid = []
    for tt in t:
        member_uid.append(tt[0])
    
    priority_dh_uid = []
    priority_dc_uid = []
    regular_dh_uid = []    
    regular_dc_uid = [] 
    await app.db.execute(dhrid, f"SELECT uid, sval FROM settings WHERE skey = 'notification'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return
    for tt in t:
        d = tt[1].split(",")
        if notification_type in d:
            if tt[0] in member_uid:
                if "drivershub" in d:
                    priority_dh_uid.append(tt[0])
                if "discord" in d:
                    priority_dc_uid.append(tt[0])
            elif not only_to_members:
                if "drivershub" in d:
                    regular_dh_uid.append(tt[0])
                if "discord" in d:
                    regular_dc_uid.append(tt[0])
            break

    await app.db.execute(dhrid, f"SELECT uid, sval FROM settings WHERE skey = 'discord-notification'")
    channelids = {}
    t = await app.db.fetchall(dhrid)
    for tt in t:
        channelids[tt[0]] = tt[1]
    
    userlang = {}
    await app.db.execute(dhrid, f"SELECT uid, sval FROM settings WHERE skey = 'language'")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        userlang[tt[0]] = tt[1]
    for uid in priority_dc_uid + priority_dh_uid + regular_dc_uid + regular_dh_uid:
        if not uid in userlang.keys():
            userlang[uid] = app.config.language
    
    if not no_drivershub_notification:
        t = int(time.time())
        for uid in priority_dh_uid + regular_dh_uid:
            c = convertQuotation(ml.hspl(request, content, force_lang=userlang[uid]))
            await app.db.execute(dhrid, f"INSERT INTO user_notification(uid, content, timestamp, status) VALUES ({uid}, '{c}', {t}, 0)")
            await app.db.commit(dhrid)

    if not no_discord_notification:
        data = {}
        for uid in priority_dc_uid + regular_dc_uid:
            if discord_embed != {}:
                fields = []
                if "fields" in discord_embed.keys():
                    for field in discord_embed["fields"]:
                        fields.append({"name": ml.hspl(request, field["name"], force_lang=userlang[uid]), "value": ml.hspl(request, field["value"], force_lang=userlang[uid]), "inline": field["inline"]})
                footer = {"text": ml.hspl(request, discord_embed["footer"]["text"], force_lang=userlang[uid]), "icon_url": discord_embed["footer"]["icon_url"]}
                data = {"embeds": [{"title": ml.hspl(request, discord_embed["title"], force_lang=userlang[uid]), "url": discord_embed["url"] if "url" in discord_embed.keys() else "", "description": ml.hspl(request, discord_embed["description"], force_lang=userlang[uid]), "fields": fields, "footer": {"text": app.config.name, "icon_url": app.config.logo_url} if "footer" not in discord_embed.keys() else footer, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}
            else:
                data = {"embeds": [{"title": ml.tr(request, "notification", force_lang = await GetUserLanguage(request, uid)),
                    "description": content, "footer": {"text": app.config.name, "icon_url": app.config.logo_url}, \
                    "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}
            await SendDiscordNotification(request, uid, data, channelid = channelids[uid] if uid in channelids.keys() else False)

async def AuditLog(request, uid, text, discord_message_only = False):
    try:
        (app, dhrid) = (request.app, request.state.dhrid)
        name = ml.ctr(request, "unknown_user")
        avatar = ""
        if uid == -999:
            name = ml.ctr(request, "system")
        elif uid == -998:
            name = ml.ctr(request, "discord_api")
        else:
            uinfo = await GetUserInfo(request, uid = uid)
            name = uinfo["name"]
            avatar = uinfo["avatar"]
            userid = uinfo["userid"] if uinfo["userid"] is not None else "N/A"
        if uid != -998 and not discord_message_only:
            await app.db.execute(dhrid, f"INSERT INTO auditlog VALUES ({uid}, '{convertQuotation(text)}', {int(time.time())})")
            await app.db.commit(dhrid)
        if app.config.hook_audit_log.channel_id != "" or app.config.hook_audit_log.webhook_url != "":
            try:
                footer = {"text": name}
                if uid not in [-999, -998]:
                    footer = {"text": f"{name} (UID: {uid} | User ID: {userid})", "icon_url": avatar}

                headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}

                if app.config.hook_audit_log.channel_id != "":
                    durl = f"https://discord.com/api/v10/channels/{app.config.hook_audit_log.channel_id}/messages"
                elif app.config.hook_audit_log.webhook_url != "":
                    durl = app.config.hook_audit_log.webhook_url

                r = await arequests.post(app, durl, data=json.dumps({"embeds": [{"description": text, "footer": footer, "timestamp": str(datetime.now()), "color": int(app.config.hex_color, 16)}]}), headers =  headers)
                if r.status_code == 401:
                    DisableDiscordIntegration(app)
            except:
                pass
    except:
        pass

async def AutoMessage(app, meta, setvar):
    try:
        timestamp = ""
        if meta.embed.timestamp:
            timestamp = str(datetime.now())
        data = json.dumps({
            "content": setvar(meta.content),
            "embeds": [{
                "title": setvar(meta.embed.title),
                "description": setvar(meta.embed.description),
                "footer": {
                    "text": setvar(meta.embed.footer.text),
                    "icon_url": setvar(meta.embed.footer.icon_url)
                },
                "image": {
                    "url": setvar(meta.embed.image_url)
                },
                "timestamp": timestamp,
                "color": int(app.config.hex_color, 16)
            }]})

        if meta.channel_id != "":
            if app.config.discord_bot_token == "":
                return

            headers = {"Authorization": f"Bot {app.config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v10/channels/{meta.channel_id}/messages"
            r = await arequests.post(app, ddurl, headers = headers, data=data)
            if r.status_code == 401:
                DisableDiscordIntegration(app)

        elif meta.webhook_url != "":
            r = await arequests.post(app, meta.webhook_url, headers={"Content-Type": "application/json"}, data=data)
            if r.status_code == 401:
                DisableDiscordIntegration(app)

    except:
        pass
