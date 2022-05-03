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