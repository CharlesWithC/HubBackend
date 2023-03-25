# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import re
import zlib
from base64 import b64decode, b64encode


def convertQuotation(s):
    s = str(s)
    return s.replace("\\'","'").replace("'", "\\'")

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

def nint(t):
    try:
        if t is None:
            return 0
        return int(t)
    except:
        return 0

def str2list(l):
    # converts comma-separated list str of int elements to list
    # e.g. "1,2,3" -> [1,2,3]
    l = l.split(",")
    return [int(x) for x in l if isint(x)]

def intify(l):
    return [int(x) for x in l if isint(x)]

def list2str(l):
    # converts list to comma-separated list str
    # e.g. [1,2,3] -> "1,2,3"
    l = [str(x) for x in l if isint(x)]
    return ",".join(l)

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