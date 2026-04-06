# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import inspect
import time

from fastapi import Request

import multilang as ml
from functions.arequests import arequests
from functions.general import RateLimitException, DisableDiscordIntegration

def parse_discord_response(resp):
    content_type = resp.headers.get('Content-Type', '')

    if resp.status_code == 429:
        if 'application/json' in content_type:
            # api-level rate limit
            d = resp.json()
            glbl = d.get("global", False)
            retry_after = d.get("retry_after", 5)
        else:
            # cf-level rate limit
            glbl = True
            retry_after = int(resp.headers.get("Retry-After", 5))

        return (True, 429, {"global": glbl, "retry_after": retry_after})

    if 'application/json' in content_type:
        return (True, resp.status_code, resp.json())
    else:
        return (False, resp.status_code, resp.text)

class DiscordAuth:
    def __init__(self, client_id, client_secret, callback_url):
        self.client_id = client_id
        self.client_secret = client_secret
        self.callback_url = callback_url

    async def get_tokens(self, code, retry = 3):
        """ Gets the access token from the code given. The code can only be used on an active url (callback url) meaning you can only use the code once. """
        if retry == -1:
            raise RateLimitException("Unable to get token: Rate limited.")

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

        r = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        (ok, status_code, resp) = parse_discord_response(r)
        if status_code == 429:
            await asyncio.sleep(resp["retry_after"] + 0.5)
            return await self.get_tokens(code, retry - 1)
        elif not ok:
            raise Exception("Unable to get token: Invalid response from Discord API.")
        else:
            return resp

    async def refresh_token(self, refresh_token, retry = 3):
        """ Refreshes access token and access tokens and will return a new set of tokens """
        if retry == -1:
            raise RateLimitException("Unable to refresh token: Rate limited.")

        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'refresh_token',
            'refresh_token': refresh_token
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        r = await arequests.post(None, 'https://discord.com/api/v10/oauth2/token', data=data, headers=headers)
        (ok, status_code, resp) = parse_discord_response(r)
        if status_code == 429:
            await asyncio.sleep(resp["retry_after"] + 0.5)
            return await self.get_tokens(refresh_token, retry - 1)
        elif not ok:
            raise Exception("Unable to refresh token: Invalid response from Discord API.")
        else:
            return resp

    async def get_user_data_from_token(self, access_token, retry = 3):
        """ Gets the user data from an access_token """
        if retry == -1:
            raise RateLimitException("Unable to get user data: Rate limited.")

        headers = {
            "Authorization": f'Bearer {access_token}'
        }

        r = await arequests.get(None, 'https://discord.com/api/v10/users/@me', headers=headers)
        (ok, status_code, resp) = parse_discord_response(r)
        if status_code == 429:
            await asyncio.sleep(resp["retry_after"] + 0.5)
            return await self.get_user_data_from_token(access_token, retry - 1)
        elif not ok:
            raise Exception("Unable to get user data: Invalid response from Discord API.")
        else:
            return resp

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
                    (_, _, d) = parse_discord_response(r)

                    if r.status_code == 429:
                        app.state.discord_opqueue.append((method, key, url, data, headers, error_msg, retry_count + 1))

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
