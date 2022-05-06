# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

from base64 import b64encode, b64decode

def b64e(s):
    try:
        return b64encode(s.encode()).decode()
    except:
        return s
    
def b64d(s):
    try:
        return b64decode(s.encode()).decode()
    except:
        return s

import discord
from discord import Webhook
import aiohttp
from db import newconn
from app import config
from datetime import datetime
import time

async def AuditLog(userid, text):
    conn = newconn()
    cur = conn.cursor()
    name = "Unknown User"
    cur.execute(f"SELECT name FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    if len(t) > 0:
        name = t[0][0]
    cur.execute(f"INSERT INTO auditlog VALUES ({userid}, '{text}', {int(time.time())})")
    conn.commit()
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(config.webhook, session=session)
        embed = discord.Embed(description = text, color = 0x770202)
        embed.set_footer(text = f"Responsible User: {name} (ID {userid})")
        embed.timestamp = datetime.now()
        await webhook.send(embed=embed)