# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, math
from datetime import datetime
import requests

from app import app, config
from db import newconn
from functions import *

@app.get(f"/{config.vtcprefix}/event")
async def getEvent(request: Request, response: Response, authorization: str = Header(None), page: Optional[int] = 1, eventid: Optional[int] = -1):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    userid = -1
    if stoken != "guest":
        isapptoken = False
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
            t = cur.fetchall()
            if len(t) == 0:
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
            isapptoken = True
        discordid = t[0][0]
        if not isapptoken:
            ip = t[0][1]
            orgiptype = 4
            if iptype(ip) == "ipv6":
                orgiptype = 6
            curiptype = 4
            if iptype(request.client.host) == "ipv6":
                curiptype = 6
            if orgiptype != curiptype:
                cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                conn.commit()
            else:
                if ip != request.client.host:
                    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                    conn.commit()
                    # response.status_code = 401
                    return {"error": True, "descriptor": "401: Unauthroized"}
        cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        userid = t[0][0]
        roles = t[0][1].split(",")
    limit = ""
    if userid == -1 or not str(config.perms.driver[0]) in roles:
        limit = "AND pvt = 0"

    if page <= 0:
        page = 1

    if eventid != -1:
        cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid = {eventid} {limit}")
        t = cur.fetchall()
        if len(t) == 0:
            return {"error": True, "descriptor": "Event not found"}
        tt = t[0]
        attendee = tt[9].split(",")
        vote = tt[10].split(",")
        if userid == -1:
            attendee = []
            vote = []
        while "" in attendee:
            attendee.remove("")
        while "" in vote:
            vote.remove("")
        attendeetxt = ""
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendeetxt += f"{name}, "
        attendeetxt = attendeetxt[:-2]
        votetxt = ""
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            votetxt += f"{name}, "
        votetxt = votetxt[:-2]
        return {"error": False, "response": {"eventid": tt[0], "title": b64d(tt[8]), "tmplink": b64d(tt[1]), "departure": b64d(tt[2]), "destination": b64d(tt[3]), "private": tt[11],\
            "distance": b64d(tt[4]), "mts": tt[5], "dts": tt[6], "img": b64d(tt[7]).split(","), "attendee": attendeetxt, "attendeeid": ",".join(attendee), "vote": votetxt, "voteid": ",".join(vote)}}

    cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid >= 0 AND mts >= {int(time.time()) - 86400} {limit} ORDER BY mts ASC LIMIT {(page-1) * 10}, 10")
    t = cur.fetchall()
    ret = []
    for tt in t:
        attendee = tt[9].split(",")
        vote = tt[10].split(",")
        if userid == -1:
            attendee = []
            vote = []
        while "" in attendee:
            attendee.remove("")
        while "" in vote:
            vote.remove("")
        attendeetxt = ""
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendeetxt += f"{name}, "
        attendeetxt = attendeetxt[:-2]
        votetxt = ""
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            votetxt += f"{name}, "
        votetxt = votetxt[:-2]
        ret.append({"eventid": tt[0], "title": b64d(tt[8]), "tmplink": b64d(tt[1]), "departure": b64d(tt[2]), "destination": b64d(tt[3]), "private": tt[11],\
            "distance": b64d(tt[4]), "mts": tt[5], "dts": tt[6], "img": b64d(tt[7]).split(","), "attendee": attendeetxt, "attendeeid": ",".join(attendee), "vote": votetxt, "voteid": ",".join(vote)})
    
    cur.execute(f"SELECT COUNT(*) FROM event WHERE eventid >= 0 AND mts >= {int(time.time()) - 86400} {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
        
    cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid >= 0 AND mts < {int(time.time()) - 86400} {limit} ORDER BY mts ASC LIMIT {max((page-1) * 10 - tot,0)}, 10")
    t = cur.fetchall()
    for tt in t:
        attendee = tt[9].split(",")
        vote = tt[10].split(",")
        if userid == -1:
            attendee = []
            vote = []
        while "" in attendee:
            attendee.remove("")
        while "" in vote:
            vote.remove("")
        attendeetxt = ""
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendeetxt += f"{name}, "
        attendeetxt = attendeetxt[:-2]
        votetxt = ""
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            votetxt += f"{name}, "
        votetxt = votetxt[:-2]
        ret.append({"eventid": tt[0], "title": b64d(tt[8]), "tmplink": b64d(tt[1]), "departure": b64d(tt[2]), "destination": b64d(tt[3]), "private": tt[11],\
            "distance": b64d(tt[4]), "mts": tt[5], "dts": tt[6], "img": b64d(tt[7]).split(","), "attendee": attendeetxt, "attendeeid": ",".join(attendee), "vote": votetxt, "voteid": ",".join(vote)})
    
    cur.execute(f"SELECT COUNT(*) FROM event WHERE eventid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret[:10], "page": page, "tot": tot}}

@app.get(f"/{config.vtcprefix}/event/full")
async def getFullEvent(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer ") and not authorization.startswith("Application "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    userid = -1
    if stoken != "guest":
        isapptoken = False
        cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
        t = cur.fetchall()
        if len(t) == 0:
            cur.execute(f"SELECT discordid FROM appsession WHERE token = '{stoken}'")
            t = cur.fetchall()
            if len(t) == 0:
                # response.status_code = 401
                return {"error": True, "descriptor": "401: Unauthroized"}
            isapptoken = True
        discordid = t[0][0]
        if not isapptoken:
            ip = t[0][1]
            orgiptype = 4
            if iptype(ip) == "ipv6":
                orgiptype = 6
            curiptype = 4
            if iptype(request.client.host) == "ipv6":
                curiptype = 6
            if orgiptype != curiptype:
                cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
                conn.commit()
            else:
                if ip != request.client.host:
                    cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
                    conn.commit()
                    # response.status_code = 401
                    return {"error": True, "descriptor": "401: Unauthroized"}
        cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
        t = cur.fetchall()
        if len(t) == 0:
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
        userid = t[0][0]
        roles = t[0][1].split(",")
    limit = ""
    if userid == -1 or not str(config.perms.driver[0]) in roles:
        limit = "AND pvt = 0"

    cur.execute(f"SELECT eventid, title, mts FROM event WHERE eventid >= 0 {limit} ORDER BY mts")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"eventid": tt[0], "title": b64d(tt[1]), "mts": tt[2]})

    return {"error": False, "response": {"list": ret}}

@app.post(f"/{config.vtcprefix}/event/vote")
async def eventVote(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    userid = t[0][0]
    roles = t[0][1]
    
    ok = False
    for i in roles:
        if int(i) in config.perms.driver:
            ok = True

    if not ok:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    eventid = int(form["eventid"])
    cur.execute(f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        return {"error": True, "descriptor": "Event not found"}
    vote = t[0][0].split(",")
    if str(userid) in vote:
        vote.remove(str(userid))
        cur.execute(f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        conn.commit()
        return {"error": False, "response": "Vote removed"}
    else:
        vote.append(str(userid))
        cur.execute(f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        conn.commit()
        return {"error": False, "response": "Vote added"}

@app.post(f"/{config.vtcprefix}/event")
async def postEvent(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")
        
    ok = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxteventid'")
    t = cur.fetchall()
    nxteventid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {nxteventid+1} WHERE skey = 'nxteventid'")
    conn.commit()

    form = await request.form()
    title = b64e(form["title"])
    tmplink = b64e(form["tmplink"])
    departure = b64e(form["departure"])
    destination = b64e(form["destination"])
    distance = b64e(form["distance"])
    mts = int(form["mts"])
    dts = int(form["dts"])
    img = b64e(form["img"])
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1

    cur.execute(f"INSERT INTO event VALUES ({nxteventid}, {adminid}, '{tmplink}', '{departure}', '{destination}', '{distance}', {mts}, {dts}, '{img}', {pvt}, '{title}', '', 0, '')")
    await AuditLog(adminid, f"Created event #{nxteventid}")
    conn.commit()

    return {"error": False, "response": {"message": "Event created.", "eventid": nxteventid}}

@app.patch(f"/{config.vtcprefix}/event")
async def patchEvent(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles, name FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    adminname = t[0][2]
    while "" in adminroles:
        adminroles.remove("")

    ok = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    eventid = int(form["eventid"])
    title = b64e(form["title"])
    tmplink = b64e(form["tmplink"])
    departure = b64e(form["departure"])
    destination = b64e(form["destination"])
    distance = b64e(form["distance"])
    mts = int(form["mts"])
    dts = int(form["dts"])
    img = b64e(form["img"])
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1

    cur.execute(f"SELECT userid FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Event not found!"}
    creator = t[0][0]
    
    cur.execute(f"UPDATE event SET title = '{title}', tmplink = '{tmplink}', departure = '{departure}', destination = '{destination}', \
        distance = '{distance}', mts = {mts}, dts = {dts}, img = '{img}', pvt = {pvt} WHERE eventid = {eventid}")
    await AuditLog(adminid, f"Updated event #{eventid}")
    conn.commit()

    return {"error": False, "response": {"message": "Event updated.", "eventid": eventid}}

@app.delete(f"/{config.vtcprefix}/event")
async def deleteEvent(eventid: int, request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")

    ok = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    cur.execute(f"SELECT * FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Event not found!"}
    
    cur.execute(f"UPDATE event SET eventid = -eventid WHERE eventid = {eventid}")
    await AuditLog(adminid, f"Deleted event #{eventid}")
    conn.commit()

    return {"error": False, "response": {"message": "Event deleted."}}

@app.post(f"/{config.vtcprefix}/event/attendee")
async def updateEventAttendee(request: Request, response: Response, authorization: str = Header(None)):
    if authorization is None:
        # response.status_code = 401
        return {"error": True, "descriptor": "No authorization header"}
    if not authorization.startswith("Bearer "):
        # response.status_code = 401
        return {"error": True, "descriptor": "Invalid authorization header"}
    stoken = authorization.split(" ")[1]
    if not stoken.replace("-","").isalnum():
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT discordid, ip FROM session WHERE token = '{stoken}'")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    discordid = t[0][0]
    ip = t[0][1]
    orgiptype = 4
    if iptype(ip) == "ipv6":
        orgiptype = 6
    curiptype = 4
    if iptype(request.client.host) == "ipv6":
        curiptype = 6
    if orgiptype != curiptype:
        cur.execute(f"UPDATE session SET ip = '{request.client.host}' WHERE token = '{stoken}'")
        conn.commit()
    else:
        if ip != request.client.host:
            cur.execute(f"DELETE FROM session WHERE token = '{stoken}'")
            conn.commit()
            # response.status_code = 401
            return {"error": True, "descriptor": "401: Unauthroized"}
    cur.execute(f"SELECT userid, roles FROM user WHERE discordid = {discordid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}
    adminid = t[0][0]
    adminroles = t[0][1].split(",")
    while "" in adminroles:
        adminroles.remove("")
        
    ok = False
    for i in adminroles:
        if int(i) in config.perms.admin or int(i) in config.perms.event:
            ok = True
    
    if not ok:
        # response.status_code = 401
        return {"error": True, "descriptor": "401: Unauthroized"}

    form = await request.form()
    eventid = int(form["eventid"])
    attendees = form["attendees"].replace(" ","").split(",")
    while "" in attendees:
        attendees.remove("")
    points = int(form["points"])

    cur.execute(f"SELECT attendee FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        # response.status_code = 404
        return {"error": True, "descriptor": "Event not found!"}
    orgattendees = t[0][0].split(",")
    while "" in orgattendees:
        orgattendees.remove("")

    ret = f"Updated event #{eventid} attendees\n"
    ret1 = f"Given "
    cnt = 0
    for attendee in attendees:
        if attendee in orgattendees:
            continue
        attendee = int(attendee)
        cur.execute(f"SELECT name, discordid FROM user WHERE userid = {attendee}")
        t = cur.fetchall()
        if len(t) == 0:
            continue
        ret1 += f"{t[0][0]}, "
        cnt += 1
        cur.execute(f"UPDATE driver SET eventpnt = eventpnt + {points} WHERE userid = {attendee}")
    ret1 = ret1[:-2]
    ret1 += f" {points} event points.\n"
    if cnt > 0:
        ret = ret + ret1

    ret2 = f"Removed {points} from "
    cnt = 0
    for attendee in orgattendees:
        if not attendee in attendees:
            attendee = int(attendee)
            cur.execute(f"SELECT name, discordid FROM user WHERE userid = {attendee}")
            t = cur.fetchall()
            if len(t) == 0:
                continue
            ret2 += f"{t[0][0]}, "
            cur.execute(f"UPDATE driver SET eventpnt = eventpnt - {points} WHERE userid = {attendee}")
            cnt += 1
    ret2 = ret2[:-2]
    if cnt > 0:
        ret = ret + ret2

    if ret == f"Updated event #{eventid} attendees\n":
        return {"error": False, "response": {"message": "No changes made."}}

    cur.execute(f"UPDATE event SET attendee = '{','.join(attendees)}', eventpnt = {points} WHERE eventid = {eventid}")
    conn.commit()

    ret = ret.replace("'","''")
    await AuditLog(adminid, ret)
    return {"error": False, "response": {"message": ret}}