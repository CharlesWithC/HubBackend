# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
import traceback
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql, genconn
from functions.main import *


def EventNotification():        
    while 1:
        try:
            conn = genconn()
            cur = conn.cursor()

            notified = []
            cur.execute(f"SELECT sval FROM settings WHERE skey = 'notified-event'")
            t = cur.fetchall()
            for tt in t:
                if int(time.time()) - int(tt[0].split("-")[1]) > 3600:
                    cur.execute(f"DELETE FROM settings WHERE skey = 'notified-event' AND sval = '{tt[0]}'")
                else:
                    notified.append(tt[0].split("-")[0])
            conn.commit()

            notification_enabled = []
            tonotify = {}
            cur.execute(f"SELECT uid FROM settings WHERE skey = 'notification' AND sval LIKE '%,event,%'")
            d = cur.fetchall()
            for dd in d:
                notification_enabled.append(dd[0])
            cur.execute(f"SELECT uid, sval FROM settings WHERE skey = 'discord-notification'")
            d = cur.fetchall()
            for dd in d:
                if dd[0] in notification_enabled:
                    tonotify[dd[0]] = dd[1]

            cur.execute(f"SELECT eventid, title, link, departure, destination, distance, meetup_timestamp, departure_timestamp, vote FROM event WHERE meetup_timestamp >= {int(time.time())} AND meetup_timestamp <= {int(time.time() + 3600)}")
            t = cur.fetchall()
            for tt in t:
                if str(tt[0]) in notified:
                    continue
                notified.append(str(tt[0]))
                cur.execute(f"INSERT INTO settings VALUES (0, 'notified-event', '{tt[0]}-{int(time.time())}')")
                conn.commit()

                title = tt[1] if tt[1] != "" else "N/A"
                link = decompress(tt[2])
                if not isurl(link):
                    link = None
                departure = tt[3] if tt[3] != "" else "N/A"
                destination = tt[4] if tt[4] != "" else "N/A"
                distance = tt[5] if tt[5] != "" else "N/A"
                meetup_timestamp = tt[6]
                departure_timestamp = tt[7]
                vote = tt[8].split(",")

                vote = [int(x) for x in vote if isint(x)]
                for vt in vote:
                    uid = int(bGetUserInfo(userid = vt, ignore_activity = True)["uid"])
                    if uid in tonotify.keys():
                        channelid = tonotify[uid]
                        language = bGetUserLanguage(uid, "en")
                        QueueDiscordMessage(channelid, {"embeds": [{"title": ml.tr(None, "event_notification", force_lang = language), "description": ml.tr(None, "event_notification_description", force_lang = language), "url": link,
                            "fields": [{"name": ml.tr(None, "title", force_lang = language), "value": title, "inline": False},
                                {"name": ml.tr(None, "departure", force_lang = language), "value": departure, "inline": True},
                                {"name": ml.tr(None, "destination", force_lang = language), "value": destination, "inline": True},
                                {"name": ml.tr(None, "distance", force_lang = language), "value": distance, "inline": True},
                                {"name": ml.tr(None, "meetup_time", force_lang = language), "value": f"<t:{meetup_timestamp}:R>", "inline": True},
                                {"name": ml.tr(None, "departure_time", force_lang = language), "value": f"<t:{departure_timestamp}:R>", "inline": True}],
                            "footer": {"text": config.name, "icon_url": config.logo_url},
                            "timestamp": str(datetime.fromtimestamp(meetup_timestamp)), "color": config.intcolor}]})
                            
                time.sleep(1)
            cur.close()
            conn.close()
        except:
            traceback.print_exc()

        time.sleep(60)

