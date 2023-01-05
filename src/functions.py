# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from base64 import b64encode, b64decode
from discord import Webhook, Embed
from aiohttp import ClientSession
from fastapi.responses import JSONResponse
from datetime import datetime
import json, time, math, zlib, re, random
import hmac, base64, struct, hashlib
import ipaddress, requests, threading
import traceback

from db import genconn, aiosql
from app import config, tconfig
import multilang as ml

ISO3166_COUNTRIES = {'AF': 'Afghanistan', 'AX': 'Åland Islands', 'AL': 'Albania', 'DZ': 'Algeria', 'AS': 'American Samoa', 'AD': 'Andorra', 'AO': 'Angola', 'AI': 'Anguilla', 'AQ': 'Antarctica', 'AG': 'Antigua and Barbuda', 'AR': 'Argentina', 'AM': 'Armenia', 'AW': 'Aruba', 'AU': 'Australia', 'AT': 'Austria', 'AZ': 'Azerbaijan', 'BS': 'Bahamas', 'BH': 'Bahrain', 'BD': 'Bangladesh', 'BB': 'Barbados', 'BY': 'Belarus', 'BE': 'Belgium', 'BZ': 'Belize', 'BJ': 'Benin', 'BM': 'Bermuda', 'BT': 'Bhutan', 'BO': 'Bolivia, Plurinational State of', 'BQ': 'Bonaire, Sint Eustatius and Saba', 'BA': 'Bosnia and Herzegovina', 'BW': 'Botswana', 'BV': 'Bouvet Island', 'BR': 'Brazil', 'IO': 'British Indian Ocean Territory', 'BN': 'Brunei Darussalam', 'BG': 'Bulgaria', 'BF': 'Burkina Faso', 'BI': 'Burundi', 'KH': 'Cambodia', 'CM': 'Cameroon', 'CA': 'Canada', 'CV': 'Cabo Verde', 'KY': 'Cayman Islands', 'CF': 'Central African Republic', 'TD': 'Chad', 'CL': 'Chile', 'CN': 'China', 'CX': 'Christmas Island', 'CC': 'Cocos (Keeling) Islands', 'CO': 'Colombia', 'KM': 'Comoros', 'CG': 'Congo', 'CD': 'Congo, Democratic Republic of the', 'CK': 'Cook Islands', 'CR': 'Costa Rica', 'CI': "Côte d'Ivoire", 'HR': 'Croatia', 'CU': 'Cuba', 'CW': 'Curaçao', 'CY': 'Cyprus', 'CZ': 'Czechia', 'DK': 'Denmark', 'DJ': 'Djibouti', 'DM': 'Dominica', 'DO': 'Dominican Republic', 'EC': 'Ecuador', 'EG': 'Egypt', 'SV': 'El Salvador', 'GQ': 'Equatorial Guinea', 'ER': 'Eritrea', 'EE': 'Estonia', 'ET': 'Ethiopia', 'FK': 'Falkland Islands (Malvinas)', 'FO': 'Faroe Islands', 'FJ': 'Fiji', 'FI': 'Finland', 'FR': 'France', 'GF': 'French Guiana', 'PF': 'French Polynesia', 'TF': 'French Southern Territories', 'GA': 'Gabon', 'GM': 'Gambia', 'GE': 'Georgia', 'DE': 'Germany', 'GH': 'Ghana', 'GI': 'Gibraltar', 'GR': 'Greece', 'GL': 'Greenland', 'GD': 'Grenada', 'GP': 'Guadeloupe', 'GU': 'Guam', 'GT': 'Guatemala', 'GG': 'Guernsey', 'GN': 'Guinea', 'GW': 'Guinea-Bissau', 'GY': 'Guyana', 'HT': 'Haiti', 'HM': 'Heard Island and McDonald Islands', 'VA': 'Holy See', 'HN': 'Honduras', 'HK': 'Hong Kong', 'HU': 'Hungary', 'IS': 'Iceland', 'IN': 'India', 'ID': 'Indonesia', 'IR': 'Iran, Islamic Republic of', 'IQ': 'Iraq', 'IE': 'Ireland', 'IM': 'Isle of Man', 'IL': 'Israel', 'IT': 'Italy', 'JM': 'Jamaica', 'JP': 'Japan', 'JE': 'Jersey', 'JO': 'Jordan', 'KZ': 'Kazakhstan', 'KE': 'Kenya', 'KI': 'Kiribati', 'KP': "Korea, Democratic People's Republic of", 'KR': 'Korea, Republic of', 'XK': 'Kosovo', 'KW': 'Kuwait', 'KG': 'Kyrgyzstan', 'LA': "Lao People's Democratic Republic", 'LV': 'Latvia', 'LB': 'Lebanon', 'LS': 'Lesotho', 'LR': 'Liberia', 'LY': 'Libya', 'LI': 'Liechtenstein', 'LT': 'Lithuania', 'LU': 'Luxembourg', 'MO': 'Macao', 'MK': 'North Macedonia', 'MG': 'Madagascar', 'MW': 'Malawi', 'MY': 'Malaysia', 'MV': 'Maldives', 'ML': 'Mali', 'MT': 'Malta', 'MH': 'Marshall Islands', 'MQ': 'Martinique', 'MR': 'Mauritania', 'MU': 'Mauritius', 'YT': 'Mayotte', 'MX': 'Mexico', 'FM': 'Micronesia, Federated States of', 'MD': 'Moldova, Republic of', 'MC': 'Monaco', 'MN': 'Mongolia', 'ME': 'Montenegro', 'MS': 'Montserrat', 'MA': 'Morocco', 'MZ': 'Mozambique', 'MM': 'Myanmar', 'NA': 'Namibia', 'NR': 'Nauru', 'NP': 'Nepal', 'NL': 'Netherlands', 'NC': 'New Caledonia', 'NZ': 'New Zealand', 'NI': 'Nicaragua', 'NE': 'Niger', 'NG': 'Nigeria', 'NU': 'Niue', 'NF': 'Norfolk Island', 'MP': 'Northern Mariana Islands', 'NO': 'Norway', 'OM': 'Oman', 'PK': 'Pakistan', 'PW': 'Palau', 'PS': 'Palestine, State of', 'PA': 'Panama', 'PG': 'Papua New Guinea', 'PY': 'Paraguay', 'PE': 'Peru', 'PH': 'Philippines', 'PN': 'Pitcairn', 'PL': 'Poland', 'PT': 'Portugal', 'PR': 'Puerto Rico', 'QA': 'Qatar', 'RE': 'Réunion', 'RO': 'Romania', 'RU': 'Russian Federation', 'RW': 'Rwanda', 'BL': 'Saint Barthélemy', 'SH': 'Saint Helena, Ascension and Tristan da Cunha', 'KN': 'Saint Kitts and Nevis', 'LC': 'Saint Lucia', 'MF': 'Saint Martin (French part)', 'PM': 'Saint Pierre and Miquelon', 'VC': 'Saint Vincent and the Grenadines', 'WS': 'Samoa', 'SM': 'San Marino', 'ST': 'Sao Tome and Principe', 'SA': 'Saudi Arabia', 'SN': 'Senegal', 'RS': 'Serbia', 'SC': 'Seychelles', 'SL': 'Sierra Leone', 'SG': 'Singapore', 'SX': 'Sint Maarten (Dutch part)', 'SK': 'Slovakia', 'SI': 'Slovenia', 'SB': 'Solomon Islands', 'SO': 'Somalia', 'ZA': 'South Africa', 'GS': 'South Georgia and the South Sandwich Islands', 'SS': 'South Sudan', 'ES': 'Spain', 'LK': 'Sri Lanka', 'SD': 'Sudan', 'SR': 'Suriname', 'SJ': 'Svalbard and Jan Mayen', 'SZ': 'Eswatini', 'SE': 'Sweden', 'CH': 'Switzerland', 'SY': 'Syrian Arab Republic', 'TW': 'Taiwan, Province of China', 'TJ': 'Tajikistan', 'TZ': 'Tanzania, United Republic of', 'TH': 'Thailand', 'TL': 'Timor-Leste', 'TG': 'Togo', 'TK': 'Tokelau', 'TO': 'Tonga', 'TT': 'Trinidad and Tobago', 'TN': 'Tunisia', 'TR': 'Türkiye', 'TM': 'Turkmenistan', 'TC': 'Turks and Caicos Islands', 'TV': 'Tuvalu', 'UG': 'Uganda', 'UA': 'Ukraine', 'AE': 'United Arab Emirates', 'GB': 'United Kingdom of Great Britain and Northern Ireland', 'US': 'United States of America', 'UM': 'United States Minor Outlying Islands', 'UY': 'Uruguay', 'UZ': 'Uzbekistan', 'VU': 'Vanuatu', 'VE': 'Venezuela, Bolivarian Republic of', 'VN': 'Viet Nam', 'VG': 'Virgin Islands, British', 'VI': 'Virgin Islands, U.S.', 'WF': 'Wallis and Futuna', 'EH': 'Western Sahara', 'YE': 'Yemen', 'ZM': 'Zambia', 'ZW': 'Zimbabwe', 'XX': 'Unknown', 'T1': 'Tor'} 
# XX and T1 are provided by CloudFlare, which are not ISO3166 standard

