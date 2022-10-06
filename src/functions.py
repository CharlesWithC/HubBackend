# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

TF = [False, True]

from base64 import b64encode, b64decode
from discord import Webhook, Embed
from aiohttp import ClientSession
from datetime import datetime, timedelta
import json, time, math, zlib, re
import hmac, base64, struct, hashlib
import ipaddress, requests

from db import newconn
from app import config, tconfig
import multilang as ml

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

def compress(s):
    if type(s) == str:
        s = s.encode()
    t = zlib.compress(s)
    t = b64encode(t).decode()
    return t

def decompress(s):
    if type(s) == str:
        s = s.encode()
    t = b64decode(s)
    t = zlib.decompress(t)
    t = t.decode()
    return t

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
        return 4
    elif re.search(ipv6, Ip):
        return 6
    else:
        return 0

def isurl(s):
    r = re.compile(
            r'^(?:http)s?://' # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|' #domain...
            r'localhost|' #localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})' # ...or ip
            r'(?::\d+)?' # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return re.match(r, s) is not None

def getDayStartTs(timestamp):
    dt = datetime.fromtimestamp(timestamp)
    return int(datetime(dt.year, dt.month, dt.day).timestamp())

def tseparator(num):
    flag = ""
    if int(num) < 0:
        flag = "-"
        num = abs(int(num))
    if int(num) < 1000:
        return flag + str(num)
    else:
        return flag + tseparator(str(num)[:-3]) + "," + str(num)[-3:]

def sigfig(num, sigfigs_opt = 3):
    num = int(num)
    flag = ""
    if num < 0:
        flag = "-"
        num = -num
    if num < 1000:
        return str(num)
    power10 = math.log10(num)
    SUFFIXES = ['', 'K', 'M', 'B', 'T', 'P', 'E', 'Z']
    suffixNum = math.floor(power10 / 3)
    if suffixNum >= len(SUFFIXES):
        return flag + "999+" + SUFFIXES[-1]
    suffix = SUFFIXES[suffixNum]
    suffixPower10 = math.pow(10, suffixNum * 3)
    base = num / suffixPower10
    baseRound = str(base)[:min(4,len(str(base)))]
    if baseRound.endswith("."):
        baseRound = baseRound[:-1]
    return flag + baseRound + suffix
    
def get_hotp_token(secret, intervals_no):
    key = base64.b32decode(secret, True)
    msg = struct.pack(">Q", intervals_no)
    h = hmac.new(key, msg, hashlib.sha1).digest()
    o = o = h[19] & 15
    h = (struct.unpack(">I", h[o:o+4])[0] & 0x7fffffff) % 1000000
    return h
    
def get_totp_token(secret):
    ret = []
    for k in range(-2,2):
        x =str(get_hotp_token(secret,intervals_no=int(time.time())//30+k))
        while len(x)!=6:
            x+='0'
        ret.append(x)
    return ret

def valid_totp(otp, secret):
    return str(otp) in get_totp_token(secret)

def ratelimit(ip, endpoint, limittime, limitcnt):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM ratelimit WHERE first_request_timestamp <= {int(time.time() - 86400)}")
    cur.execute(f"SELECT first_request_timestamp, request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO ratelimit VALUES ('{ip}', '{endpoint}', {int(time.time())}, 1)")
        conn.commit()
        return 0
    else:
        first_request_timestamp = t[0][0]
        request_count = t[0][1]
        if int(time.time()) - first_request_timestamp > limittime:
            cur.execute(f"UPDATE ratelimit SET first_request_timestamp = {int(time.time())}, request_count = 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
            conn.commit()
            return 0
        else:
            if request_count + 1 > limitcnt:
                return limittime - (int(time.time()) - first_request_timestamp)
            else:
                cur.execute(f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
                conn.commit()
                return 0

def auth(authorization, request, check_ip_address = True, allow_application_token = False, check_member = True, required_permission = ["admin", "driver"]):
    # authorization header basic check
    if authorization is None:
        return {"error": True, "descriptor": ml.tr(request, "authorization_header_not_found")}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        return {"error": True, "descriptor": ml.tr(request, "invalid_authorization_header")}
    
    tokentype = authorization.split(" ")[0]
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

    conn = newconn()
    cur = conn.cursor()

    # application token
    if tokentype == "Application":
        # check if allowed
        if not allow_application_token:
            return {"error": True, "descriptor": ml.tr(request, "application_token_prohibited")}

        # validate token
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        discordid = t[0][0]

        # application token will skip ip check

        # additional check
        
        # this should not happen but just in case
        cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        userid = t[0][0]
        roles = t[0][1].split(",")
        name = t[0][2]
        if userid == -1 and check_member:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        while "" in roles:
            roles.remove("")

        if check_member:
            # permission check will only take place if member check is enforced
            ok = False
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "application_token": True}

    # bearer token
    elif tokentype == "Bearer":
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        discordid = t[0][0]
        ip = t[0][1]

        # check ip
        orgiptype = iptype(ip)
        if orgiptype != 0:
            curiptype = iptype(request.client.host)
            if orgiptype != curiptype:
                cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                conn.commit()
            else:
                if curiptype == 6:
                    curip = ipaddress.ip_address(request.client.host).exploded
                    orgip = ipaddress.ip_address(ip).exploded
                    if curip.split(":")[:4] != orgip.split(":")[:4]:
                        cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                        conn.commit()
                        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
                elif curiptype == 4:
                    if ip.split(".")[:3] != request.client.host.split(".")[:3]:
                        cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                        conn.commit()
                        return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        
        # additional check
        
        # this should not happen but just in case
        cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}
        userid = t[0][0]
        roles = t[0][1].split(",")
        name = t[0][2]
        if userid == -1 and check_member:
            return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        while "" in roles:
            roles.remove("")

        if check_member:
            # permission check will only take place if member check is enforced
            ok = False
            
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "application_token": False}
    
    return {"error": True, "descriptor": ml.tr(request, "unauthorized")}

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
            async with ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_audit, session=session)
                embed = Embed(description = text, color = config.rgbcolor)
                if userid != -999:
                    embed.set_footer(text = f"Responsible User: {name} (ID {userid})")
                else:
                    embed.set_footer(text = f"Responsible User: {name}")
                embed.timestamp = datetime.now()
                await webhook.send(embed=embed)
        except:
            pass

async def AutoMessage(meta, setvar):
    try:
        if meta.webhook_url != "":
            async with ClientSession() as session:
                webhook = Webhook.from_url(meta.webhook_url, session=session)
                embed = Embed(title = setvar(meta.embed.title), \
                    description = setvar(meta.embed.description), color = config.rgbcolor)
                embed.set_footer(text = setvar(meta.embed.footer.text), icon_url = setvar(meta.embed.footer.icon_url))
                if meta.embed.image_url != "":
                    embed.set_image(url = setvar(meta.embed.image_url))
                if meta.embed.timestamp:
                    embed.timestamp = datetime.now()
                await webhook.send(content = setvar(meta.content), embed=embed)

        elif meta.channel_id != "":
            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v9/channels/{meta.channel_id}/messages"
            timestamp = ""
            if meta.embed.timestamp:
                timestamp = str(datetime.now())
            requests.post(ddurl, headers=headers, data=json.dumps({
                "content": setvar(meta.content),
                "embed":{
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
                    "color": config.intcolor
                }}))
    except:
        pass