@app.get(f"/{config.abbr}/event/list")
async def get_event_list(request: Request, response: Response, authorization: str = Header(None), \
    page: Optional[int] = 1, page_size: Optional[int] = 10, query: Optional[str] = "", \
        first_event_after: Optional[int] = -1):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /event/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization != None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await ActivityUpdate(dhrid, au["uid"], f"events")
    
    if first_event_after < 0:
        first_event_after = int(time.time()) - 86400

    limit = ""
    if userid == -1:
        limit = "AND is_private = 0 "
    if query != "":
        query = convert_quotation(query).lower()
        limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "

    if page <= 0:
        page = 1

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    await aiosql.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid >= 0 AND meetup_timestamp >= {first_event_after} {limit} ORDER BY meetup_timestamp ASC LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        attendee = tt[9].split(",")
        vote = tt[10].split(",")
        if userid == -1:
            attendee = []
            vote = []
        attendee = [int(x) for x in attendee if isint(x)]
        vote = [int(x) for x in vote if isint(x)]
        attendee_cnt = 0
        for at in attendee:
            attendee_cnt += 1
        vote_cnt = 0
        for vt in vote:
            vote_cnt += 1
        ret.append({"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), "link": decompress(tt[1]), \
            "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], \
                "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], \
                    "attendees": attendee_cnt, "votes": vote_cnt})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM event WHERE eventid >= 0 AND meetup_timestamp >= {first_event_after} {limit}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
        
    await aiosql.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid >= 0 AND meetup_timestamp < {first_event_after} {limit} ORDER BY meetup_timestamp ASC LIMIT {max((page-1) * page_size - tot,0)}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    for tt in t:
        attendee = tt[9].split(",")
        vote = tt[10].split(",")
        if userid == -1:
            attendee = []
            vote = []
        attendee = [int(x) for x in attendee if isint(x)]
        vote = [int(x) for x in vote if isint(x)]
        attendee_cnt = 0
        for at in attendee:
            attendee_cnt += 1
        vote_cnt = 0
        for vt in vote:
            vote_cnt += 1
        ret.append({"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), \
            "link": decompress(tt[1]), "departure": tt[2], "destination": tt[3],\
            "distance": tt[4], "meetup_timestamp": tt[5], "departure_timestamp": tt[6], \
                "points": tt[12], "is_private": TF[tt[11]], "attendees": attendee_cnt, "votes": vote_cnt})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM event WHERE eventid >= 0 {limit}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.get(f"/{config.abbr}/event/{{eventid}}")
async def get_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'GET /event', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization != None:
        au = await auth(dhrid, authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await ActivityUpdate(dhrid, au["uid"], f"events")
    
    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = aulanguage)}

    await aiosql.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = aulanguage)}
    tt = t[0]
    attendee = tt[9].split(",")
    vote = tt[10].split(",")
    if userid == -1:
        attendee = []
        vote = []
    attendee = [int(x) for x in attendee if isint(x)]
    vote = [int(x) for x in vote if isint(x)]
    attendee_ret = []
    for at in attendee:
        attendee_ret.append(await GetUserInfo(dhrid, request, userid = at))
    vote_ret = []
    for vt in vote:
        vote_ret.append(await GetUserInfo(dhrid, request, userid = vt))

    return {"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), "link": decompress(tt[1]), "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], "attendees": attendee_ret, "votes": vote_ret}

@app.put(f"/{config.abbr}/event/{{eventid}}/vote")
async def put_event_vote(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PUT /event/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
        
    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    vote = t[0][0].split(",")
    vote = [str(x) for x in vote if isint(x)]
    if str(userid) in vote:
        response.status_code = 409
        return {"error": ml.tr(request, "event_already_voted", force_lang = au["language"])}
    else:
        vote.append(str(userid))
        await aiosql.execute(dhrid, f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        await aiosql.commit(dhrid)
        return Response(status_code=204)
    
@app.delete(f"/{config.abbr}/event/{{eventid}}/vote")
async def delete_event_vote(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /event/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
        
    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    vote = t[0][0].split(",")
    vote = [str(x) for x in vote if isint(x)]
    if str(userid) in vote:
        vote.remove(str(userid))
        await aiosql.execute(dhrid, f"UPDATE event SET vote = '{','.join(vote)}' WHERE eventid = {eventid}")
        await aiosql.commit(dhrid)
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "event_not_voted", force_lang = au["language"])}

@app.post(f"/{config.abbr}/event")
async def post_event(request: Request, response: Response, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'POST /event', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    data = await request.json()
    try:
        title = convert_quotation(data["title"])
        link = compress(data["link"])
        departure = convert_quotation(data["departure"])
        destination = convert_quotation(data["destination"])
        distance = convert_quotation(data["distance"])
        meetup_timestamp = int(data["meetup_timestamp"])
        departure_timestamp = int(data["departure_timestamp"])
        description = compress(data["description"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["departure"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "departure", "limit": "200"}, force_lang = au["language"])}
        if len(data["destination"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "destination", "limit": "200"}, force_lang = au["language"])}
        if len(data["distance"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "distance", "limit": "200"}, force_lang = au["language"])}
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        is_private = 0
        if data["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"INSERT INTO event(userid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, is_private, title, attendee, points, vote) VALUES ({adminid}, '{link}', '{departure}', '{destination}', '{distance}', {meetup_timestamp}, {departure_timestamp}, '{description}', {is_private}, '{title}', '', 0, '')")
    await aiosql.commit(dhrid)
    await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    eventid = (await aiosql.fetchone(dhrid))[0]
    await AuditLog(dhrid, adminid, f"Created event `#{eventid}`")

    return {"eventid": eventid}

@app.patch(f"/{config.abbr}/event/{{eventid}}")
async def patch_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /event', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
        
    await aiosql.execute(dhrid, f"SELECT userid FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    data = await request.json()
    try:
        title = convert_quotation(data["title"])
        link = compress(data["link"])
        departure = convert_quotation(data["departure"])
        destination = convert_quotation(data["destination"])
        distance = convert_quotation(data["distance"])
        meetup_timestamp = int(data["meetup_timestamp"])
        departure_timestamp = int(data["departure_timestamp"])
        description = compress(data["description"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if len(data["departure"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "departure", "limit": "200"}, force_lang = au["language"])}
        if len(data["destination"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "destination", "limit": "200"}, force_lang = au["language"])}
        if len(data["distance"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "distance", "limit": "200"}, force_lang = au["language"])}
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        is_private = 0
        if data["is_private"] == "true":
            is_private = 1
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE event SET title = '{title}', link = '{link}', departure = '{departure}', destination = '{destination}', \
        distance = '{distance}', meetup_timestamp = {meetup_timestamp}, departure_timestamp = {departure_timestamp}, description = '{description}', is_private = {is_private} WHERE eventid = {eventid}")
    await AuditLog(dhrid, adminid, f"Updated event `#{eventid}`")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.delete(f"/{config.abbr}/event/{{eventid}}")
async def delete_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'DELETE /event', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT * FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"DELETE FROM event WHERE eventid = {eventid}")
    await AuditLog(dhrid, adminid, f"Deleted event `#{eventid}`")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.patch(f"/{config.abbr}/event/{{eventid}}/attendees")
