# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

TF = [False, True]

from base64 import b64encode, b64decode
from discord import Webhook, Embed
from aiohttp import ClientSession
from fastapi.responses import JSONResponse
from datetime import datetime
import json, time, math, zlib, re
import hmac, base64, struct, hashlib
import ipaddress, requests, threading
from iso3166 import countries
import traceback

from db import newconn
from app import config, tconfig
import multilang as ml

def convert_quotation(s):
    s = str(s)
    return s.replace("\\'","'").replace("'", "\\'")

def b64e(s):
    s = str(s)
    s = re.sub(re.compile('<.*?>'), '', s)
    try:
        return b64encode(s.encode()).decode()
    except:
        return s
    
def b64d(s):
    s = str(s)
    try:
        return b64decode(s.encode()).decode()
    except:
        return s

def compress(s):
    if s == "":
        return ""
    if type(s) == str:
        s = s.encode()
    t = zlib.compress(s)
    t = b64encode(t).decode()
    return t

def decompress(s):
    if s == "":
        return ""
    try:
        if type(s) == str:
            s = s.encode()
        t = b64decode(s)
        t = zlib.decompress(t)
        t = t.decode()
        return t
    except:
        return s

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

def getFullCountry(abbr):
    try:
        country = countries.get(abbr).name
        return convert_quotation(country)
    except:
        return ""

def getRequestCountry(request, abbr = False):
    if "cf-ipcountry" in request.headers.keys():
        country = request.headers["cf-ipcountry"]
        try:
            country = countries.get(country)
            if abbr:
                return convert_quotation(request.headers["cf-ipcountry"])
            return country.name
        except:
            if abbr:
                return ""
            return ""
    if abbr:
        return ""
    return ""

def getUserAgent(request):
    if "user-agent" in request.headers.keys():
        if len(request.headers["user-agent"]) <= 200:
            return convert_quotation(request.headers["user-agent"])
        return ""
    else:
        return ""

cuserinfo = {} # user info cache

def getAvatarSrc(userid):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, avatar FROM user WHERE userid = {userid}")
    t = cur.fetchall()
    discordid = str(t[0][0])
    avatar = str(t[0][1])
    src = ""
    if avatar.startswith("a_"):
        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif"
    else:
        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png"
    return src

def getUserInfo(userid = -1, discordid = -1, privacy = False, tell_deleted = False):
    if userid == -999:
        return {"name": "System", "userid": "-1", "discordid": "-1", "avatar": "", "roles": []}
        
    if privacy:
        return {"name": "[Protected]", "userid": "-1", "discordid": "-1", "avatar": "", "roles": []}

    if userid == -1 and discordid == -1:
        if not tell_deleted:
            return {"name": "Unknown", "userid": "-1", "discordid": "-1", "avatar": "", "roles": []}
        else:
            return {"name": "Unknown", "userid": "-1", "discordid": "-1", "avatar": "", "roles": [], "is_deleted": True}

    global cuserinfo
    
    if userid != -1 and f"userid={userid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"userid={userid}"]["expire"]:
            return cuserinfo[f"userid={userid}"]["data"]
    if discordid != -1 and f"discordid={discordid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"discordid={discordid}"]["expire"]:
            return cuserinfo[f"discordid={discordid}"]["data"]

    query = ""
    if userid != -1:
        query = f"userid = '{userid}'"
    elif discordid != -1:
        query = f"discordid = '{discordid}'"

    conn = newconn()
    cur = conn.cursor()
    
    cur.execute(f"SELECT name, userid, discordid, avatar, roles FROM user WHERE {query}")
    p = cur.fetchall()
    if len(p) == 0:
        if not tell_deleted:
            return {"name": "Unknown", "userid": str(userid), "discordid": str(discordid), "avatar": "", "roles": []}
        else:
            return {"name": "Unknown", "userid": str(userid), "discordid": str(discordid), "avatar": "", "roles": [], "is_deleted": True}

    roles = p[0][4].split(",")
    while "" in roles:
        roles.remove("")

    if p[0][1] != -1:
        cuserinfo[f"userid={p[0][1]}"] = {"data": {"name": p[0][0], "userid": str(p[0][1]), "discordid": str(p[0][2]), "avatar": p[0][3], "roles": roles}, "expire": int(time.time()) + 600}
    cuserinfo[f"discordid={p[0][2]}"] = {"data": {"name": p[0][0], "userid": str(p[0][1]), "discordid": str(p[0][2]), "avatar": p[0][3], "roles": roles}, "expire": int(time.time()) + 600}

    return {"name": p[0][0], "userid": str(p[0][1]), "discordid": str(p[0][2]), "avatar": p[0][3], "roles": roles}

