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
    text = text.replace("''","'").replace("'","''")
    cur.execute(f"INSERT INTO auditlog VALUES ({userid}, '{text}', {int(time.time())})")
    conn.commit()
    if config.webhook_audit != "":
        try:
            async with aiohttp.ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_audit, session=session)
                embed = discord.Embed(description = text, color = config.rgbcolor)
                if userid != -999:
                    embed.set_footer(text = f"Responsible User: {name} (ID {userid})")
                else:
                    embed.set_footer(text = f"Responsible User: {name}")
                embed.timestamp = datetime.now()
                await webhook.send(embed=embed)
        except:
            pass
        
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

ipv4 = '''^(25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)\.(
            25[0-5]|2[0-4][0-9]|[0-1]?[0-9][0-9]?)$'''
 
ipv6 = '''(([0-9a-fA-F]{1,4}:){7,7}[0-9a-fA-F]{1,4}|
        ([0-9a-fA-F]{1,4}:){1,7}:|([0-9a-fA-F]{1,4}:)
        {1,6}:[0-9a-fA-F]{1,4}|([0-9a-fA-F]{1,4}:){1
        ,5}(:[0-9a-fA-F]{1,4}){1,2}|([0-9a-fA-F]{1,4}
        :){1,4}(:[0-9a-fA-F]{1,4}){1,3}|([0-9a-fA-F]{
        1,4}:){1,3}(:[0-9a-fA-F]{1,4}){1,4}|([0-9a-fA
        -F]{1,4}:){1,2}(:[0-9a-fA-F]{1,4}){1,5}|[0-9a
        -fA-F]{1,4}:((:[0-9a-fA-F]{1,4}){1,6})|:((:[0
        -9a-fA-F]{1,4}){1,7}|:)|fe80:(:[0-9a-fA-F]{0,
        4}){0,4}%[0-9a-zA-Z]{1,}|::(ffff(:0{1,4}){0,1}
        :){0,1}((25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0-9
        ])\.){3,3}(25[0-5]|(2[0-4]|1{0,1}[0-9]){0,1}[0
        -9])|([0-9a-fA-F]{1,4}:){1,4}:((25[0-5]|(2[0-4]
        |1{0,1}[0-9]){0,1}[0-9])\.){3,3}(25[0-5]|(2[0-4]
        |1{0,1}[0-9]){0,1}[0-9]))'''
 
def iptype(Ip): 
    if re.search(ipv4, Ip):
        return "ipv4"
    elif re.search(ipv6, Ip):
        return "ipv6"
    else:
        return "invalid ip"

def TSeparator(num):
    flag = ""
    if int(num) < 0:
        flag = "-"
        num = abs(int(num))
    if int(num) < 1000:
        return flag + str(num)
    else:
        return flag + TSeparator(str(num)[:-3]) + "," + str(num)[-3:]

def ratelimit(ip, endpoint, limittime, limitcnt):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM ratelimit WHERE firstop <= {int(time.time() - 86400)}")
    cur.execute(f"SELECT firstop, opcount FROM ratelimit WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO ratelimit VALUES ('{ip}', '{endpoint}', {int(time.time())}, 1)")
        conn.commit()
        return 0
    else:
        firstop = t[0][0]
        opcount = t[0][1]
        if int(time.time()) - firstop > limittime:
            cur.execute(f"UPDATE ratelimit SET firstop = {int(time.time())}, opcount = 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
            conn.commit()
            return 0
        else:
            if opcount + 1 > limitcnt:
                return limittime - (int(time.time()) - firstop)
            else:
                cur.execute(f"UPDATE ratelimit SET opcount = opcount + 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
                conn.commit()
                return 0