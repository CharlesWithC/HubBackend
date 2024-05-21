# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import math
import os
import time
import traceback
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from api import tracebackHandler
from functions import *


async def EventNotification(app):
    request = Request(scope={"type":"http", "app": app, "headers": [], "mocked": True})
    rrnd = 0
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid, acquire_max_wait = 10)
            await app.db.extend_conn(dhrid, 5)

            request.state.dhrid = dhrid

            npid = app.redis.get("multiprocess-pid")
            if npid is not None and int(npid) != os.getpid():
                return
            app.redis.set("multiprocess-pid", os.getpid())

            rrnd += 1
            if rrnd == 1:
                # skip first round
                try:
                    await asyncio.sleep(3)
                except:
                    return
                continue

            notified_event_company = []
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'notified-event-company'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                sval = tt[0].split("-")
                if int(time.time()) - int(sval[2]) > int(sval[1]):
                    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'notified-event-company' AND sval = '{tt[0]}'")
                else:
                    notified_event_company.append((int(sval[0]), int(sval[1])))
            await app.db.commit(dhrid)

            notified_event_user = []
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'notified-event-user'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                sval = tt[0].split("-")
                if int(time.time()) - int(sval[1]) > 3600:
                    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'notified-event-user' AND sval = '{tt[0]}'")
                else:
                    notified_event_user.append(int(sval[0]))
            await app.db.commit(dhrid)

            notification_enabled = []
            tonotify = {}
            await app.db.execute(dhrid, "SELECT uid FROM settings WHERE skey = 'notification' AND sval LIKE '%,upcoming_event,%'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                notification_enabled.append(dd[0])
            await app.db.execute(dhrid, "SELECT uid, sval FROM settings WHERE skey = 'discord-notification'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                if dd[0] in notification_enabled:
                    tonotify[dd[0]] = dd[1]

            try:
                for meta in app.config.event_upcoming_forwarding:
                    meta = Dict2Obj(meta)

                    if meta.webhook_url == "" and meta.channel_id == "":
                        continue

                    await app.db.execute(dhrid, f"SELECT eventid, title, link, departure, destination, distance, meetup_timestamp, departure_timestamp, vote, description, is_private, userid FROM event WHERE meetup_timestamp >= {int(time.time())} AND meetup_timestamp <= {int(time.time() + meta.seconds_ahead)}")
                    t = await app.db.fetchall(dhrid)
                    for tt in t:
                        if (tt[0], meta.seconds_ahead) in notified_event_company:
                            continue
                        notified_event_company.append((tt[0], meta.seconds_ahead))
                        await app.db.execute(dhrid, f"INSERT INTO settings VALUES (0, 'notified-event-company', '{tt[0]}-{meta.seconds_ahead}-{int(time.time())}')")
                        await app.db.commit(dhrid)

                        eventid = tt[0]
                        title = tt[1] if tt[1] != "" else "N/A"
                        link = decompress(tt[2])
                        departure = tt[3] if tt[3] != "" else "N/A"
                        destination = tt[4] if tt[4] != "" else "N/A"
                        distance = tt[5] if tt[5] != "" else "N/A"
                        meetup_timestamp = tt[6]
                        departure_timestamp = tt[7]
                        description = decompress(tt[9])
                        is_private = tt[10]
                        creator_userid = tt[11]
                        creator = await GetUserInfo(request, userid = creator_userid, is_internal_function = True)

                        if meta.is_private is not None and int(meta.is_private) != is_private:
                            continue

                        def setvar(msg):
                            return msg.replace("{mention}", f"<@{creator['discordid']}>").replace("{name}", creator['name']).replace("{userid}", str(creator['userid'])).replace("{uid}", str(creator['uid'])).replace("{avatar}", validateUrl(creator['avatar'])).replace("{id}", str(eventid)).replace("{title}", title).replace("{description}", description).replace("{link}", validateUrl(link)).replace("{departure}", departure).replace("{destination}", destination).replace("{distance}", distance).replace("{meetup_timestamp}", str(meetup_timestamp)).replace("{departure_timestamp}", str(departure_timestamp))

                        await AutoMessage(app, meta, setvar)

                        await app.db.extend_conn(dhrid, 2)
                        try:
                            await asyncio.sleep(1)
                        except:
                            return
            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())

            try:
                await app.db.execute(dhrid, f"SELECT eventid, title, link, departure, destination, distance, meetup_timestamp, departure_timestamp, vote, description, is_private, userid FROM event WHERE meetup_timestamp >= {int(time.time())} AND meetup_timestamp <= {int(time.time() + 3600)}")
                t = await app.db.fetchall(dhrid)
                for tt in t:
                    if tt[0] in notified_event_user:
                        continue
                    notified_event_user.append(tt[0])
                    await app.db.execute(dhrid, f"INSERT INTO settings VALUES (0, 'notified-event-user', '{tt[0]}-{int(time.time())}')")
                    await app.db.commit(dhrid)

                    title = tt[1] if tt[1] != "" else "N/A"
                    link = decompress(tt[2])
                    departure = tt[3] if tt[3] != "" else "N/A"
                    destination = tt[4] if tt[4] != "" else "N/A"
                    distance = tt[5] if tt[5] != "" else "N/A"
                    meetup_timestamp = tt[6]
                    departure_timestamp = tt[7]
                    vote = str2list(tt[8])

                    for vt in vote:
                        uid = (await GetUserInfo(request, userid = vt, ignore_activity = True, is_internal_function = True))["uid"]
                        if uid in tonotify.keys():
                            channelid = tonotify[uid]
                            language = GetUserLanguage(request, uid)
                            QueueDiscordMessage(app, channelid, {"embeds": [{"title": title, "description": ml.tr(request, "event_notification_description", force_lang = language), "url": validateUrl(link),
                                "fields": [{"name": ml.tr(request, "departure", force_lang = language), "value": departure, "inline": True},
                                    {"name": ml.tr(request, "destination", force_lang = language), "value": destination, "inline": True},
                                    {"name": ml.tr(request, "distance", force_lang = language), "value": distance, "inline": True},
                                    {"name": ml.tr(request, "meetup_time", force_lang = language), "value": f"<t:{meetup_timestamp}:R>", "inline": True},
                                    {"name": ml.tr(request, "departure_time", force_lang = language), "value": f"<t:{departure_timestamp}:R>", "inline": True}],
                                "footer": {"text": ml.tr(request, "event_notification", force_lang = language), "icon_url": app.config.logo_url},
                                "timestamp": str(datetime.fromtimestamp(meetup_timestamp)), "color": int(app.config.hex_color, 16)}]})
                            await notification(request, "upcoming_event", uid, ml.tr(request, "event_starting", var = {"eventid": tt[0], "title": title}, force_lang = language), force = True, no_discord_notification = True)
                    await app.db.extend_conn(dhrid, 2)
                    try:
                        await asyncio.sleep(1)
                    except:
                        return
            except Exception as exc:
                await tracebackHandler(request, exc, traceback.format_exc())

            await app.db.close_conn(dhrid)
        except Exception as exc:
            await tracebackHandler(request, exc, traceback.format_exc())

        try:
            await asyncio.sleep(60)
        except:
            return

async def get_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", is_private: Optional[bool] = None, \
        title: Optional[str] = "", created_by: Optional[int] = None, attended_by: Optional[int] = None, voted_by: Optional[int] = None, \
        after_eventid: Optional[int] = None, created_after: Optional[int] = None, created_before: Optional[int] = None, \
        meetup_after: Optional[int] = None, meetup_before: Optional[int] = None, \
        departure_after: Optional[int] = None, departure_before: Optional[int] = None, \
        min_vote: Optional[int] = None, max_vote: Optional[int] = None, \
        min_attendee: Optional[int] = None, max_attendee: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /events/list', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    userid = -1
    if authorization is not None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            await ActivityUpdate(request, au["uid"], "events")

    limit = ""
    if userid in [-1, None]:
        limit = "AND is_private = 0 "
    if title != "":
        title = convertQuotation(title).lower()
        limit += f"AND LOWER(title) LIKE '%{title}%' "
    if meetup_after is not None:
        limit += f"AND meetup_timestamp >= {meetup_after} "
    if meetup_before is not None:
        limit += f"AND meetup_timestamp <= {meetup_before} "
    if departure_after is not None:
        limit += f"AND departure_timestamp >= {departure_after} "
    if departure_before is not None:
        limit += f"AND departure_timestamp <= {departure_before} "
    if created_after is not None:
        limit += f"AND timestamp >= {created_after} "
    if created_before is not None:
        limit += f"AND timestamp <= {created_before} "
    if userid not in [-1, None]:
        if min_vote is not None:
            if min_vote == 1:
                limit += "AND (LENGTH(vote) - LENGTH(REPLACE(vote, ',', '')) >= 2 AND vote != '' AND vote != ',,') "
            elif min_vote > 1:
                limit += f"AND (LENGTH(vote) - LENGTH(REPLACE(vote, ',', '')) >= {min_vote + 1}) "
        if max_vote is not None:
            if max_vote == 0:
                limit += "AND (vote = '' OR vote = ',,') "
            elif max_vote == 1:
                limit += "AND (LENGTH(vote) - LENGTH(REPLACE(vote, ',', '')) <= 2 OR vote = '' OR vote = ',,') "
            elif max_vote > 1:
                limit += f"AND (LENGTH(vote) - LENGTH(REPLACE(vote, ',', '')) <= {max_vote + 1} OR vote = '' OR vote = ',,') "
        if min_attendee is not None:
            if min_attendee == 1:
                limit += "AND (LENGTH(attendee) - LENGTH(REPLACE(attendee, ',', '')) >= 2 AND attendee != '' AND attendee != ',,') "
            elif min_attendee > 1:
                limit += f"AND (LENGTH(attendee) - LENGTH(REPLACE(attendee, ',', '')) >= {min_attendee + 1}) "
        if max_attendee is not None:
            if max_attendee == 0:
                limit += "AND (attendee = '' OR attendee = ',,') "
            elif max_attendee == 1:
                limit += "AND (LENGTH(attendee) - LENGTH(REPLACE(attendee, ',', '')) <= 2 OR attendee = '' OR attendee = ',,') "
            elif max_attendee > 1:
                limit += f"AND (LENGTH(attendee) - LENGTH(REPLACE(attendee, ',', '')) <= {max_attendee + 1} OR attendee = '' OR attendee = ',,') "
    if created_by is not None:
        limit += f"AND userid = {created_by} "
    if userid not in [-1, None]:
        if attended_by is not None:
            limit += f"AND attendee LIKE '%,{attended_by},%' "
        if voted_by is not None:
            limit += f"AND vote LIKE '%,{voted_by},%' "
    if is_private is not None:
        if is_private:
            limit += "AND is_private = 1 "
        else:
            limit += "AND is_private = 0 "

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    if order_by not in ["orderid", "eventid", "title", "meetup_timestamp", "departure_timestamp", "create_timestamp"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}
    if order_by == "create_timestamp":
        order_by = "timestamp"
    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT eventid FROM event WHERE eventid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, meetup_timestamp ASC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_eventid is not None:
        for tt in t:
            if tt[0] == after_eventid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points, orderid, is_pinned, timestamp, userid FROM event WHERE eventid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, meetup_timestamp ASC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        attendee_cnt = 0
        vote_cnt = 0
        if userid not in [-1, None]:
            attendee_cnt = len(str2list(tt[9]))
            vote_cnt = len(str2list(tt[10]))
        voted = None
        if userid not in [-1, None]:
            if userid in str2list(tt[10]):
                voted = True
            else:
                voted = False
        ret.append({"eventid": tt[0], "title": tt[8], "link": decompress(tt[1]), "description": decompress(tt[7]),
            "creator": await GetUserInfo(request, userid = tt[16]), \
            "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], \
                "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], \
                    "orderid": tt[13], "is_pinned": TF[tt[14]], "timestamp": tt[15], \
                    "attendees": attendee_cnt, "votes": vote_cnt, "voted": voted})

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /events', 60, 120)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    userid = -1
    aulanguage = ""
    if authorization is not None:
        au = await auth(authorization, request, check_member = False, allow_application_token = True)
        if au["error"]:
            response.status_code = au["code"]
            del au["code"]
            return au
        else:
            userid = au["userid"]
            aulanguage = au["language"]
            await ActivityUpdate(request, au["uid"], "events")

    await app.db.execute(dhrid, f"SELECT eventid, link, departure, destination, distance, meetup_timestamp, departure_timestamp, description, title, attendee, vote, is_private, points, orderid, is_pinned, timestamp, userid FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = aulanguage)}
    tt = t[0]
    attendee = str2list(tt[9])
    vote = str2list(tt[10])
    if userid in [-1, None]:
        attendee = []
        vote = []
    attendee_ret = []
    for at in attendee:
        attendee_ret.append(await GetUserInfo(request, userid = at))
    vote_ret = []
    for vt in vote:
        vote_ret.append(await GetUserInfo(request, userid = vt))
    voted = None
    if userid not in [-1, None]:
        if userid in vote:
            voted = True
        else:
            voted = False

    return {"eventid": tt[0], "title": tt[8], "link": decompress(tt[1]), "description": decompress(tt[7]), "creator": await GetUserInfo(request, userid = tt[16]), "departure": tt[2], "destination": tt[3], "distance": tt[4], "meetup_timestamp": tt[5], "departure_timestamp": tt[6], "points": tt[12], "is_private": TF[tt[11]], "orderid": tt[13], "is_pinned": TF[tt[14]], "timestamp": tt[15], "attendees": attendee_ret, "votes": vote_ret, "voted": voted}

async def put_vote(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PUT /events/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

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
    rl = await ratelimit(request, 'DELETE /events/vote', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

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
    rl = await ratelimit(request, 'POST /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_events"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = data["title"]
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = data["description"]
        if len(data["description"]) > 2000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}

        if data["link"] is None:
            data["link"] = ""
        data["link"] = data["link"].strip(" ")
        if data["link"] != "" and not isurl(data["link"]):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_link", force_lang = au["language"])}
        link = data["link"]
        if len(data["link"]) > 1000:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "link", "limit": "1,000"}, force_lang = au["language"])}

        departure = data["departure"]
        if len(data["departure"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "departure", "limit": "200"}, force_lang = au["language"])}
        destination = data["destination"]
        if len(data["destination"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "destination", "limit": "200"}, force_lang = au["language"])}
        distance = data["distance"]
        if len(data["distance"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "distance", "limit": "200"}, force_lang = au["language"])}
        meetup_timestamp = int(data["meetup_timestamp"])
        if abs(meetup_timestamp) > 9223372036854775807:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "meetup_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        departure_timestamp = int(data["departure_timestamp"])
        if abs(departure_timestamp) > 9223372036854775807:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "departure_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        if "is_private" not in data.keys():
            data["is_private"] = False
        is_private = int(bool(data["is_private"]))
        if "orderid" not in data.keys():
            data["orderid"] = 0
        if "is_pinned" not in data.keys():
            data["is_pinned"] = False
        orderid = int(data["orderid"])
        if abs(orderid) > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO event(userid, title, description, link, departure, destination, distance, meetup_timestamp, departure_timestamp, is_private, orderid, is_pinned, timestamp, vote, attendee, points) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(description))}', '{convertQuotation(compress(link))}', '{convertQuotation(departure)}', '{convertQuotation(destination)}', '{convertQuotation(distance)}', {meetup_timestamp}, {departure_timestamp}, {is_private}, {orderid}, {is_pinned}, {int(time.time())}, '', '', 0)")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    eventid = (await app.db.fetchone(dhrid))[0]
    await AuditLog(request, au["uid"], "event", ml.ctr(request, "created_event", var = {"id": eventid}))
    await app.db.commit(dhrid)

    await notification_to_everyone(request, "new_event", ml.spl("new_event_with_title", var = {"title": title}), discord_embed = {"title": title, "url": link, "description": description, "fields": [{"name": ml.spl("departure"), "value": departure, "inline": True}, {"name": ml.spl("destination"), "value": destination, "inline": True}, {"name": ml.spl("distance"), "value": distance, "inline": True}, {"name": ml.spl("meetup_time"), "value": f"<t:{meetup_timestamp}:R>", "inline": True}, {"name": ml.spl("departure_time"), "value": f"<t:{departure_timestamp}:R>", "inline": True}], "footer": {"text": ml.spl("new_event"), "icon_url": app.config.logo_url}}, only_to_members=is_private)

    def setvar(msg):
        return msg.replace("{mention}", f"<@{au['discordid']}>").replace("{name}", au['name']).replace("{userid}", str(au['userid'])).replace("{uid}", str(au['uid'])).replace("{avatar}", validateUrl(au['avatar'])).replace("{id}", str(eventid)).replace("{title}", title).replace("{description}", description).replace("{link}", validateUrl(link)).replace("{departure}", departure).replace("{destination}", destination).replace("{distance}", distance).replace("{meetup_timestamp}", str(meetup_timestamp)).replace("{departure_timestamp}", str(departure_timestamp))

    for meta in app.config.event_forwarding:
        meta = Dict2Obj(meta)
        if meta.is_private is not None and int(meta.is_private) != is_private:
            continue
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

    return {"eventid": eventid}

