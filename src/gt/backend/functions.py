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