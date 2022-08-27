# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI, Response, Request, Header
from typing import Optional
import json, time, requests, math

from app import app, config
from db import newconn
from functions import *
import multilang as ml

@app.get(f"/{config.vtc_abbr}/event")
async def getEvent(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, eventid: Optional[int] = -1, page_size: Optional[int] = 10):
    rl = ratelimit(request.client.host, 'GET /event', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = "guest"
    if authorization != None:
        stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            userid = -1
        else:
            userid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    limit = ""
    if userid == -1:
        limit = "AND pvt = 0"

    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if eventid != -1:
        cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid = {eventid} {limit}")
        t = cur.fetchall()
        if len(t) == 0:
            response.status_code = 404
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
        attendee_ret = []
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendee_ret.append({"userid": at, "name": name})
        vote_ret = []
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            vote_ret.append({"userid": vt, "name": name})
        return {"error": False, "response": {"eventid": str(tt[0]), "is_private": TF[tt[11]], "title": b64d(tt[8]), \
            "truckersmp_link": b64d(tt[1]), "departure": b64d(tt[2]), "destination": b64d(tt[3]), \
            "distance": b64d(tt[4]), "meetup_timestamp": str(tt[5]), "departure_timestamp": str(tt[6]), \
                "images": b64d(tt[7]).split(","), "attendees": attendee_ret, "votes": vote_ret}}

    cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid >= 0 AND mts >= {int(time.time()) - 86400} {limit} ORDER BY mts ASC LIMIT {(page-1) * page_size}, {page_size}")
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
        attendee_ret = []
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendee_ret.append({"userid": at, "name": name})
        vote_ret = []
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            vote_ret.append({"userid": vt, "name": name})
        ret.append({"eventid": str(tt[0]), "is_private": TF[tt[11]], "title": b64d(tt[8]), "truckersmp_link": b64d(tt[1]), \
            "departure": b64d(tt[2]), "destination": b64d(tt[3]), \
            "distance": b64d(tt[4]), "meetup_timestamp": str(tt[5]), "departure_timestamp": str(tt[6]), \
                "images": b64d(tt[7]).split(","), "attendees": attendee_ret, "votes": vote_ret})
    
    cur.execute(f"SELECT COUNT(*) FROM event WHERE eventid >= 0 AND mts >= {int(time.time()) - 86400} {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
        
    cur.execute(f"SELECT eventid, tmplink, departure, destination, distance, mts, dts, img, title, attendee, vote, pvt FROM event WHERE eventid >= 0 AND mts < {int(time.time()) - 86400} {limit} ORDER BY mts ASC LIMIT {max((page-1) * page_size - tot,0)}, {page_size}")
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
        attendee_ret = []
        for at in attendee:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {at}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            attendee_ret.append({"userid": at, "name": name})
        vote_ret = []
        for vt in vote:
            name = "Unknown"
            cur.execute(f"SELECT name FROM user WHERE userid = {vt}")
            t = cur.fetchall()
            if len(t) != 0:
                name = t[0][0]
            vote_ret.append({"userid": vt, "name": name})
        ret.append({"eventid": str(tt[0]), "is_private": TF[tt[11]], "title": b64d(tt[8]), "truckersmp_link": b64d(tt[1]), \
            "departure": b64d(tt[2]), "destination": b64d(tt[3]),\
            "distance": b64d(tt[4]), "meetup_timestamp": str(tt[5]), "departure_timestamp": str(tt[6]), \
                "images": b64d(tt[7]).split(","), "attendees": attendee_ret, "votes": vote_ret})
    
    cur.execute(f"SELECT COUNT(*) FROM event WHERE eventid >= 0 {limit}")
    t = cur.fetchall()
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"error": False, "response": {"list": ret[:page_size], "total_items": str(tot), \
        "total_pages": str(int(math.ceil(tot / page_size)))}}

@app.get(f"/{config.vtc_abbr}/event/all")
async def getAllEvent(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'GET /event/all', 180, 90)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    stoken = "guest"
    if authorization != None:
        stoken = authorization.split(" ")[1]
    userid = -1
    if stoken == "guest":
        userid = -1
    else:
        au = auth(authorization, request, allow_application_token = True)
        if au["error"]:
            userid = -1
        else:
            userid = au["userid"]
    
    conn = newconn()
    cur = conn.cursor()

    limit = ""
    if userid == -1:
        limit = "AND pvt = 0"

    cur.execute(f"SELECT eventid, title, mts FROM event WHERE eventid >= 0 {limit} ORDER BY mts")
    t = cur.fetchall()
    ret = []
    for tt in t:
        ret.append({"eventid": str(tt[0]), "title": b64d(tt[1]), "meetup_timestamp": str(tt[2])})

    return {"error": False, "response": {"list": ret}}

@app.post(f"/{config.vtc_abbr}/event/vote")
async def postEventVote(request: Request, response: Response, authorization: str = Header(None), eventid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'POST /event/vote', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = 401
        return au
    userid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    if int(eventid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}

    cur.execute(f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}
    vote = t[0][0].split(",")
    if str(userid) in vote:
        vote.remove(str(userid))
        cur.execute(f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        conn.commit()
        return {"error": False}
    else:
        vote.append(str(userid))
        cur.execute(f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        conn.commit()
        return {"error": False}

@app.post(f"/{config.vtc_abbr}/event")
async def postEvent(request: Request, response: Response, authorization: str = Header(None)):
    rl = ratelimit(request.client.host, 'POST /event', 180, 3)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    cur.execute(f"SELECT sval FROM settings WHERE skey = 'nxteventid'")
    t = cur.fetchall()
    nxteventid = int(t[0][0])
    cur.execute(f"UPDATE settings SET sval = {nxteventid+1} WHERE skey = 'nxteventid'")
    conn.commit()

    form = await request.form()
    title = b64e(form["title"])
    truckersmp_link = b64e(form["truckersmp_link"])
    departure = b64e(form["departure"])
    destination = b64e(form["destination"])
    distance = b64e(form["distance"])
    meetup_timestamp = int(form["meetup_timestamp"])
    departure_timestamp = int(form["departure_timestamp"])
    images = b64e(form["images"])
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1

    cur.execute(f"INSERT INTO event VALUES ({nxteventid}, {adminid}, '{truckersmp_link}', '{departure}', '{destination}', '{distance}', {meetup_timestamp}, {departure_timestamp}, '{images}', {pvt}, '{title}', '', 0, '')")
    await AuditLog(adminid, f"Created event #{nxteventid}")
    conn.commit()

    return {"error": False, "response": {"eventid": str(nxteventid)}}

@app.patch(f"/{config.vtc_abbr}/event")
async def patchEvent(request: Request, response: Response, authorization: str = Header(None), eventid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'PATCH /event', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    form = await request.form()
    title = b64e(form["title"])
    truckersmp_link = b64e(form["truckersmp_link"])
    departure = b64e(form["departure"])
    destination = b64e(form["destination"])
    distance = b64e(form["distance"])
    meetup_timestamp = int(form["meetup_timestamp"])
    departure_timestamp = int(form["departure_timestamp"])
    images = b64e(form["images"])
    pvt = 0
    if form["pvt"] == "true":
        pvt = 1

    if int(eventid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}

    cur.execute(f"SELECT userid FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}
    creator = t[0][0]
    
    cur.execute(f"UPDATE event SET title = '{title}', tmplink = '{truckersmp_link}', departure = '{departure}', destination = '{destination}', \
        distance = '{distance}', mts = {meetup_timestamp}, dts = {departure_timestamp}, img = '{images}', pvt = {pvt} WHERE eventid = {eventid}")
    await AuditLog(adminid, f"Updated event #{eventid}")
    conn.commit()

    return {"error": False}

@app.delete(f"/{config.vtc_abbr}/event")
async def deleteEvent(request: Request, response: Response, authorization: str = Header(None), eventid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'DELETE /event', 180, 30)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()

    if int(eventid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}

    cur.execute(f"SELECT * FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}
    
    cur.execute(f"UPDATE event SET eventid = -eventid WHERE eventid = {eventid}")
    await AuditLog(adminid, f"Deleted event #{eventid}")
    conn.commit()

    return {"error": False}

@app.patch(f"/{config.vtc_abbr}/event/attendee")
async def patchEventAttendee(request: Request, response: Response, authorization: str = Header(None), eventid: Optional[int] = -1):
    rl = ratelimit(request.client.host, 'PATCH /event/attendee', 180, 10)
    if rl > 0:
        response.status_code = 429
        return {"error": True, "descriptor": f"Rate limit: Wait {rl} seconds"}

    au = auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = 401
        return au
    adminid = au["userid"]
        
    conn = newconn()
    cur = conn.cursor()
    
    form = await request.form()
    attendees = form["attendees"].replace(" ","").split(",")
    while "" in attendees:
        attendees.remove("")
    points = int(form["points"])

    if int(eventid) < 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}

    cur.execute(f"SELECT attendee FROM event WHERE eventid = {eventid}")
    t = cur.fetchall()
    if len(t) == 0:
        response.status_code = 404
        return {"error": True, "descriptor": ml.tr(request, "event_not_found")}
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
            cnt += 1
    ret2 = ret2[:-2]
    if cnt > 0:
        ret = ret + ret2

    if ret == f"Updated event #{eventid} attendees\n":
        return {"error": False, "response": {"message": "No changes made."}}

    cur.execute(f"UPDATE event SET attendee = ',{','.join(attendees)},', eventpnt = {points} WHERE eventid = {eventid}")
    conn.commit()

    ret = ret.replace("'","''")
    await AuditLog(adminid, ret)
    return {"error": False, "response": {"message": ret}}