async def patch_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_events"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, link, departure, destination, distance, meetup_timestamp, departure_timestamp, is_private, orderid, is_pinned FROM event WHERE eventid = {eventid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "event_not_found", force_lang = au["language"])}
    (title, description, link, departure, destination, distance, meetup_timestamp, departure_timestamp, is_private, orderid, is_pinned) = t[0]
    description = decompress(description)
    link = decompress(link)

    data = await request.json()
    try:
        if "title" in data.keys():
            title = data["title"]
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "description" in data.keys():
            description = data["description"]
            if len(data["description"]) > 2000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "description", "limit": "2,000"}, force_lang = au["language"])}
        if "link" in data.keys():
            link = data["link"]
            if len(data["link"]) > 1000:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "departure", "limit": "1,000"}, force_lang = au["language"])}
        if "departure" in data.keys():
            departure = data["departure"]
            if len(data["departure"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "departure", "limit": "200"}, force_lang = au["language"])}
        if "destination" in data.keys():
            destination = data["destination"]
            if len(data["destination"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "destination", "limit": "200"}, force_lang = au["language"])}
        if "distance" in data.keys():
            distance = data["distance"]
            if len(data["distance"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "distance", "limit": "200"}, force_lang = au["language"])}
        if "meetup_timestamp" in data.keys():
            meetup_timestamp = int(data["meetup_timestamp"])
            if abs(meetup_timestamp) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "meetup_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        if "departure_timestamp" in data.keys():
            departure_timestamp = int(data["departure_timestamp"])
            if abs(departure_timestamp) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "departure_timestamp", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}
        if "is_private" in data.keys():
            is_private = int(bool(data["is_private"]))
        if "orderid" in data.keys():
            orderid = int(data["orderid"])
            if abs(orderid) > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_pinned" in data.keys():
            is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE event SET title = '{convertQuotation(title)}', description = '{convertQuotation(compress(description))}', link = '{convertQuotation(compress(link))}', departure = '{convertQuotation(departure)}', destination = '{convertQuotation(destination)}', distance = '{distance}', meetup_timestamp = {meetup_timestamp}, departure_timestamp = {departure_timestamp}, is_private = {is_private}, orderid = {orderid}, is_pinned = {is_pinned} WHERE eventid = {eventid}")
    await AuditLog(request, au["uid"], "event", ml.ctr(request, "updated_event", var = {"id": eventid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_event(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'DELETE /events', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_events"])
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
    await AuditLog(request, au["uid"], "event", ml.ctr(request, "deleted_event", var = {"id": eventid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def patch_attendees(request: Request, response: Response, eventid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'PATCH /events/attendees', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid)

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_events"])
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
        attendees = deduplicate(intify(attendees))
        points = int(data["points"])
        if abs(points) > 2147483647:
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
        name = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["name"]
        uid = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["uid"]
        await notification(request, "event", uid, ml.tr(request, "event_updated_received_points", var = {"title": title, "eventid": eventid, "points": tseparator(points)}, force_lang = await GetUserLanguage(request, uid)))
        ret1 += f"`{name}` (`{attendee}`), "
        cnt += 1
    ret1 = ret1[:-2]
    ret1 += ".  \n"
    if cnt > 0:
        ret = ret + ret1

    ret2 = ml.ctr(request, "removed_attendees", var = {"points": old_points}).rstrip(" ") + " "
    cnt = 0
    toremove = []
    for attendee in old_attendees:
        if attendee not in attendees:
            toremove.append(attendee)
            name = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["name"]
            uid = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["uid"]
            await notification(request, "event", uid, ml.tr(request, "event_updated_lost_points", var = {"title": title, "eventid": eventid, "points": tseparator(old_points)}, force_lang = await GetUserLanguage(request, uid)))
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
            name = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["name"]
            uid = (await GetUserInfo(request, userid = attendee, is_internal_function = True))["uid"]
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

    await AuditLog(request, au["uid"], "event", ret)

    return {"message": ret}
