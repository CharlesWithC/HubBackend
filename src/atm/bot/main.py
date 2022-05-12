#!/usr/bin/python3

# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

# Drivers Hub Bot 

from bot import bot
import json, asyncio
import discord

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.Game(name="At The Mile Logistics"))
    print(f"[Main Bot] Logged in as {bot.user} (ID: {bot.user.id})")

config_txt = open("./config.json","r").read()
config = json.loads(config_txt)

loop = asyncio.get_event_loop()
loop.create_task(bot.start(config["bottoken"]))
loop.run_forever()