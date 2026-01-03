# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import inspect
import json
import time

from fastapi import Request

import multilang as ml
from functions.arequests import arequests
from functions.general import DisableDiscordIntegration


class DiscordAuth:
    def __init__(self, client_id, client_secret, callback_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url

    async def get_tokens(self, code):
        """ Gets the access token from the code given. The code can only be used on an active url (callback url) meaning you can only use the code once. """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': self.callback_url
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        return json.loads(resp.text)

    async def refresh_token(self, refresh_token):
        """ Refreshes access token and access tokens and will return a new set of tokens """
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        resp = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        return json.loads(resp.text)


    async def get_user_data_from_token(self, access_token):
        """ Gets the user data from an access_token """
        headers = {
            "Authorization": f'Bearer {access_token}'
        }

        resp = await arequests.get(None, 'https://discord.com/api/v10/users/@me', headers=headers)
        return json.loads(resp.text)

# app.state.discord_opqueue = []

class opqueue:
    def queue(app, method, key, url, data, headers, error_msg, max_retry = 5):
        for middleware in app.external_middleware["discord_request"]:
            if not inspect.iscoroutinefunction(middleware):
                data = middleware(method = method, url = url, data = data)
        app.state.discord_opqueue.append((method, key, url, data, headers, error_msg, 4 - max_retry))

    async def run(app):
        METHOD_MAP = {"post": arequests.post, "put": arequests.put, "delete": arequests.delete}
        while 1:
            try:
                if len(app.state.discord_opqueue) == 0:
                    try:
                        await asyncio.sleep(1)
                    except:
                        return
                    continue

                # get an available one in queue
                ok = False
                idx = 0
                for i in range(len(app.state.discord_opqueue)):
                    (method, key, url, data, headers, error_msg, retry_count) = app.state.discord_opqueue[i]
                    if key not in app.state.discord_retry_after.keys() or \
                            app.state.discord_retry_after[key] < time.time():
                        ok = True
                        idx = i
                        break

                if not ok:
                    try:
                        await asyncio.sleep(1)
                    except:
                        return
                    continue
                app.state.discord_opqueue.pop(idx)

                # max retry = 5
                if retry_count == 5:
                    continue

                run_method = METHOD_MAP[method]
                try:
                    r = await run_method(app, url, data = data, headers = headers, timeout = 30)

                    if r.status_code == 429:
                        app.state.discord_opqueue.append((method, key, url, data, headers, error_msg, retry_count + 1))

                        d = json.loads(r.text)
                        if d["global"]:
                            try:
                                await asyncio.sleep(d["retry_after"])
                            except:
                                return
                            continue
                        app.state.discord_retry_after[key] = time.time() + float(d["retry_after"]) + 0.5

                    elif r.status_code == 401 and (error_msg == "disable" or error_msg.startswith("add_role") or error_msg.startswith("remove_role")):
                        DisableDiscordIntegration(app)

                    elif r.status_code // 100 != 2:
                        d = json.loads(r.text)

                        request = Request(scope={"type":"http", "app": app, "headers": []})

                        if error_msg is not None and error_msg.startswith("add_role"):
                            t = error_msg.split(",")
                            error_msg = ml.ctr(request, "error_adding_discord_role", var = {"code": d["code"], "discord_role": t[1], "user_discordid": t[2], "message": d["message"]})
                        elif error_msg is not None and error_msg.startswith("remove_role"):
                            t = error_msg.split(",")
                            error_msg = ml.ctr(request, "error_removing_discord_role", var = {"code": d["code"], "discord_role": t[1], "user_discordid": t[2], "message": d["message"]})

                        if error_msg not in [None, "disable"]:
                            from functions.notification import AuditLog
                            await AuditLog(request, -998, "discord", error_msg)

                        elif r.status_code // 100 == 4:
                            # surpass expected error behavior (soemthing wrong with config)
                            # however, don't send if the error is already sent (use elif)
                            from functions.notification import AuditLog
                            await AuditLog(request, -998, "discord", "**" + ml.ctr(request, "service_api_error", var = {"service": "Discord"}) + f"**\n```{r.text}```")

                except:
                    app.state.discord_opqueue.append((method, key, url, data, headers, error_msg, retry_count + 1))

                    try:
                        await asyncio.sleep(5)
                    except:
                        return
                    continue

            except:
                pass

            try:
                await asyncio.sleep(0.1)
            except:
                pass