async def patch_event_attendees(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, request.client.host, 'PATCH /event/attendees', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    adminid = au["userid"]
        
    data = await request.json()
    try:
        attendees = data["attendees"]
        if type(attendees) is not list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        attendees = [str(x) for x in attendees if isint(x)]
        points = int(data["points"])
        if points > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "points", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if int(eventid) < 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"SELECT attendee, points, title FROM event WHERE eventid = {eventid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    orgattendees = t[0][0].split(",")
    orgattendees = [str(x) for x in orgattendees if isint(x)]
    orgeventpnt = t[0][1]
    title = t[0][2]
    gap = points - orgeventpnt

    ret = f"Updated event `#{eventid}` attendees  \n"
    ret1 = f"New attendees - Given `{points}` points to "
    cnt = 0
    for attendee in attendees:
        if attendee in orgattendees:
            continue
        attendee = int(attendee)
        name = (await GetUserInfo(dhrid, request, userid = attendee))["name"]
        uid = (await GetUserInfo(dhrid, request, userid = attendee))["uid"]
        await notification(dhrid, "event", uid, ml.tr(request, "event_updated_received_points", var = {"title": title, "eventid": eventid, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
        ret1 += f"{name} ({attendee}), "
        cnt += 1
    ret1 = ret1[:-2]
    ret1 += f".  \n"
    if cnt > 0:
        ret = ret + ret1

    ret2 = f"Removed attendees - Removed `{points}` points from "
    cnt = 0
    toremove = []
    for attendee in orgattendees:
        if not attendee in attendees:
            toremove.append(attendee)
            attendee = int(attendee)
            name = (await GetUserInfo(dhrid, request, userid = attendee))["name"]
            uid = (await GetUserInfo(dhrid, request, userid = attendee))["uid"]
            await notification(dhrid, "event", uid, ml.tr(request, "event_updated_lost_points", var = {"title": title, "eventid": eventid, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
            ret2 += f"{name} ({attendee}), "
            cnt += 1
    ret2 = ret2[:-2]
    ret2 += f".  \n"
    if cnt > 0:
        ret = ret + ret2
    for attendee in toremove:
        orgattendees.remove(attendee)
    
    if gap != 0:
        if gap > 0:
            ret3 = f"Updated points - Added `{gap}` points to "
        else:
            ret3 = f"Updated points - Removed `{-gap}` points from "
        cnt = 0
        for attendee in orgattendees:
            attendee = int(attendee)
            name = (await GetUserInfo(dhrid, request, userid = attendee))["name"]
            uid = (await GetUserInfo(dhrid, request, userid = attendee))["uid"]
            if gap > 0:
                await notification(dhrid, "event", uid, ml.tr(request, "event_updated_received_more_points", var = {"title": title, "eventid": eventid, "gap": gap, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
            elif gap < 0:
                await notification(dhrid, "event", uid, ml.tr(request, "event_updated_lost_more_points", var = {"title": title, "eventid": eventid, "gap": -gap, "points": tseparator(points)}, force_lang = await GetUserLanguage(dhrid, uid, "en")))
            ret3 += f"{name} ({attendee}), "
            cnt += 1
        ret3 = ret3[:-2]
        ret3 += f".  \n  "
        if cnt > 0:
            ret = ret + ret3

    await aiosql.execute(dhrid, f"UPDATE event SET attendee = ',{','.join(attendees)},', points = {points} WHERE eventid = {eventid}")
    await aiosql.commit(dhrid)

    if ret == f"Updated event #{eventid} attendees  \n":
        return {"message": "No changes made."}

    await AuditLog(dhrid, adminid, ret)
    return {"message": ret}