# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from base64 import b64encode, b64decode
import re
def b64e(s):
    s = re.sub(re.compile('<.*?>'), '', s)
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
    if userid != -999:
        cur.execute(f"SELECT name FROM user WHERE userid = {userid}")
        t = cur.fetchall()
        if len(t) > 0:
            name = t[0][0]
    else:
        name = "System"
    cur.execute(f"INSERT INTO auditlog VALUES ({userid}, '{text}', {int(time.time())})")
    conn.commit()
    async with aiohttp.ClientSession() as session:
        webhook = Webhook.from_url(config.webhook, session=session)
        embed = discord.Embed(description = text, color = 0x770202)
        embed.set_footer(text = f"Responsible User: {name} (ID {userid})")
        embed.timestamp = datetime.now()
        await webhook.send(embed=embed)
        
def b62encode(d):
    ret = ""
    l = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if d == 0:
        return l[0]
    flag = ""
    if d < 0:
        flag = "-"
        d = abs(d)
    while d:
        ret += l[d % 62]
        d //= 62
    return flag + ret[::-1]

def b62decode(d):
    flag = 1
    if d.startswith("-"):
        flag = -1
        d = d[1:]
    ret = 0
    l = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(len(d)):
        ret += l.find(d[i]) * 62 ** (len(d) - i - 1)
    return ret * flag