def activityUpdate(discordid, activity):
    if int(discordid) <= 0:
        return
    conn = newconn()
    cur = conn.cursor()
    activity = convert_quotation(activity)
    cur.execute(f"SELECT timestamp FROM user_activity WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) != 0:
        last_timestamp = t[0][0]
        if int(time.time()) - last_timestamp <= 2 and activity.find("Delivery Log #") == -1 and activity.find("Profile") == -1:
            return
        cur.execute(f"UPDATE user_activity SET activity = '{activity}', timestamp = {int(time.time())} WHERE discordid = {discordid}")
    else:
        cur.execute(f"INSERT INTO user_activity VALUES ({discordid}, '{activity}', {int(time.time())})")
    conn.commit()
    
discord_message_queue = []

def QueueDiscordMessage(channelid, data):
    global discord_message_queue
    if config.discord_bot_token == "":
        return
    discord_message_queue.append((channelid, data))

def SendDiscordMessage(channelid, data):
    if config.discord_bot_token == "":
        return -1
    
    try:
        requests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", \
                headers=headers, data=json.dumps(data))
    except:
        pass

    return 0

def ProcessDiscordMessage(): # thread
    global discord_message_queue
    global config
    headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
    while 1:
        try:
            if config.discord_bot_token == "":
                return
            if len(discord_message_queue) == 0:
                time.sleep(1)
                continue
            
            # get first in queue
            channelid = discord_message_queue[0][0]
            data = discord_message_queue[0][1]

            # see if there's any more embed to send to the channel
            to_delete = [0]
            for i in range(1, len(discord_message_queue)):
                (chnid, d) = discord_message_queue[i]
                if chnid == channelid and \
                        not "content" in d.keys() and "embeds" in d.keys():
                    # not a text message but a rich embed
                    if len(str(data["embeds"])) + len(str(d["embeds"])) > 5000:
                        break # make sure this will not exceed character limit
                    for j in range(len(d["embeds"])):
                        data["embeds"].append(d["embeds"][j])
                    to_delete.append(i)

            try:
                r = requests.post(f"https://discord.com/api/v10/channels/{channelid}/messages", \
                    headers=headers, data=json.dumps(data))
            except:
                traceback.print_exc()
                time.sleep(5)
                continue

            if r.status_code == 429:
                d = json.loads(r.text)
                time.sleep(d["retry_after"])
            elif r.status_code == 403:
                conn = newconn()
                cur = conn.cursor()
                cur.execute(f"DELETE FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")
                cur.execute(f"DELETE FROM settings WHERE skey = 'event-notification' AND sval = '{channelid}'")
                conn.commit()
                for i in to_delete[::-1]:
                    discord_message_queue.pop(i)
            elif r.status_code == 401:
                DisableDiscordIntegration()
                return
            elif r.status_code == 200 or r.status_code >= 400 and r.status_code <= 499:
                for i in to_delete[::-1]:
                    discord_message_queue.pop(i)

            time.sleep(1)
            
        except:
            traceback.print_exc()
            time.sleep(1)

threading.Thread(target=ProcessDiscordMessage, daemon = True).start()

def CheckDiscordNotification(discordid):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'discord-notification'")
    t = cur.fetchall()
    if len(t) == 0:
        return False
    ret = t[0][0]
    if ret == "disabled":
        return False
    return ret

def SendDiscordNotification(discordid, data):
    t = CheckDiscordNotification(discordid)
    if t == False:
        return
    QueueDiscordMessage(t, data)

def GetUserLanguage(discordid, default_language = ""):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
    t = cur.fetchall()
    if len(t) == 0:
        return default_language
    return t[0][0]

def CheckNotificationEnabled(notification_type, discordid):
    conn = newconn()
    cur = conn.cursor()
    
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = cur.fetchall()
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True
    
    if notification_type in settings.keys() and not settings[notification_type]:
        return False
    return True

def notification(notification_type, discordid, content, no_drivershub_notification = False, \
        no_discord_notification = False, discord_embed = {}):
    if int(discordid) <= 0:
        return
        
    conn = newconn()
    cur = conn.cursor()
    
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = cur.fetchall()
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return

    if settings["drivershub"] and not no_drivershub_notification:
        cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxtnotificationid'")
        t = cur.fetchall()
        nxtnotificationid = int(t[0][0])
        cur.execute(f"UPDATE settings SET sval = '{nxtnotificationid + 1}' WHERE skey = 'nxtnotificationid'")
        cur.execute(f"INSERT INTO user_notification VALUES ({nxtnotificationid}, {discordid}, '{convert_quotation(content)}', {int(time.time())}, 0)")
        conn.commit()
    
    if settings["discord"] and not no_discord_notification:
        if discord_embed != {}:
            SendDiscordNotification(discordid, {"embeds": [{"title": discord_embed["title"], 
                "description": discord_embed["description"], "fields": discord_embed["fields"], "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]})
        else:
            SendDiscordNotification(discordid, {"embeds": [{"title": ml.tr(None, "notification", force_lang = GetUserLanguage(discordid, "en")), 
                "description": content, "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]})

def ratelimit(request, ip, endpoint, limittime, limitcnt):
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"DELETE FROM ratelimit WHERE first_request_timestamp <= {round(time.time() - 86400)}")
    cur.execute(f"DELETE FROM ratelimit WHERE endpoint = '429-error' AND first_request_timestamp <= {round(time.time() - 60)}")
    cur.execute(f"SELECT first_request_timestamp, endpoint FROM ratelimit WHERE ip = '{ip}' AND endpoint LIKE 'ip-ban-%'")
    t = cur.fetchall()
    maxban = 0
    for tt in t:
        frt = tt[0]
        bansec = int(tt[1].split("-")[-1])
        maxban = max(frt + bansec, maxban)
        if maxban < int(time.time()):
            cur.execute(f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-{bansec}'")
            conn.commit()
            maxban = 0
    if maxban > 0:
        resp_headers = {}
        resp_headers["Retry-After"] = str(maxban - int(time.time()))
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(maxban)
        resp_headers["X-RateLimit-Reset-After"] = str(maxban - int(time.time()))
        resp_headers["X-RateLimit-Global"] = "true"
        resp_content = {"error": True, "descriptor": ml.tr(request, "rate_limit"), \
            "retry_after": str(maxban - int(time.time())), "global": True}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    cur.execute(f"SELECT SUM(request_count) FROM ratelimit WHERE ip = '{ip}' AND first_request_timestamp > {int(time.time() - 60)}")
    t = cur.fetchall()
    if t[0][0] != None and t[0][0] > 150:
        # more than 150r/m combined
        # including 429 requests
        # 10min ip ban
        cur.execute(f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-600'")
        cur.execute(f"INSERT INTO ratelimit VALUES ('{ip}', 'ip-ban-600', {int(time.time())}, 0)")
        conn.commit()
        resp_headers = {}
        resp_headers["Retry-After"] = str(600)
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(0)
        resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + 600)
        resp_headers["X-RateLimit-Reset-After"] = str(600)
        resp_headers["X-RateLimit-Global"] = "true"
        resp_content = {"error": True, "descriptor": ml.tr(request, "rate_limit"), \
            "retry_after": "600", "global": True}
        return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
    cur.execute(f"SELECT first_request_timestamp, request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
    t = cur.fetchall()
    if len(t) == 0:
        cur.execute(f"INSERT INTO ratelimit VALUES ('{ip}', '{endpoint}', {int(time.time())}, 1)")
        conn.commit()
        resp_headers = {}
        resp_headers["X-RateLimit-Limit"] = str(limitcnt)
        resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
        resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
        resp_headers["X-RateLimit-Reset-After"] = str(limittime)
        return (False, resp_headers)
    else:
        first_request_timestamp = t[0][0]
        request_count = t[0][1]
        if int(time.time()) - first_request_timestamp > limittime:
            cur.execute(f"UPDATE ratelimit SET first_request_timestamp = {int(time.time())}, request_count = 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
            conn.commit()
            resp_headers = {}
            resp_headers["X-RateLimit-Limit"] = str(limitcnt)
            resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
            resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
            resp_headers["X-RateLimit-Reset-After"] = str(limittime)
            return (False, resp_headers)
        else:
            if request_count + 1 > limitcnt:
                cur.execute(f"SELECT request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '429-error'")
                t = cur.fetchall()
                if len(t) > 0:
                    cur.execute(f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '429-error'")
                    conn.commit()
                else:
                    cur.execute(f"INSERT INTO ratelimit VALUES ('{ip}', '429-error', {int(time.time())}, 1)")
                    conn.commit()

                retry_after = limittime - (int(time.time()) - first_request_timestamp)
                resp_headers = {}
                resp_headers["Retry-After"] = str(retry_after)
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(0)
                resp_headers["X-RateLimit-Reset"] = str(retry_after + int(time.time()))
                resp_headers["X-RateLimit-Reset-After"] = str(retry_after)
                resp_headers["X-RateLimit-Global"] = "false"
                resp_content = {"error": True, "descriptor": ml.tr(request, "rate_limit"), \
                    "retry_after": str(retry_after), "global": False}
                return (True, JSONResponse(content = resp_content, headers = resp_headers, status_code = 429))
            else:
                cur.execute(f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
                conn.commit()
                resp_headers = {}
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(limitcnt - request_count - 1)
                resp_headers["X-RateLimit-Reset"] = str(first_request_timestamp + limittime)
                resp_headers["X-RateLimit-Reset-After"] = str(limittime - (int(time.time()) - first_request_timestamp))
                return (False, resp_headers)

def auth(authorization, request, check_ip_address = True, allow_application_token = False, check_member = True, required_permission = []):
    # authorization header basic check
    if authorization is None:
        return {"error": True, "descriptor": "Unauthorized", "code": 401}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        return {"error": True, "descriptor": "Unauthorized", "code": 401}
    
    tokentype = authorization.split(" ")[0]
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": True, "descriptor": "Unauthorized", "code": 401}

    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")

    # application token
    if tokentype == "Application":
        # check if allowed
        if not allow_application_token:
            return {"error": True, "descriptor": ml.tr(request, "application_token_prohibited"), "code": 401}

        # validate token
        cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Unauthorized", "code": 401}
        discordid = t[0][0]

        # application token will skip ip check

        # additional check
        
        # this should not happen but just in case
        cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Unauthorized", "code": 401}
        userid = t[0][0]
        roles = t[0][1].split(",")
        name = t[0][2]
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": True, "descriptor": "Unauthorized", "code": 401}

        while "" in roles:
            roles.remove("")

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": True, "descriptor": "Forbidden", "code": 403}

        cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
        t = cur.fetchall()
        language = ""
        if len(t) != 0:
            language = t[0][0]

        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "language": language, "application_token": True}

    # bearer token
    elif tokentype == "Bearer":
        cur.execute(f"SELECT discordid, ip, country, last_used_timestamp, user_agent FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Unauthorized", "code": 401}
        discordid = t[0][0]
        ip = t[0][1]
        country = t[0][2]
        last_used_timestamp = t[0][3]
        user_agent = t[0][4]

        # check country
        curCountry = getRequestCountry(request, abbr = True)
        if curCountry != country and country != "":
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            return {"error": True, "descriptor": "Unauthorized", "code": 401}

        if ip != request.client.host:
            cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        if curCountry != country and not curCountry != "" and country != "":
            cur.execute(f"UPDATE session SET country = '{curCountry}' WHERE token = '{stoken}'")
        if getUserAgent(request) != user_agent:
            cur.execute(f"UPDATE session SET user_agent = '{getUserAgent(request)}' WHERE token = '{stoken}'")
        conn.commit()
        
        # additional check
        
        # this should not happen but just in case
        cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Unauthorized", "code": 401}
        userid = t[0][0]
        roles = t[0][1].split(",")
        name = t[0][2]
        if userid == -1 and (check_member or len(required_permission) != 0):
            return {"error": True, "descriptor": "Unauthorized", "code": 401}

        while "" in roles:
            roles.remove("")

        if check_member and len(required_permission) != 0:
            # permission check will only take place if member check is enforced
            ok = False
            
            for role in roles:
                for perm in required_permission:
                    if perm in tconfig["perms"].keys() and int(role) in tconfig["perms"][perm] or int(role) in tconfig["perms"]["admin"]:
                        ok = True
            
            if not ok:
                return {"error": True, "descriptor": "Forbidden", "code": 403}

        if int(time.time()) - last_used_timestamp >= 5:
            cur.execute(f"UPDATE session SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            conn.commit()

        cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
        t = cur.fetchall()
        language = ""
        if len(t) != 0:
            language = t[0][0]
            
        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "language": language, "application_token": False}
    
    return {"error": True, "descriptor": "Unauthorized", "code": 401}

async def AuditLog(userid, text):
    try:
        conn = newconn()
        cur = conn.cursor()
        name = "Unknown User"
        if userid == -999:
            name = "System"
        elif userid == -998:
            name = "Discord API"
        else:
            cur.execute(f"SELECT name FROM user WHERE userid = {userid}")
            t = cur.fetchall()
            if len(t) > 0:
                name = t[0][0]
        if userid != -998:
            cur.execute(f"INSERT INTO auditlog VALUES ({userid}, '{convert_quotation(text)}', {int(time.time())})")
            conn.commit()
        if config.webhook_audit != "":
            async with ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_audit, session=session)
                embed = Embed(description = text, color = config.rgbcolor)
                if userid not in [-999, -998]:
                    embed.set_footer(text = f"{name} (ID {userid})", icon_url = getAvatarSrc(userid))
                else:
                    embed.set_footer(text = f"{name}")
                embed.timestamp = datetime.now()
                await webhook.send(embed=embed)
    except:
        traceback.print_exc()

def DisableDiscordIntegration():
    global config
    config.discord_bot_token = ""
    try:
        requests.post(config.webhook_audit, data=json.dumps({"embeds": [{"title": "Attention Required", "description": "Failed to validate Discord Bot Token. All Discord Integrations have been temporarily disabled within the current session. Setting a valid token in config and reloading API will restore the functions.", "color": config.intcolor, "footer": {"text": "System"}, "timestamp": str(datetime.now())}]}), headers={"Content-Type": "application/json"})
    except:
        pass

async def AutoMessage(meta, setvar):
    global config
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
            if config.discord_bot_token == "":
                return

            headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
            ddurl = f"https://discord.com/api/v10/channels/{meta.channel_id}/messages"
            timestamp = ""
            if meta.embed.timestamp:
                timestamp = str(datetime.now())
            r = requests.post(ddurl, headers=headers, data=json.dumps({
                "content": setvar(meta.content),
                "embeds": [{
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
                }]}))
            if r.status_code == 401:
                DisableDiscordIntegration()
    except:
        traceback.print_exc()