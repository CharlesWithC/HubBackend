# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import math
import os
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


async def EventNotification(app):
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)
            await app.db.extend_conn(dhrid, 5)

            request = Request(scope={"type":"http", "app": app})
            request.state.dhrid = dhrid

            npid = -1
            nlup = -1
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'process-event-notification-pid'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                npid = int(t[0][0])
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'process-event-notification-last-update'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                nlup = int(t[0][0])
            if npid != -1 and npid != os.getpid() and time.time() - nlup <= 600:
                try:
                    await asyncio.sleep(60)
                except:
                    return
                continue
            await app.db.execute(dhrid, "DELETE FROM settings WHERE skey = 'process-event-notification-pid' OR skey = 'process-event-notification-last-update'")
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES (NULL, 'process-event-notification-pid', '{os.getpid()}')")
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES (NULL, 'process-event-notification-last-update', '{int(time.time())}')")
            await app.db.commit(dhrid)

            notified_event = []
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'notified-event'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                sval = tt[0].split("-")
                if int(time.time()) - int(sval[1]) > 3600:
                    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'notified-event' AND sval = '{tt[0]}'")
                else:
                    notified_event.append(int(sval[0]))
            await app.db.commit(dhrid)

            notification_enabled = []
            tonotify = {}
            await app.db.execute(dhrid, "SELECT uid FROM settings WHERE skey = 'notification' AND sval LIKE '%,event,%'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                notification_enabled.append(dd[0])
            await app.db.execute(dhrid, "SELECT uid, sval FROM settings WHERE skey = 'discord-notification'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                if dd[0] in notification_enabled:
                    tonotify[dd[0]] = dd[1]

            await app.db.execute(dhrid, f"SELECT eventid, title, link, departure, destination, distance, meetup_timestamp, departure_timestamp, vote FROM event WHERE meetup_timestamp >= {int(time.time())} AND meetup_timestamp <= {int(time.time() + 3600)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                if tt[0] in notified_event:
                    continue
                notified_event.append(tt[0])
                await app.db.execute(dhrid, f"INSERT INTO settings VALUES (0, 'notified-event', '{tt[0]}-{int(time.time())}')")
                await app.db.commit(dhrid)

                title = tt[1] if tt[1] != "" else "N/A"
                link = decompress(tt[2])
                if not isurl(link):
                    link = None
                departure = tt[3] if tt[3] != "" else "N/A"
                destination = tt[4] if tt[4] != "" else "N/A"
                distance = tt[5] if tt[5] != "" else "N/A"
                meetup_timestamp = tt[6]
                departure_timestamp = tt[7]
                vote = str2list(tt[8])
                
                for vt in vote:
                    uid = (await GetUserInfo(request, userid = vt, ignore_activity = True))["uid"]
                    if uid in tonotify.keys():
                        channelid = tonotify[uid]
                        language = GetUserLanguage(request, uid)
                        QueueDiscordMessage(app, channelid, {"embeds": [{"title": ml.tr(request, "event_notification", force_lang = language), "description": ml.tr(request, "event_notification_description", force_lang = language), "url": link,
                            "fields": [{"name": ml.tr(request, "title", force_lang = language), "value": title, "inline": False},
                                {"name": ml.tr(request, "departure", force_lang = language), "value": departure, "inline": True},
                                {"name": ml.tr(request, "destination", force_lang = language), "value": destination, "inline": True},
                                {"name": ml.tr(request, "distance", force_lang = language), "value": distance, "inline": True},
                                {"name": ml.tr(request, "meetup_time", force_lang = language), "value": f"<t:{meetup_timestamp}:R>", "inline": True},
                                {"name": ml.tr(request, "departure_time", force_lang = language), "value": f"<t:{departure_timestamp}:R>", "inline": True}],
                            "footer": {"text": app.config.name, "icon_url": app.config.logo_url},
                            "timestamp": str(datetime.fromtimestamp(meetup_timestamp)), "color": int(app.config.hex_color, 16)}]})
                            
                await app.db.extend_conn(dhrid, 2)
                try:
                    await asyncio.sleep(1)
                except:
                    return
            
            await app.db.close_conn(dhrid)
        except:
            pass

        try:
            await asyncio.sleep(60)
        except:
            return

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, query: Optional[str] = "", \
        first_event_after: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /events/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization is not None:
        au = await auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            await ActivityUpdate(request, au["uid"], "events")
    
    if first_event_after is None:
        first_event_after = int(time.time()) - 86400

    limit = ""
    if userid == -1:
        limit = "AND is_private = 0 "
    if query != "":
        query = convertQuotation(query).lower()
        limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    await app.db.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid >= 0 AND meetup_timestamp >= {first_event_after} {limit} ORDER BY meetup_timestamp ASC LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        attendee_cnt = 0
        vote_cnt = 0
        if userid != -1:
            attendee_cnt = len(str2list(tt[9]))
            vote_cnt = len(str2list(tt[10]))
        ret.append({"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), "link": decompress(tt[1]), \
            "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], \
                "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], \
                    "attendees": attendee_cnt, "votes": vote_cnt})
    
    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM event WHERE eventid >= 0 AND meetup_timestamp >= {first_event_after} {limit}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]
        
    await app.db.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid >= 0 AND meetup_timestamp < {first_event_after} {limit} ORDER BY meetup_timestamp ASC LIMIT {max(max(page-1, 0) * page_size - tot,0)}, {page_size}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        attendee_cnt = 0
        vote_cnt = 0
        if userid != -1:
            attendee_cnt = len(str2list(tt[9]))
            vote_cnt = len(str2list(tt[10]))
        ret.append({"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), \
            "link": decompress(tt[1]), "departure": tt[2], "destination": tt[3],\
            "distance": tt[4], "meetup_timestamp": tt[5], "departure_timestamp": tt[6], \
                "points": tt[12], "is_private": TF[tt[11]], "attendees": attendee_cnt, "votes": vote_cnt})
    
    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM event WHERE eventid >= 0 {limit}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /events', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    userid = -1
    if authorization is not None:
        au = await auth(authorization, request, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await ActivityUpdate(request, au["uid"], "events")
    
    await app.db.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = aulanguage)}
    tt = t[0]
    attendee = str2list(tt[9])
    vote = str2list(tt[10])
    if userid == -1:
        attendee = []
        vote = []
    attendee_ret = []
    for at in attendee:
        attendee_ret.append(await GetUserInfo(request, userid = at))
    vote_ret = []
    for vt in vote:
        vote_ret.append(await GetUserInfo(request, userid = vt))

    return {"eventid": tt[0], "title": tt[8], "description": decompress(tt[7]), "link": decompress(tt[1]), "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], "attendees": attendee_ret, "votes": vote_ret}

async def put_vote(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PUT /events/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
        
    await app.db.execute(dhrid, f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    vote = str2list(t[0][0])
    
    if userid in vote:
        response.status_code = 409
        return {"error": ml.tr(request, "event_already_voted", force_lang = au["language"])}
    else:
        vote.append(userid)
        await app.db.execute(dhrid, f"UPDATE event SET vote = ',{list2str(vote)},' WHERE eventid = {eventid}")
        await app.db.commit(dhrid)
        return Response(status_code=204)
    
async def delete_vote(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /events/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
        
    await app.db.execute(dhrid, f"SELECT vote FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    vote = str2list(t[0][0])

    if userid in vote:
        vote.remove(userid)
        await app.db.execute(dhrid, f"UPDATE event SET vote = ',{list2str(vote)},' WHERE eventid = {eventid}")
        await app.db.commit(dhrid)
        return Response(status_code=204)
    else:
        response.status_code = 409
        return {"error": ml.tr(request, "event_not_voted", force_lang = au["language"])}

async def post_event(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        link = compress(data["link"])
        departure = convertQuotation(data["departure"])
        destination = convertQuotation(data["destination"])
        distance = convertQuotation(data["distance"])
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
        is_private = int(data["is_private"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO event(userid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, is_private, title, attendee, points, vote) VALUES ({au['userid']}, '{link}', '{departure}', '{destination}', '{distance}', {meetup_timestamp}, {departure_timestamp}, '{description}', {is_private}, '{title}', '', 0, '')")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    eventid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], ml.ctr(request, "created_event", var = {"id": eventid}))

    return {"eventid": eventid}

async def patch_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    await app.db.execute(dhrid, f"SELECT userid FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        link = compress(data["link"])
        departure = convertQuotation(data["departure"])
        destination = convertQuotation(data["destination"])
        distance = convertQuotation(data["distance"])
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
        is_private = int(data["is_private"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"UPDATE event SET title = '{title}', link = '{link}', departure = '{departure}', destination = '{destination}', distance = '{distance}', meetup_timestamp = {meetup_timestamp}, departure_timestamp = {departure_timestamp}, description = '{description}', is_private = {is_private} WHERE eventid = {eventid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "updated_event", var = {"id": eventid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return 
        
    await app.db.execute(dhrid, f"SELECT * FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    
    await app.db.execute(dhrid, f"DELETE FROM event WHERE eventid = {eventid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_event", var = {"id": eventid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def patch_attendees(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /events/attendees', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "event"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
        
    data = await request.json()
    try:
        attendees = data["attendees"]
        if type(attendees) is not list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        attendees = intify(attendees)
        points = int(data["points"])
        if points > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "points", "limit": "2,147,483,647"}, force_lang = au["language"])}
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT attendee, points, title FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    old_attendees = str2list(t[0][0])
    old_points = t[0][1]
    title = t[0][2]
    gap = points - old_points

    ret = ml.ctr(request, "updated_event_attendees", var = {"id": eventid}) + "  \n"
    ret1 = ml.ctr(request, "added_attendees", var = {"points": points}).rstrip(" ") + " "
    cnt = 0
    for attendee in attendees:
        if attendee in old_attendees:
            continue
        name = (await GetUserInfo(request, userid = attendee))["name"]
        uid = (await GetUserInfo(request, userid = attendee))["uid"]
        await notification(request, "event", uid, ml.tr(request, "event_updated_received_points", var = {"title": title, "eventid": eventid, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
        ret1 += f"`{name}` (`{attendee}`), "
        cnt += 1
    ret1 = ret1[:-2]
    ret1 += ".  \n"
    if cnt > 0:
        ret = ret + ret1

    ret2 = ml.ctr(request, "removed_attendees", var = {"points": points}).rstrip(" ") + " "
    cnt = 0
    toremove = []
    for attendee in old_attendees:
        if attendee not in attendees:
            toremove.append(attendee)
            name = (await GetUserInfo(request, userid = attendee))["name"]
            uid = (await GetUserInfo(request, userid = attendee))["uid"]
            await notification(request, "event", uid, ml.tr(request, "event_updated_lost_points", var = {"title": title, "eventid": eventid, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
            ret2 += f"`{name}` (`{attendee}`), "
            cnt += 1
    ret2 = ret2[:-2]
    ret2 += ".  \n"
    if cnt > 0:
        ret = ret + ret2
    for attendee in toremove:
        old_attendees.remove(attendee)
    
    if gap != 0:
        if gap > 0:
            ret3 = ml.ctr(request, "added_event_points", var = {"points": gap})
        else:
            ret3 = ml.ctr(request, "removed_event_points", var = {"points": -gap})
        cnt = 0
        for attendee in old_attendees:
            name = (await GetUserInfo(request, userid = attendee))["name"]
            uid = (await GetUserInfo(request, userid = attendee))["uid"]
            if gap > 0:
                await notification(request, "event", uid, ml.tr(request, "event_updated_received_more_points", var = {"title": title, "eventid": eventid, "gap": gap, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
            elif gap < 0:
                await notification(request, "event", uid, ml.tr(request, "event_updated_lost_more_points", var = {"title": title, "eventid": eventid, "gap": -gap, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
            ret3 += f"`{name}` (`{attendee}`), "
            cnt += 1
        ret3 = ret3[:-2]
        ret3 += ".  \n  "
        if cnt > 0:
            ret = ret + ret3

    await app.db.execute(dhrid, f"UPDATE event SET attendee = ',{list2str(attendees)},', points = {points} WHERE eventid = {eventid}")
    await app.db.commit(dhrid)

    if ret == ml.ctr(request, "updated_event_attendees", var = {"id": eventid}) + "  \n":
        return {"message": ml.tr(request, "no_changes_made", force_lang = await GetUserLanguage(request, au["uid"]))}

    await AuditLog(request, au["uid"], ret)
    return {"message": ret}