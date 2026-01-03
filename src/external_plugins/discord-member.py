# Copyright (C) 2022-2026 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# This external plugin returns a list of Discord members in the guild
# that has the Discord role defined by driver role in configuration.

import asyncio

from fastapi import Header, Request, Response
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute

from functions import *

async def FetchDiscordMembers(app):
    await asyncio.sleep(5)
    while True:
        npid = app.redis.get("multiprocess-pid")
        if npid is not None and int(npid) != os.getpid():
            return
        app.redis.set("multiprocess-pid", os.getpid())

        accept_discord_roles = [str(x["discord_role_id"]) for x in app.config.roles if x["id"] in app.config.perms.driver and "discord_role_id" in x.keys() and isint(x["discord_role_id"])]
        if len(accept_discord_roles) == 0:
            await asyncio.sleep(3600)
            continue
        after = 0
        new_members = []

        while True:
            try:
                r = await arequests.get(app, f"https://discord.com/api/v10/guilds/{app.config.discord_guild_id}/members?limit=1000&after={after}", headers = {"Authorization": f"Bot {app.config.discord_bot_token}"})
                d = json.loads(r.text)
                if r.status_code == 429:
                    await asyncio.sleep(d["retry_after"])
                    continue
                if r.status_code != 200:
                    await asyncio.sleep(3600)
                    break
                members = []
                for member in d:
                    if any(role in accept_discord_roles for role in member["roles"]):
                        members.append(member["user"]["id"])
                        app.redis.set(f"discord_member:{member['user']['id']}:roles", list2str(member["roles"]))
                new_members += members

                if len(d) < 1000:
                    break
                after = d[-1]["user"]["id"]
                await asyncio.sleep(1)
            except:
                import traceback
                traceback.print_exc()
                await asyncio.sleep(60)
                continue

        app.redis.delete("discord_members")
        for discordid in new_members:
            app.redis.lpush("discord_members", discordid)

        await asyncio.sleep(600)

async def get_discord_member(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid, db_name = app.config.db_name)
    au = await auth(authorization, request, required_permission = ["manage_profiles"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    # lrange is not proxied by our custom redis wrapper
    return app.redis.lrange(f"{app.config.abbr}:discord_members", 0, -1)

async def startup(app):
    loop = asyncio.get_event_loop()
    loop.create_task(FetchDiscordMembers(app))

def init(config: dict, print_log: bool = False):
    routes = [
        APIRoute("/member/discord", get_discord_member, methods=["GET"], response_class=JSONResponse)
    ]

    states = {}

    return (True, routes, states, {"startup": startup})
