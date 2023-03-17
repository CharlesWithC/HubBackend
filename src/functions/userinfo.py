# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time

from app import config
from db import aiosql, genconn
from functions.dataop import *
from functions.general import *
from functions.security import auth
from static import *

async def getHighestActiveRole(dhrid):
    for roleid in ROLES.keys():
        await aiosql.execute(dhrid, f"SELECT uid FROM user WHERE roles LIKE '%,{roleid},%'")
        t = await aiosql.fetchall(dhrid)
        if len(t) > 0:
            return roleid
    return list(ROLES.keys())[0]

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

async def ActivityUpdate(dhrid, uid, activity):
    if uid is None or int(uid) <= 0:
        return
    activity = convert_quotation(activity)
    await aiosql.execute(dhrid, f"SELECT timestamp FROM user_activity WHERE uid = {uid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        last_timestamp = t[0][0]
        if int(time.time()) - last_timestamp <= 3:
            return
        await aiosql.execute(dhrid, f"UPDATE user_activity SET activity = '{activity}', timestamp = {int(time.time())} WHERE uid = {uid}")
    else:
        await aiosql.execute(dhrid, f"INSERT INTO user_activity VALUES ({uid}, '{activity}', {int(time.time())})")
    await aiosql.commit(dhrid)
    
cuserinfo = {} # user info cache (15 seconds)
cactivity = {} # activity cache (2 seconds)

def ClearUserCache():
    global cuserinfo
    global cactivity
    users = list(cuserinfo.keys())
    for user in users:
        if int(time.time()) > cuserinfo[user]["expire"]:
            del cuserinfo[user]
    users = list(cactivity.keys())
    for user in users:
        if int(time.time()) > cactivity[user]["expire"]:
            del cactivity[user]

async def GetUserInfo(dhrid, request, userid = -1, discordid = -1, uid = -1, privacy = False, tell_deleted = False, include_email = False, ignore_activity = False):
    if userid == -999:
        return {"uid": None, "userid": None, "name": "System", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        
    if privacy:
        return {"uid": None, "userid": None, "name": "[Protected]", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}

    if userid == -1 and discordid == -1 and uid == -1:
        if not tell_deleted:
            return {"uid": None, "userid": None, "name": "Unknown", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        else:
            return {"uid": None, "userid": None, "name": "Unknown", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None, "is_deleted": True}

    ClearUserCache()
    global cuserinfo
    global cactivity
    
    if userid != -1 and f"userid={userid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"userid={userid}"]["expire"]:
            uid = cuserinfo[f"userid={userid}"]["uid"]
    if discordid != -1 and f"discordid={discordid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"discordid={discordid}"]["expire"]:
            uid = cuserinfo[f"discordid={discordid}"]["uid"]
    if uid != -1 and f"uid={uid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"uid={uid}"]["expire"]:
            ret = cuserinfo[f"uid={uid}"]["data"]
            if ignore_activity:
                ret["activity"] = None
            if not ignore_activity and (f"uid={uid}" not in cactivity.keys() or \
                f"uid={uid}" in cactivity.keys() and int(time.time()) >= cactivity[f"uid={uid}"]["expire"]):
                activity = None
                await aiosql.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
                ac = await aiosql.fetchall(dhrid)
                if len(ac) != 0:
                    if int(time.time()) - ac[0][1] >= 300:
                        activity = {"status": "offline", "last_seen": ac[0][1]}
                    elif int(time.time()) - ac[0][1] >= 120:
                        activity = {"status": "online", "last_seen": ac[0][1]}
                    else:
                        activity = {"status": ac[0][0], "last_seen": ac[0][1]}
                    cactivity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
                else:
                    cactivity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}
                ret["activity"] = cactivity[f"uid={uid}"]["data"]
            return ret

    query = ""
    if userid != -1:
        query = f"userid = {userid}"
    elif discordid != -1:
        query = f"discordid = {discordid}"
    elif uid != -1:
        query = f"uid = {uid}"
    
    await aiosql.execute(dhrid, f"SELECT uid, userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, mfa_secret, join_timestamp FROM user WHERE {query}")
    p = await aiosql.fetchall(dhrid)
    if len(p) == 0:
        uid = None if uid == -1 else uid
        userid = None if userid == -1 else userid
        discordid = None if discordid == -1 else discordid
        if not tell_deleted:
            return {"uid": uid, "userid": userid, "name": "Unknown", "email": None, "discordid": str(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        else:
            return {"uid": uid, "userid": userid, "name": "Unknown", "email": None, "discordid": str(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None, "is_deleted": True}

    uid = p[0][0]

    if not request is None:
        if "authorization" in request.headers.keys():
            authorization = request.headers["authorization"]
            au = await auth(dhrid, authorization, request)
            if not au["error"]:
                roles = au["roles"]
                for i in roles:
                    if int(i) in config.perms.admin:
                        include_email = True
                    if int(i) in config.perms.hr or int(i) in config.perms.hrm:
                        include_email = True
                if au["discordid"] == p[0][2]:
                    include_email = True

    roles = p[0][6].split(",")
    roles = [int(x) for x in roles if isint(x)]
    mfa_secret = p[0][10]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True
    email = p[0][3]
    if email.endswith("!"): # unverified
        email = email[:-1]
    if not include_email:
        email = ""

    activity = None
    await aiosql.execute(dhrid, f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
    ac = await aiosql.fetchall(dhrid)
    if len(ac) != 0:
        if int(time.time()) - ac[0][1] >= 300:
            activity = {"status": "offline", "last_seen": ac[0][1]}
        elif int(time.time()) - ac[0][1] >= 120:
            activity = {"status": "online", "last_seen": ac[0][1]}
        else:
            activity = {"status": ac[0][0], "last_seen": ac[0][1]}
        cactivity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
    else:
        cactivity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}

    if p[0][1] != -1:
        cuserinfo[f"userid={p[0][1]}"] = {"uid": uid, "expire": int(time.time()) + 15}
    if p[0][7] != -1:
        cuserinfo[f"discordid={p[0][7]}"] = {"uid": uid, "expire": int(time.time()) + 15}

    userid = p[0][1]
    if userid == -1:
        userid = None

    cuserinfo[f"uid={uid}"] = {"data": {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": str(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}, "expire": int(time.time()) + 15}
    
    return {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": str(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}

def bGetUserInfo(userid = -1, discordid = -1, uid = -1, privacy = False, tell_deleted = False, include_email = False, ignore_activity = False):
    if userid == -999:
        return {"uid": None, "userid": None, "name": "System", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        
    if privacy:
        return {"uid": None, "userid": None, "name": "[Protected]", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}

    if userid == -1 and discordid == -1 and uid == -1:
        if not tell_deleted:
            return {"uid": None, "userid": None, "name": "Unknown", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        else:
            return {"uid": None, "userid": None, "name": "Unknown", "email": None, "discordid": None, "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None, "is_deleted": True}

    ClearUserCache()
    global cuserinfo
    global cactivity
    
    if userid != -1 and f"userid={userid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"userid={userid}"]["expire"]:
            uid = cuserinfo[f"userid={userid}"]["uid"]
    if discordid != -1 and f"discordid={discordid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"discordid={discordid}"]["expire"]:
            uid = cuserinfo[f"discordid={discordid}"]["uid"]
    if uid != -1 and f"uid={uid}" in cuserinfo.keys():
        if int(time.time()) < cuserinfo[f"uid={uid}"]["expire"]:
            ret = cuserinfo[f"uid={uid}"]["data"]
            if not ignore_activity and (f"uid={uid}" not in cactivity.keys() or \
                f"uid={uid}" in cactivity.keys() and int(time.time()) >= cactivity[f"uid={uid}"]["expire"]):
                activity = None
                conn = genconn()
                cur = conn.cursor()
                cur.execute(f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
                ac = cur.fetchall()
                if len(ac) != 0:
                    if int(time.time()) - ac[0][1] >= 300:
                        activity = {"status": "offline", "last_seen": ac[0][1]}
                    elif int(time.time()) - ac[0][1] >= 120:
                        activity = {"status": "online", "last_seen": ac[0][1]}
                    else:
                        activity = {"status": ac[0][0], "last_seen": ac[0][1]}
                    cactivity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
                else:
                    cactivity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}
                ret["activity"] = cactivity[f"uid={uid}"]["data"]
                cur.close()
                conn.close()
            return ret

    query = ""
    if userid != -1:
        query = f"userid = '{userid}'"
    elif discordid != -1:
        query = f"discordid = '{discordid}'"
    elif uid != -1:
        query = f"uid = '{uid}'"
    
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"SELECT uid, userid, name, email, avatar, bio, roles, discordid, steamid, truckersmpid, mfa_secret, join_timestamp FROM user WHERE {query}")
    p = cur.fetchall()
    if len(p) == 0:
        cur.close()
        conn.close()
        uid = None if uid == -1 else uid
        userid = None if userid == -1 else userid
        discordid = None if discordid == -1 else discordid
        if not tell_deleted:
            return {"uid": uid, "userid": userid, "name": "Unknown", "email": None, "discordid": str(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None}
        else:
            return {"uid": uid, "userid": userid, "name": "Unknown", "email": None, "discordid": str(discordid), "steamid": None, "truckersmpid": None, "avatar": "", "bio": "", "roles": [], "activity": None, "mfa": False, "join_timestamp": None, "is_deleted": True}

    uid = p[0][0]

    roles = p[0][6].split(",")
    roles = [int(x) for x in roles if isint(x)]
    mfa_secret = p[0][10]
    mfa_enabled = False
    if mfa_secret != "":
        mfa_enabled = True
    email = p[0][3]
    if email.endswith("!"): # unverified
        email = email[:-1]
    if not include_email:
        email = ""

    activity = None
    cur.execute(f"SELECT activity, timestamp FROM user_activity WHERE uid = {uid}")
    ac = cur.fetchall()
    if len(ac) != 0:
        if int(time.time()) - ac[0][1] >= 300:
            activity = {"status": "offline", "last_seen": ac[0][1]}
        elif int(time.time()) - ac[0][1] >= 120:
            activity = {"status": "online", "last_seen": ac[0][1]}
        else:
            activity = {"status": ac[0][0], "last_seen": ac[0][1]}
        cactivity[f"uid={uid}"] = {"data": activity, "expire": int(time.time()) + 2}
    else:
        cactivity[f"uid={uid}"] = {"data": None, "expire": int(time.time()) + 2}

    cur.close()
    conn.close()
    
    userid = p[0][1]
    if userid == -1:
        userid = None

    if p[0][1] != -1:
        cuserinfo[f"userid={p[0][1]}"] = {"uid": uid, "expire": int(time.time()) + 15}
    if p[0][7] != -1:
        cuserinfo[f"discordid={p[0][7]}"] = {"uid": uid, "expire": int(time.time()) + 15}
        
    cuserinfo[f"uid={uid}"] = {"data": {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": str(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}, "expire": int(time.time()) + 15}
    
    return {"uid": uid, "userid": userid, "name": p[0][2], "email": email, "discordid": str(p[0][7]), "steamid": nstr(p[0][8]), "truckersmpid": p[0][9], "avatar": p[0][4], "bio": b64d(p[0][5]), "roles": roles, "activity": activity, "mfa": mfa_enabled, "join_timestamp": p[0][11]}

clanguage = {} # language cache (3 seconds)

def ClearUserLanguageCache():
    global clanguage
    users = list(clanguage.keys())
    for user in users:
        if int(time.time()) > clanguage[user]["expire"]:
            del clanguage[user]

async def GetUserLanguage(dhrid, uid, default_language = ""):
    ClearUserLanguageCache()

    global clanguage
    if uid in clanguage.keys() and int(time.time()) <= clanguage[uid]["expire"]:
        return clanguage[uid]["language"]
    await aiosql.execute(dhrid, f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'language'")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        clanguage[uid] = {"language": default_language, "expire": int(time.time()) + 3}
        return default_language
    clanguage[uid] = {"language": t[0][0], "expire": int(time.time()) + 3}
    return t[0][0]

def bGetUserLanguage(uid, default_language = ""):
    ClearUserLanguageCache()

    global clanguage
    if uid in clanguage.keys() and int(time.time()) <= clanguage[uid]["expire"]:
        return clanguage[uid]["language"]
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE uid = '{uid}' AND skey = 'language'")
    t = cur.fetchall()
    cur.close()
    conn.close()
    if len(t) == 0:
        clanguage[uid] = {"language": default_language, "expire": int(time.time()) + 3}
        return default_language
    clanguage[uid] = {"language": t[0][0], "expire": int(time.time()) + 3}
    return t[0][0]