TF = [False, True]

def convert_quotation(s):
    s = str(s)
    return s.replace("\\'","'").replace("'", "\\'")

def nint(t):
    try:
        if t is None:
            return 0
        return int(t)
    except:
        return 0

def genrid():
    return str(int(time.time()*10000000)) + str(random.randint(0, 10000)).zfill(5)

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
    if abbr.upper() in ISO3166_COUNTRIES.keys():
        return convert_quotation(ISO3166_COUNTRIES[abbr.upper()])
    else:
        return ""

def getRequestCountry(request, abbr = False):
    if "cf-ipcountry" in request.headers.keys():
        country = request.headers["cf-ipcountry"]
        if country.upper() in ISO3166_COUNTRIES.keys(): # makre sure abbr is a valid country code
            if abbr:
                return convert_quotation(request.headers["cf-ipcountry"])
            else:
                return convert_quotation(ISO3166_COUNTRIES[country.upper()])
    return ""

def getUserAgent(request):
    if "user-agent" in request.headers.keys():
        if len(request.headers["user-agent"]) <= 200:
            return convert_quotation(request.headers["user-agent"])
        return ""
    else:
        return ""

cuserinfo = {} # user info cache

async def getAvatarSrc(dhrid, userid):
    await aiosql.execute(dhrid, f"SELECT discordid, avatar FROM user WHERE userid = {userid}")
    t = await aiosql.fetchall(dhrid)
    discordid = str(t[0][0])
    avatar = str(t[0][1])
    src = ""
    if avatar.startswith("a_"):
        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".gif"
    else:
        src = "https://cdn.discordapp.com/avatars/" + discordid + "/" + avatar + ".png"
    return src

