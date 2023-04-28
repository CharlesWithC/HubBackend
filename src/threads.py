# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import copy
import json
import os
import time

from discord_oauth2 import DiscordAuth
from fastapi import Request

import static
from config import validateConfig
from functions.dataop import *
from functions.general import *
from functions.userinfo import DeleteRoleConnection
from logger import logger


async def DetectConfigChanges(app):
    # NOTE Why? When running in multiple workers, app is not synced between workers, hence config cannot be synced
    while 1:
        try:
            if not os.path.exists(app.config_path):
                # just in case
                try:
                    await asyncio.sleep(600)
                except:
                    return
                continue

            if app.config_last_modified != os.path.getmtime(app.config_path):
                # modified
                config_txt = open(app.config_path, "r", encoding="utf-8").read()
                config = validateConfig(json.loads(config_txt))
                config = Dict2Obj(config)
                app.config = config
                app.backup_config = copy.deepcopy(config.__dict__)
                app.config_last_modified = os.path.getmtime(app.config_path)
                logger.info(f"[{app.config.abbr}] [PID: {os.getpid()}] Config modification detected, reloaded config.")
                app = static.load(app)

        except:
            pass

        try:
            await asyncio.sleep(30)
        except:
            return

async def ClearOutdatedData(app):
    while 1:
        # combined thread
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)
            request = Request(scope={"type":"http", "app": app})

            await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE first_request_timestamp <= {round(time.time() - 3600)}")
            await app.db.execute(dhrid, f"DELETE FROM ratelimit WHERE endpoint = '429-error' AND first_request_timestamp <= {round(time.time() - 60)}")
            await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

            await app.db.execute(dhrid, f"SELECT uid, discordid FROM user WHERE email = 'pending' AND join_timestamp < {int(time.time() - 86400)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                uid = tt[0]
                discordid = tt[1]
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

                await DeleteRoleConnection(request, discordid)

            await app.db.execute(dhrid, f"SELECT uid FROM pending_user_deletion WHERE expire_timestamp < {int(time.time())}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                uid = tt[0]
                
                await app.db.execute(dhrid, f"SELECT discordid FROM user WHERE uid = {uid}")
                p = await app.db.fetchall(dhrid)
                if len(p) > 0:
                    discordid = p[0][0]
                    await DeleteRoleConnection(request, discordid)

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
            await app.db.close_conn(dhrid)
        except:
            pass
        
        try:
            await asyncio.sleep(30)
        except:
            return
        
async def RefreshDiscordAccessToken(app):
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)

            npid = -1
            nlup = -1
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'process-discord-refresh-pid'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                npid = int(t[0][0])
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'process-discord-refresh-last-update'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                nlup = int(t[0][0])
            if npid != -1 and npid != os.getpid() and time.time() - nlup <= 600:
                try:
                    await asyncio.sleep(60)
                except:
                    return
                continue
            await app.db.execute(dhrid, "DELETE FROM settings WHERE skey = 'process-discord-refresh-pid' OR skey = 'process-discord-refresh-last-update'")
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES (NULL, 'process-discord-refresh-pid', '{os.getpid()}')")
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES (NULL, 'process-discord-refresh-last-update', '{int(time.time())}')")
            await app.db.commit(dhrid)

            await app.db.execute(dhrid, f"SELECT discordid, callback_url, refresh_token FROM discord_access_token WHERE expire_timestamp <= {int(time.time() + 3600)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                (discordid, callback_url, refresh_token) = (tt[0], tt[1], tt[2])
                await app.db.extend_conn(dhrid, 30)
                discord_auth = DiscordAuth(app.config.discord_client_id, app.config.discord_client_secret, callback_url)
                tokens = discord_auth.refresh_token(refresh_token)
                await app.db.extend_conn(dhrid, 2)
                await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE discordid = {discordid}")
                if "error" in tokens.keys():
                    continue

                (access_token, refresh_token, expire_timestamp) = (convertQuotation(tokens["access_token"]), convertQuotation(tokens["refresh_token"]), tokens["expires_in"] + int(time.time()) - 60)
                await app.db.execute(dhrid, f"INSERT INTO discord_access_token VALUES ({discordid}, '{convertQuotation(callback_url)}', '{access_token}', '{refresh_token}', {expire_timestamp})")

            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)

        except:
            pass

        await asyncio.sleep(600)