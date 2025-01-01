# Copyright (C) 2022-2025 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import re
import zlib
from base64 import b64decode, b64encode


def convertQuotation(s):
    s = str(s)
    s = s.replace("\\", "\\\\").replace("'", "\\'")
    return s

def nstr(t):
    if t is None:
        return None
    return str(t)

def isint(t):
    try:
        int(t)
        return True
    except:
        return False

def isfloat(t):
    try:
        float(t)
        return True
    except:
        return False

def nint(t):
    try:
        if t is None:
            return 0
        if type(t) is tuple: # db fetchone query
            return int(t[0])
        return int(t)
    except:
        return 0

def nfloat(t):
    try:
        if t is None:
            return 0
        return float(t)
    except:
        return 0

def dictF2I(data):
    if isinstance(data, float):
        return int(data)
    elif isinstance(data, dict):
        return {key: dictF2I(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [dictF2I(item) for item in data]
    else:
        return data

def deduplicate(lst):
    return list(set(lst))

def str2list(lst):
    # converts comma-separated list str of int elements to list
    # e.g. "1,2,3" -> [1,2,3]
    lst = lst.split(",")
    return [int(x) for x in lst if isint(x)]

def intify(lst):
    return [int(x) for x in lst if isint(x)]

def list2str(lst):
    # converts list to comma-separated list str
    # e.g. [1,2,3] -> "1,2,3"
    lst = [str(x) for x in lst if isint(x)]
    return ",".join(lst)

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
    st = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    if d == 0:
        return st[0]
    flag = ""
    if d < 0:
        flag = "-"
        d = abs(d)
    while d:
        ret += st[d % 62]
        d //= 62
    return flag + ret[::-1]

def b62decode(d):
    flag = 1
    if d.startswith("-"):
        flag = -1
        d = d[1:]
    ret = 0
    st = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    for i in range(len(d)):
        ret += st.find(d[i]) * 62 ** (len(d) - i - 1)
    return ret * flag

def tseparator(num):
    """Thousand Separator"""

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

def validate_regex(pattern):
    try:
        re.compile(pattern)
        return True
    except re.error:
        return False

def regex_replace(text, rules):
    for match_rule, replace_rule in rules.items():
        if validate_regex(match_rule):
            text = re.sub(match_rule, replace_rule, text)
    return text

def flatten_dict(d, parent_key='', sep=':', placeholder='<EMPTY_DICT>'):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            if v:
                items.extend(flatten_dict(v, new_key, sep=sep, placeholder=placeholder).items())
            else:
                items.append((new_key, placeholder))
        else:
            items.append((new_key, v))
    return dict(items)

def deflatten_dict(d, sep=':', placeholder='<EMPTY_DICT>', intify = False):
    deflated_dict = {}
    for k, v in d.items():
        parts = k.split(sep)
        sub_dict = deflated_dict
        for part in parts[:-1]:
            if part not in sub_dict:
                sub_dict[part] = {}
            sub_dict = sub_dict[part]
        if intify and isint(v):
            v = int(v)
        if intify and isint(parts[-1]):
            parts[-1] = int(parts[-1])
        sub_dict[parts[-1]] = {} if v == placeholder else v
    return deflated_dict