async def getUserInfo(dhrid, userid = -1, discordid = -1, privacy = False, tell_deleted = False):
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
    
    await aiosql.execute(dhrid, f"SELECT name, userid, discordid, avatar, roles FROM user WHERE {query}")
    p = await aiosql.fetchall(dhrid)
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

def bGetUserInfo(userid = -1, discordid = -1, privacy = False, tell_deleted = False):
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
    
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"SELECT name, userid, discordid, avatar, roles FROM user WHERE {query}")
    p = cur.fetchall()
    cur.close()
    conn.close()
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

async def activityUpdate(dhrid, discordid, activity):
    if int(discordid) <= 0:
        return
    activity = convert_quotation(activity)
    await aiosql.execute(dhrid, f"SELECT timestamp FROM user_activity WHERE discordid = {discordid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        last_timestamp = t[0][0]
        if int(time.time()) - last_timestamp <= 3:
            return
        await aiosql.execute(dhrid, f"UPDATE user_activity SET activity = '{activity}', timestamp = {int(time.time())} WHERE discordid = {discordid}")
    else:
        await aiosql.execute(dhrid, f"INSERT INTO user_activity VALUES ({discordid}, '{activity}', {int(time.time())})")
    await aiosql.commit(dhrid)
    
discord_message_queue = []

def QueueDiscordMessage(channelid, data):
    global discord_message_queue
    if config.discord_bot_token == "":
        return
    discord_message_queue.append((channelid, data))

def ProcessDiscordMessage(): # thread
    global discord_message_queue
    global config
    lastRLAclear = 0
    headers = {"Authorization": f"Bot {config.discord_bot_token}", "Content-Type": "application/json"}
    while 1:
        try:
            # combined thread
            try:
                if time.time() - lastRLAclear > 30:
                    aiosql.release()
                    
                    conn = genconn()
                    cur = conn.cursor()
                    cur.execute(f"DELETE FROM ratelimit WHERE first_request_timestamp <= {round(time.time() - 86400)}")
                    cur.execute(f"DELETE FROM ratelimit WHERE endpoint = '429-error' AND first_request_timestamp <= {round(time.time() - 60)}")
                    cur.execute(f"DELETE FROM session WHERE timestamp < {int(time.time()) - 86400 * 30}")
                    cur.execute(f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
                    lastRLAclear = time.time()
                    conn.commit()
                    cur.close()
                    conn.close()
            except:
                pass

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
                conn = genconn()
                cur = conn.cursor()
                cur.execute(f"DELETE FROM settings WHERE skey = 'discord-notification' AND sval = '{channelid}'")
                cur.execute(f"DELETE FROM settings WHERE skey = 'event-notification' AND sval = '{channelid}'")
                conn.commit()
                cur.close()
                conn.close()
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

async def CheckDiscordNotification(dhrid, discordid):
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'discord-notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return False
    ret = t[0][0]
    if ret == "disabled":
        return False
    return ret

async def SendDiscordNotification(dhrid, discordid, data):
    t = await CheckDiscordNotification(dhrid, discordid)
    if t == False:
        return
    QueueDiscordMessage(t, data)

async def GetUserLanguage(dhrid, discordid, default_language = ""):
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        return default_language
    return t[0][0]

def bGetUserLanguage(discordid, default_language = ""):
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
    t = cur.fetchall()
    cur.close()
    conn.close()
    if len(t) == 0:
        return default_language
    return t[0][0]

async def CheckNotificationEnabled(dhrid, notification_type, discordid):
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return False
    return True

async def notification(dhrid, notification_type, discordid, content, no_drivershub_notification = False, \
        no_discord_notification = False, discord_embed = {}):
    if int(discordid) <= 0:
        return
    
    settings = {"drivershub": False, "discord": False, "login": False, "dlog": False, "member": False, "application": False, "challenge": False, "division": False, "event": False}

    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'notification'")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        d = t[0][0].split(",")
        for dd in d:
            if dd in settings.keys():
                settings[dd] = True

    if notification_type in settings.keys() and not settings[notification_type]:
        return

    if settings["drivershub"] and not no_drivershub_notification:
        await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE skey = 'nxtnotificationid'")
        t = await aiosql.fetchall(dhrid)
        nxtnotificationid = int(t[0][0])
        await aiosql.execute(dhrid, f"UPDATE settings SET sval = '{nxtnotificationid + 1}' WHERE skey = 'nxtnotificationid'")
        await aiosql.execute(dhrid, f"INSERT INTO user_notification VALUES ({nxtnotificationid}, {discordid}, '{convert_quotation(content)}', {int(time.time())}, 0)")
        await aiosql.commit(dhrid)
    
    if settings["discord"] and not no_discord_notification:
        if discord_embed != {}:
            await SendDiscordNotification(dhrid, discordid, {"embeds": [{"title": discord_embed["title"], 
                "description": discord_embed["description"], "fields": discord_embed["fields"], "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]})
        else:
            await SendDiscordNotification(dhrid, discordid, {"embeds": [{"title": ml.tr(None, "notification", force_lang = await GetUserLanguage(dhrid, discordid, "en")), 
                "description": content, "footer": {"text": config.name, "icon_url": config.logo_url}, \
                "timestamp": str(datetime.now()), "color": config.intcolor}]})

async def ratelimit(dhrid, request, ip, endpoint, limittime, limitcnt):
    await aiosql.execute(dhrid, f"SELECT first_request_timestamp, endpoint FROM ratelimit WHERE ip = '{ip}' AND endpoint LIKE 'ip-ban-%'")
    t = await aiosql.fetchall(dhrid)
    maxban = 0
    for tt in t:
        frt = tt[0]
        bansec = int(tt[1].split("-")[-1])
        maxban = max(frt + bansec, maxban)
        if maxban < int(time.time()):
            await aiosql.execute(dhrid, f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-{bansec}'")
            await aiosql.commit(dhrid)
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
    await aiosql.execute(dhrid, f"SELECT SUM(request_count) FROM ratelimit WHERE ip = '{ip}' AND first_request_timestamp > {int(time.time() - 60)}")
    t = await aiosql.fetchall(dhrid)
    if t[0][0] != None and t[0][0] > 150:
        # more than 150r/m combined
        # including 429 requests
        # 10min ip ban
        await aiosql.execute(dhrid, f"DELETE FROM ratelimit WHERE ip = '{ip}' AND endpoint = 'ip-ban-600'")
        await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', 'ip-ban-600', {int(time.time())}, 0)")
        await aiosql.commit(dhrid)
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
    await aiosql.execute(dhrid, f"SELECT first_request_timestamp, request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', '{endpoint}', {int(time.time())}, 1)")
        await aiosql.commit(dhrid)
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
            await aiosql.execute(dhrid, f"UPDATE ratelimit SET first_request_timestamp = {int(time.time())}, request_count = 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
            await aiosql.commit(dhrid)
            resp_headers = {}
            resp_headers["X-RateLimit-Limit"] = str(limitcnt)
            resp_headers["X-RateLimit-Remaining"] = str(limitcnt - 1)
            resp_headers["X-RateLimit-Reset"] = str(int(time.time()) + limittime)
            resp_headers["X-RateLimit-Reset-After"] = str(limittime)
            return (False, resp_headers)
        else:
            if request_count + 1 > limitcnt:
                await aiosql.execute(dhrid, f"SELECT request_count FROM ratelimit WHERE ip = '{ip}' AND endpoint = '429-error'")
                t = await aiosql.fetchall(dhrid)
                if len(t) > 0:
                    await aiosql.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '429-error'")
                    await aiosql.commit(dhrid)
                else:
                    await aiosql.execute(dhrid, f"INSERT INTO ratelimit VALUES ('{ip}', '429-error', {int(time.time())}, 1)")
                    await aiosql.commit(dhrid)

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
                await aiosql.execute(dhrid, f"UPDATE ratelimit SET request_count = request_count + 1 WHERE ip = '{ip}' AND endpoint = '{endpoint}'")
                await aiosql.commit(dhrid)
                resp_headers = {}
                resp_headers["X-RateLimit-Limit"] = str(limitcnt)
                resp_headers["X-RateLimit-Remaining"] = str(limitcnt - request_count - 1)
                resp_headers["X-RateLimit-Reset"] = str(first_request_timestamp + limittime)
                resp_headers["X-RateLimit-Reset-After"] = str(limittime - (int(time.time()) - first_request_timestamp))
                return (False, resp_headers)

async def auth(dhrid, authorization, request, check_ip_address = True, allow_application_token = False, check_member = True, required_permission = []):
    # authorization header basic check
    if authorization is None:
        return {"error": True, "descriptor": "Unauthorized", "code": 401}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        return {"error": True, "descriptor": "Unauthorized", "code": 401}
    
    tokentype = authorization.split(" ")[0]
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        return {"error": True, "descriptor": "Unauthorized", "code": 401}

    # application token
    if tokentype == "Application":
        # check if allowed
        if not allow_application_token:
            return {"error": True, "descriptor": ml.tr(request, "application_token_prohibited"), "code": 401}

        # validate token
        await aiosql.execute(dhrid, f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            return {"error": True, "descriptor": "Unauthorized", "code": 401}
        discordid = t[0][0]

        # application token will skip ip check

        # additional check
        
        # this should not happen but just in case
        await aiosql.execute(dhrid, f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = await aiosql.fetchall(dhrid)
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

        await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
        t = await aiosql.fetchall(dhrid)
        language = ""
        if len(t) != 0:
            language = t[0][0]

        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "language": language, "application_token": True}

    # bearer token
    elif tokentype == "Bearer":
        await aiosql.execute(dhrid, f"SELECT discordid, ip, country, last_used_timestamp, user_agent FROM session WHERE token = '{stoken}'")
        t = await aiosql.fetchall(dhrid)
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
            await aiosql.execute(dhrid, f"DELETE FROM session WHERE token = '{stoken}'")
            await aiosql.commit(dhrid)
            return {"error": True, "descriptor": "Unauthorized", "code": 401}

        if ip != request.client.host:
            await aiosql.execute(dhrid, f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        if curCountry != country and not curCountry != "" and country != "":
            await aiosql.execute(dhrid, f"UPDATE session SET country = '{curCountry}' WHERE token = '{stoken}'")
        if getUserAgent(request) != user_agent:
            await aiosql.execute(dhrid, f"UPDATE session SET user_agent = '{getUserAgent(request)}' WHERE token = '{stoken}'")
        await aiosql.commit(dhrid)
        
        # additional check
        
        # this should not happen but just in case
        await aiosql.execute(dhrid, f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
        t = await aiosql.fetchall(dhrid)
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
            await aiosql.execute(dhrid, f"UPDATE session SET last_used_timestamp = {int(time.time())} WHERE token = '{stoken}'")
            await aiosql.commit(dhrid)

        await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE discordid = '{discordid}' AND skey = 'language'")
        t = await aiosql.fetchall(dhrid)
        language = ""
        if len(t) != 0:
            language = t[0][0]
            
        return {"error": False, "discordid": discordid, "userid": userid, "name": name, "roles": roles, "language": language, "application_token": False}
    
    return {"error": True, "descriptor": "Unauthorized", "code": 401}

async def AuditLog(dhrid, userid, text):
    try:
        name = "Unknown User"
        if userid == -999:
            name = "System"
        elif userid == -998:
            name = "Discord API"
        else:
            await aiosql.execute(dhrid, f"SELECT name FROM user WHERE userid = {userid}")
            t = await aiosql.fetchall(dhrid)
            if len(t) > 0:
                name = t[0][0]
        if userid != -998:
            await aiosql.execute(dhrid, f"INSERT INTO auditlog VALUES ({userid}, '{convert_quotation(text)}', {int(time.time())})")
            await aiosql.commit(dhrid)
        if config.webhook_audit != "":
            async with ClientSession() as session:
                webhook = Webhook.from_url(config.webhook_audit, session=session)
                embed = Embed(description = text, color = config.rgbcolor)
                if userid not in [-999, -998]:
                    embed.set_footer(text = f"{name} (ID {userid})", icon_url = await getAvatarSrc(dhrid, userid))
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