# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import base64
import hashlib
import hmac
import struct
import time


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
        x = x.zfill(6)
        ret.append(x)
    return ret

def valid_totp(otp, secret):
    return otp in get_totp_token(secret)