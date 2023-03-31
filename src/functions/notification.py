# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import json
import threading
import time
import traceback
from datetime import datetime

import requests

import multilang as ml
from app import config
from db import aiosql, genconn
from functions.dataop import *
from functions.general import *
from functions.userinfo import *
from functions.arequests import *
from static import *

discord_message_queue = []

def QueueDiscordMessage(channelid, data):
    global discord_message_queue
    if config.discord_bot_token == "":
        return
    discord_message_queue.append((channelid, data))

def ProcessDiscordMessage(): # thread
    global discord_message_queue
    global config
    lastRLAclear = 0
    headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
    while 1:
        try:
            # combined thread
            try:
                if time.time() - lastRLAclear > 30:
                    conn = genconn()
                    cur = conn.cursor()
                    cur.execute(f"DELETE FROM ratelimit WHERE first_request_timestamp <= {round(time.time() - 3600)}")
                    cur.execute(f"DELETE FROM ratelimit WHERE endpoint = '429-error' AND first_request_timestamp <= {round(time.time() - 60)}")
                    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
                    cur.execute(f"SELECT uid FROM user WHERE email = 'pending' AND join_timestamp < {int(time.time() - 86400)}")
                    t = cur.fetchall()
                    for tt in t:
                        uid = tt[0]
                        cur.execute(f"DELETE FROM user WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM email_confirmation WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM user_password WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM user_activity WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM user_notification WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM session WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM auth_ticket WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM application_token WHERE uid = {uid}")
                        cur.execute(f"DELETE FROM settings WHERE uid = {uid}")
                    lastRLAclear = time.time()
                    conn.commit()
                    cur.close()
                    conn.close()
            except:
                pass

            if config.discord_bot_token == "":
                return
            if len(discord_message_queue) == 0:
                time.sleep(1)
                continue
            
            # get first in queue
            channelid = discord_message_queue[0][0]
            data = discord_message_queue[0][1]

            # see if there's any more embed to send to the channel
            to_delete = [0]
            for i in range(1, len(discord_message_queue)):
                (chnid, d) = discord_message_queue[i]
                if chnid == channelid and \
                        not "content" in d.keys() and "embeds" in d.keys():
                    # not a text message but a rich embed
                    if len(str(data["embeds"])) + len(str(d["embeds"])) > 5000:
                        break # make sure this will not exceed character limit
                    for j in range(len(d["embeds"])):
                        data["embeds"].append(d["embeds"][j])
                    to_delete.append(i)

            try:
                r = requests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", \
                    headers=headers, data=json.dumps(data))
            except:
                traceback.print_exc()
                time.sleep(5)
                continue

            if r.status_code == 429:
                d = json.loads(r.text)
                time.sleep(d["retry_after"])
            elif r.status_code == 403:
                conn = genconn()
                cur = conn.cursor()
                cur.execute(f"SELECT uid FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")
                t = cur.fetchall()
                if len(t) != 0:
                    uid = t[0][0]
                    cur.execute(f"DELETE FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")
                    
                    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}
                    settingsok = False

                    cur.execute(f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
                    t = cur.fetchall()
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
                        cur.execute(f"UPDATE settings SET sval = '{res}' WHERE uid = {uid} AND skey = 'notification'")
                    else:
                        cur.execute(f"INSERT INTO settings VALUES ('{uid}', 'notification', '{res}')")
                conn.commit()
                cur.close()
                conn.close()
                for i in to_delete[::-1]:
                    discord_message_queue.pop(i)
            elif r.status_code == 401:
                DisableDiscordIntegration()
                return
            elif r.status_code == 200 or r.status_code >= 400 and r.status_code <= 499:
                for i in to_delete[::-1]:
                    discord_message_queue.pop(i)

            time.sleep(1)
            
        except:
            traceback.print_exc()
            time.sleep(1)

threading.Thread(target=ProcessDiscordMessage, daemon = True).start()

async def CheckDiscordNotification(dhrid, uid):
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'discord-notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return False
    ret = t[0][0]
    if ret == "disabled":
        return False
    return ret

async def SendDiscordNotification(dhrid, uid, data):
    t = await CheckDiscordNotification(dhrid, uid)
    if t == False:
        return
    QueueDiscordMessage(t, data)

async def CheckNotificationEnabled(dhrid, notification_type, uid):
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return False
    return True

async def notification(dhrid, notification_type, uid, content, no_drivershub_notification = False, \
        no_discord_notification = False, discord_embed = {}):
    if uid is None or int(uid) <= 0:
        return
    
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = {uid} AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return

    if settings["drivershub"] and not no_drivershub_notification:
        await aiosql.execute(dhrid, f"INSERT INTO user_notification(uid, content, timestamp, status) VALUES ({uid}, '{convertQuotation(content)}', {int(time.time())}, 0)")
        await aiosql.commit(dhrid)
    
    if settings["discord"] and not no_discord_notification:
        if discord_embed != {}:
            await SendDiscordNotification(dhrid, uid, {"embeds": [{"title": discord_embed["title"], 
                "description": discord_embed["description"], "fields": discord_embed["fields"], "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.int_color}]})
        else:
            await SendDiscordNotification(dhrid, uid, {"embeds": [{"title": ml.tr(None, "notification", force_lang = await GetUserLanguage(dhrid, uid)), 
                "description": content, "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.int_color}]})

async def AuditLog(dhrid, uid, text, discord_message_only = False):
    try:
        name = ml.ctr("unknown_user")
        avatar = ""
        if uid == -999:
            name = ml.ctr("system")
        elif uid == -998:
            name = ml.ctr("discord_api")
        else:
            await aiosql.execute(dhrid, f"SELECT name, avatar FROM user WHERE uid = {uid}")
            t = await aiosql.fetchall(dhrid)
            if len(t) > 0:
                name = t[0][0]
                avatar = t[0][1]
        if uid != -998 and not discord_message_only:
            await aiosql.execute(dhrid, f"INSERT INTO auditlog VALUES ({uid}, '{convertQuotation(text)}', {int(time.time())})")
            await aiosql.commit(dhrid)
        if config.webhook_audit != "":
            footer = {"text": name}
            if uid not in [-999, -998]:
                footer = {"text": f"{name} (ID {uid})", "icon_url": avatar}
            try:
                r = await arequests.post(config.webhook_audit, data=json.dumps({"embeds": [{"description": text, "footer": footer, "timestamp": str(datetime.now()), "color": config.int_color}]}), headers = {"Content-Type": "application/json"})
                if r.status_code == 401:
                    DisableDiscordIntegration()
            except:
                traceback.print_exc()
    except:
        traceback.print_exc()

async def AutoMessage(meta, setvar):
    global config
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
                "color": config.int_color
            }]})
        
        if meta.webhook_url != "":
            r = await arequests.post(meta.webhook_url, headers={"Content-Type": "application/json"}, data=data)
            if r.status_code == 401:
                DisableDiscordIntegration()

        elif meta.channel_id != "":
            if config.discord_bot_token == "":
                return

            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v10/channels/{meta.channel_id}/messages"
            r = await arequests.post(ddurl, headers=headers, data=data)
            if r.status_code == 401:
                DisableDiscordIntegration()
    except:
        traceback.print_exc()