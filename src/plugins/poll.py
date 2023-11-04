# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import copy
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *

POLL_CONFIG_KEYS = ["max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter", "show_stats_when_ended"]
POLL_DEFAULT_CONFIG = {"max_choice": 1, "allow_modify_vote": False, "show_stats": True, "show_stats_before_vote": False, "show_voter": False, "show_stats_when_ended": True}
POLL_CONFIG_TYPE = {"max_choice": int, "allow_modify_vote": bool, "show_stats": bool, "show_stats_before_vote": bool, "show_voter": bool, "show_stats_when_ended": bool}
# show_stats(before_vote) must be 1 to show_voter
# show_stats => show stats after vote
# show_stats_before_vote => overwrite show_stats (aka show stats after/before vote)

# NOTE: To end a poll, set its `end_time` to current timestamp

async def PollResultNotification(app):
    rrnd = 0
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)
            await app.db.extend_conn(dhrid, 5)

            request = Request(scope={"type":"http", "app": app})
            request.state.dhrid = dhrid

            npid = -1
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'multiprocess-pid' FOR UPDATE")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                npid = int(t[0][0])
            if npid != -1 and npid != os.getpid():
                return
            await app.db.execute(dhrid, "DELETE FROM settings WHERE skey = 'multiprocess-pid'")
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES (NULL, 'multiprocess-pid', '{os.getpid()}')")
            await app.db.commit(dhrid)
            rrnd += 1
            if rrnd == 1:
                try:
                    await asyncio.sleep(3)
                except:
                    return
                continue

            notified_poll = []
            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'notified-poll'")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                sval = tt[0].split("-")
                if int(time.time()) - int(sval[1]) > 3600:
                    await app.db.execute(dhrid, f"DELETE FROM settings WHERE skey = 'notified-poll' AND sval = '{tt[0]}'")
                else:
                    notified_poll.append(int(sval[0]))
            await app.db.commit(dhrid)

            notification_enabled = []
            tonotify = {}
            await app.db.execute(dhrid, "SELECT uid FROM settings WHERE skey = 'notification' AND sval LIKE '%,poll_result,%'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                notification_enabled.append(dd[0])
            await app.db.execute(dhrid, "SELECT uid, sval FROM settings WHERE skey = 'discord-notification'")
            d = await app.db.fetchall(dhrid)
            for dd in d:
                if dd[0] in notification_enabled:
                    tonotify[dd[0]] = dd[1]

            await app.db.execute(dhrid, f"SELECT pollid, title, description, end_time, config FROM poll WHERE end_time >= {int(time.time() - 3600)} AND end_time <= {int(time.time())}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                if tt[0] in notified_poll:
                    continue
                notified_poll.append(tt[0])
                await app.db.execute(dhrid, f"INSERT INTO settings VALUES (0, 'notified-poll', '{tt[0]}-{int(time.time())}')")
                await app.db.commit(dhrid)

                pollid = tt[0]
                title = tt[1] if tt[1] != "" else "N/A"
                description = decompress(tt[2]) if tt[2] != "" else "N/A"
                end_time = tt[3]
                configl = str2list(tt[4])
                config = copy.deepcopy(POLL_DEFAULT_CONFIG)
                for i in range(len(POLL_CONFIG_KEYS)):
                    if i < len(configl):
                        config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](configl[i])

                choices = {}
                choice_vote = {}
                await app.db.execute(dhrid, f"SELECT choiceid, content FROM poll_choice WHERE pollid = {pollid} ORDER BY orderid ASC")
                p = await app.db.fetchall(dhrid)
                for pp in p:
                    choices[pp[0]] = pp[1]
                    choice_vote[pp[0]] = 0

                votes = {}
                voted_userid = []
                await app.db.execute(dhrid, f"SELECT choiceid, userid FROM poll_vote WHERE pollid = {pollid}")
                p = await app.db.fetchall(dhrid)
                for pp in p:
                    if pp[1] not in votes.keys():
                        votes[pp[1]] = [pp[0]]
                    else:
                        votes[pp[1]].append(pp[0])
                    voted_userid.append(pp[1])
                    choice_vote[pp[0]] += 1

                total_vote = sum(choice_vote.values())

                for userid in voted_userid:
                    userinfo = await GetUserInfo(request, userid = userid, ignore_activity = True)
                    uid = userinfo["uid"]
                    isstaff = checkPerm(app, userinfo["roles"], ["administrator", "manage_polls"])
                    if uid in tonotify.keys() and (isstaff or (config["show_stats_before_vote"] or config["show_stats"] or config["show_stats_when_ended"])):
                        ctxt = ""
                        for choiceid in choices.keys():
                            content = choices[choiceid]
                            if total_vote != 0:
                                stats = f"{round((choice_vote[choiceid] / total_vote)*100, 2)}% ({choice_vote[choiceid]}/{total_vote})"
                            else:
                                stats = "0% (0/0)"
                            if choiceid in votes[userid]:
                                ctxt += f":ballot_box_with_check:  {content} - {stats}\n"
                            else:
                                ctxt += f":white_square_button:  {content} - {stats}\n"
                        channelid = tonotify[uid]
                        language = GetUserLanguage(request, uid)
                        QueueDiscordMessage(app, channelid, {"embeds": [{"title": title, "description": description,
                            "fields": [{"name": ml.tr(request, "choices", force_lang = language), "value": ctxt, "inline": False}],
                            "footer": {"text": ml.tr(request, "poll_result", force_lang = language), "icon_url": app.config.logo_url},
                            "timestamp": str(datetime.fromtimestamp(end_time)), "color": int(app.config.hex_color, 16)}]})
                        await notification(request, "poll_result", uid, ml.tr(request, "poll_ended_with_title", var = {"title": title}, force_lang = language), force = True, no_discord_notification = True)
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

async def get_list(request: Request, response: Response, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_pollid: Optional[int] = None, \
        created_after: Optional[int] = None, created_before: Optional[int] = None, \
        end_after: Optional[int] = None, end_before: Optional[int] = None, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", \
        query: Optional[str] = "", created_by: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /polls/list', 60, 120)
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
    isstaff = checkPerm(app, au["roles"], ["administrator", "manage_polls"])
    await ActivityUpdate(request, au["uid"], "poll")

    limit = ""
    if query != "":
        query = convertQuotation(query).lower()
        limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "
    if created_by is not None:
        limit += f"AND userid = {created_by} "
    if created_after is not None:
        limit += f"AND timestamp >= {created_after} "
    if created_before is not None:
        limit += f"AND timestamp <= {created_before} "
    if end_after is not None:
        limit += f"AND end_time >= {end_after} "
    if end_before is not None:
        limit += f"AND end_time <= {end_before} "

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order_by not in ["orderid", "pollid", "timestamp", "end_time", "title"]:
        order_by = "orderid"
        order = "asc"
    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT pollid FROM poll WHERE pollid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, timestamp DESC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_pollid is not None:
        for tt in t:
            if tt[0] == after_pollid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT pollid, userid, title, description, config, orderid, is_pinned, timestamp, end_time FROM poll WHERE pollid >= 0 {limit} ORDER BY is_pinned DESC, {order_by} {order}, timestamp DESC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    idx = {}
    qstr = ""
    for i in range(len(t)):
        tt = t[i]
        configl = str2list(tt[4])
        config = copy.deepcopy(POLL_DEFAULT_CONFIG)
        for j in range(len(POLL_CONFIG_KEYS)):
            if j < len(configl):
                config[POLL_CONFIG_KEYS[j]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[j]](configl[j])
        qstr += f"OR pollid = {tt[0]} "
        idx[tt[0]] = i
        ret.append({"pollid": tt[0], "title": tt[2], "description": decompress(tt[3]), "choices": [], "voted": False, "config": config, "end_time": tt[8], "creator": await GetUserInfo(request, userid = tt[1]), "orderid": tt[5], "is_pinned": TF[tt[6]], "timestamp": tt[7]})

    await app.db.execute(dhrid, f"SELECT DISTINCT pollid FROM poll_vote WHERE userid = {userid} AND ({qstr[3:]})")
    t = await app.db.fetchall(dhrid)
    voted = []
    for tt in t:
        voted.append(tt[0])

    choiceidx = {}
    await app.db.execute(dhrid, f"SELECT pollid, choiceid, orderid, content FROM poll_choice WHERE {qstr[3:]} ORDER BY pollid ASC, orderid ASC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        (pollid, choiceid, orderid, content) = tt
        choiceidx[choiceid] = len(ret[idx[pollid]]["choices"])
        if isstaff or (config["show_stats_before_vote"] or pollid in voted and config["show_stats"] or config["show_stats_when_ended"] and ret[idx[pollid]]["end_time"] is not None and ret[idx[pollid]]["end_time"] < int(time.time())):
            ret[idx[pollid]]["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": 0, "voted": False})
        else:
            ret[idx[pollid]]["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": None, "voted": False})

    await app.db.execute(dhrid, f"SELECT pollid, choiceid FROM poll_vote WHERE {qstr[3:]} AND userid = {userid} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        (pollid, choiceid) = tt
        ret[idx[pollid]]["choices"][choiceidx[choiceid]]["voted"] = True
        ret[idx[pollid]]["voted"] = True

    await app.db.execute(dhrid, f"SELECT pollid, choiceid, COUNT(userid) FROM poll_vote WHERE {qstr[3:]} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        (pollid, choiceid, count) = tt
        config = ret[idx[pollid]]["config"]
        if isstaff or (config["show_stats_before_vote"] or pollid in voted and config["show_stats"] or config["show_stats_when_ended"] and ret[idx[pollid]]["end_time"] is not None and ret[idx[pollid]]["end_time"] < int(time.time())):
            ret[idx[pollid]]["choices"][choiceidx[choiceid]]["votes"] = count

    return {"list": ret[:page_size], "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_poll(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /polls', 60, 120)
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
    isstaff = checkPerm(app, au["roles"], ["administrator", "manage_polls"])
    await ActivityUpdate(request, au["uid"], "poll")

    await app.db.execute(dhrid, f"SELECT pollid, userid, title, description, config, orderid, is_pinned, timestamp, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    tt = t[0]

    configl = str2list(tt[4])
    config = copy.deepcopy(POLL_DEFAULT_CONFIG)
    for i in range(len(POLL_CONFIG_KEYS)):
        if i < len(configl):
            config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](configl[i])
    ret = {"pollid": tt[0], "title": tt[2], "description": decompress(tt[3]), "choices": [], "voted": False, "config": config, "end_time": tt[8], "creator": await GetUserInfo(request, userid = tt[1]), "orderid": tt[5], "is_pinned": TF[tt[6]], "timestamp": tt[7]}

    await app.db.execute(dhrid, f"SELECT DISTINCT pollid FROM poll_vote WHERE userid = {userid} AND pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    voted = False
    if len(t) > 0:
        voted = True

    choiceidx = {}
    await app.db.execute(dhrid, f"SELECT pollid, choiceid, orderid, content FROM poll_choice WHERE pollid = {pollid} ORDER BY orderid ASC")
    t = await app.db.fetchall(dhrid)
    for i in range(len(t)):
        (_, choiceid, orderid, content) = t[i]
        choiceidx[choiceid] = i
        votes = None
        voters = None
        if isstaff or (config["show_stats_before_vote"] or voted and config["show_stats"] or config["show_stats_when_ended"] and ret["end_time"] is not None and ret["end_time"] < int(time.time())):
            votes = 0
            if isstaff or config["show_voter"]:
                voters = []
        ret["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": votes, "voted": False, "voters": voters})

    if isstaff or (config["show_stats_before_vote"] or voted and config["show_stats"] or config["show_stats_when_ended"] and ret["end_time"] is not None and ret["end_time"] < int(time.time())):
        await app.db.execute(dhrid, f"SELECT pollid, choiceid, COUNT(userid) FROM poll_vote WHERE pollid = {pollid} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            (_, choiceid, count) = tt
            ret["choices"][choiceidx[choiceid]]["votes"] = count

            await app.db.execute(dhrid, f"SELECT pollid, choiceid FROM poll_vote WHERE pollid = {pollid} AND userid = {userid} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                (pollid, choiceid) = tt
                ret["choices"][choiceidx[choiceid]]["voted"] = True
                ret["voted"] = True

        if isstaff or config["show_voter"]:
            await app.db.execute(dhrid, f"SELECT choiceid, userid FROM poll_vote WHERE pollid = {pollid} ORDER BY choiceid ASC, timestamp ASC")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                (choiceid, voters_userid) = tt
                ret["choices"][choiceidx[choiceid]]["voters"].append(await GetUserInfo(request, userid = voters_userid))

    return ret

async def put_poll_vote(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    '''Put poll vote

    JSON: {"choices": list}

    [NOTE] `choices` must contain a list of `choiceid`
    [NOTE] Modifying vote is not allowed, use PATCH'''

    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PUT /polls/vote', 60, 60)
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

    data = await request.json()
    choiceids = []
    try:
        choices = data["choiceids"]
        for choiceid in choices:
            choiceids.append(int(choiceid))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT config, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    (configl, end_time) = t[0]
    configl = str2list(configl)
    config = copy.deepcopy(POLL_DEFAULT_CONFIG)
    for i in range(len(POLL_CONFIG_KEYS)):
        if i < len(configl):
            config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](configl[i])

    if end_time is not None and end_time < int(time.time()):
        response.status_code = 409
        return {"error": ml.tr(request, "poll_already_ended", force_lang = au["language"])}
    if len(choiceids) > config["max_choice"]:
        response.status_code = 400
        return {"error": ml.tr(request, "selected_too_many_choices", var = {"count": config["max_choice"]}, force_lang = au["language"])}

    # NOTE: PUT route only allows creating new votes, use PATCH to modify votes
    await app.db.execute(dhrid, f"SELECT userid FROM poll_vote WHERE pollid = {pollid} AND userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 409
        return {"error": ml.tr(request, "user_already_voted", force_lang = au["language"])}

    allowed_choiceids = []
    await app.db.execute(dhrid, f"SELECT choiceid FROM poll_choice WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        allowed_choiceids.append(tt[0])
    for choiceid in choiceids:
        if choiceid not in allowed_choiceids:
            response.status_code = 400
            return {"error": ml.tr(request, "selected_invalid_choice", force_lang = au["language"])}

    for choiceid in choiceids:
        await app.db.execute(dhrid, f"INSERT INTO poll_vote(pollid, choiceid, userid, timestamp) VALUES ({pollid}, {choiceid}, {userid}, {int(time.time())})")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def patch_poll_vote(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    '''Patch poll vote

    JSON: {"choices": list}

    [NOTE] `choices` must contain a list of `choiceid`
    [NOTE] This will overwrite all voted choices of the poll for the user'''

    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /polls/vote', 60, 60)
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

    data = await request.json()
    choiceids = []
    try:
        choices = data["choiceids"]
        for choiceid in choices:
            choiceids.append(int(choiceid))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT config, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    (configl, end_time) = t[0]
    configl = str2list(configl)
    config = copy.deepcopy(POLL_DEFAULT_CONFIG)
    for i in range(len(POLL_CONFIG_KEYS)):
        if i < len(config):
            config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](configl[i])

    if end_time is not None and end_time < int(time.time()):
        response.status_code = 409
        return {"error": ml.tr(request, "poll_already_ended", force_lang = au["language"])}
    if len(choiceids) > config["max_choice"]:
        response.status_code = 400
        return {"error": ml.tr(request, "selected_too_many_choices", var = {"count": config["max_choice"]}, force_lang = au["language"])}

    # NOTE: PATCH route only allows modifying votes, use PUT to create votes.
    await app.db.execute(dhrid, f"SELECT userid FROM poll_vote WHERE pollid = {pollid} AND userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "user_not_voted", force_lang = au["language"])}

    if config["allow_modify_vote"] == 0:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_vote_not_allowed", force_lang = au["language"])}

    allowed_choiceids = []
    await app.db.execute(dhrid, f"SELECT choiceid FROM poll_choice WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        allowed_choiceids.append(tt[0])
    for choiceid in choiceids:
        if choiceid not in allowed_choiceids:
            response.status_code = 400
            return {"error": ml.tr(request, "selected_invalid_choice", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM poll_vote WHERE pollid = {pollid} AND userid = {userid}")
    for choiceid in choiceids:
        await app.db.execute(dhrid, f"INSERT INTO poll_vote(pollid, choiceid, userid, timestamp) VALUES ({pollid}, {choiceid}, {userid}, {int(time.time())})")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_poll_vote(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    '''Delete poll vote

    [NOTE] This will deleted all voted choices of the poll for the user'''

    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /polls/vote', 60, 60)
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

    await app.db.execute(dhrid, f"SELECT config, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    (configl, end_time) = t[0]
    configl = str2list(configl)
    config = copy.deepcopy(POLL_DEFAULT_CONFIG)
    for i in range(len(POLL_CONFIG_KEYS)):
        if i < len(configl):
            config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](configl[i])

    if end_time is not None and end_time < int(time.time()):
        response.status_code = 409
        return {"error": ml.tr(request, "poll_already_ended", force_lang = au["language"])}

    # NOTE: DELETE route only allows deleting all votes, use PUT to create votes first.
    await app.db.execute(dhrid, f"SELECT userid FROM poll_vote WHERE pollid = {pollid} AND userid = {userid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "user_not_voted", force_lang = au["language"])}

    if config["allow_modify_vote"] == 0:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_vote_not_allowed", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM poll_vote WHERE pollid = {pollid} AND userid = {userid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_poll(request: Request, response: Response, authorization: str = Header(None)):
    '''Post a poll

    `config`: dict containing optional keys "max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter", "show_stats_when_ended"
    `choices`: list of string choices
    `end_time`: int/null'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /polls', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_polls"])
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

        choices = data["choices"]
        if type(choices) is not list:
            response.status_code = 400
            return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        if len(choices) > 10:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "choices", "limit": "10"}, force_lang = au["language"])}
        new_choices = []
        for choice in choices:
            choice = str(choice)
            if len(choice) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "single_choice", "limit": "200"}, force_lang = au["language"])}
            new_choices.append(choice)
        choices = new_choices

        if "config" in data.keys():
            config = data["config"]
            if type(config) is not dict:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            new_config = {}
            for key in POLL_CONFIG_KEYS:
                if key not in config.keys():
                    new_config[key] = copy.deepcopy(POLL_DEFAULT_CONFIG)[key]
                else:
                    new_config[key] = config[key]
            config = new_config
            try:
                config["max_choice"] = int(config["max_choice"])
                for key in ["allow_modify_vote", "show_stats", "show_voter", "show_stats_before_vote", "show_stats_when_ended"]:
                    config[key] = int(bool(config[key]))
            except:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        else:
            config = copy.deepcopy(POLL_DEFAULT_CONFIG)
        new_config = []
        for key in config.keys():
            new_config.append(int(config[key]))
        config = list2str(new_config)

        if "end_time" not in data.keys():
            data["end_time"] = 0
        end_time = nint(data["end_time"])
        if end_time <= 0:
            end_time = "NULL"
        else:
            if abs(end_time) > 9223372036854775807:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "end_time", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}

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

    await app.db.execute(dhrid, f"INSERT INTO poll(userid, title, description, config, orderid, is_pinned, end_time, timestamp) VALUES ({au['userid']}, '{convertQuotation(title)}', '{convertQuotation(compress(description))}', '{config}', {orderid}, {is_pinned}, {end_time}, {int(time.time())})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    pollid = (await app.db.fetchone(dhrid))[0]
    for i in range(len(choices)):
        await app.db.execute(dhrid, f"INSERT INTO poll_choice(pollid, orderid, content) VALUES ({pollid}, {i}, '{convertQuotation(choices[i])}')")
    await app.db.commit(dhrid)
    await AuditLog(request, au["uid"], ml.ctr(request, "created_poll", var = {"id": pollid}))

    await notification_to_everyone(request, "new_poll", ml.spl("new_poll_with_title", var = {"title": title}), discord_embed = {"title": title, "description": description, "fields": [{"name": ml.spl("choices"), "value": " - " + "\n - ".join(choices), "inline": False}], "footer": {"text": ml.spl("new_poll"), "icon_url": app.config.logo_url}}, only_to_members=True)

    def setvar(msg):
        return msg.replace("{mention}", f"<@{au['discordid']}>").replace("{name}", au['name']).replace("{userid}", str(au['userid'])).replace("{uid}", str(au['uid'])).replace("{avatar}", validateUrl(au['avatar'])).replace("{id}", str(pollid)).replace("{title}", title).replace("{description}", description)

    for meta in app.config.poll_forwarding:
        meta = Dict2Obj(meta)
        if meta.webhook_url != "" or meta.channel_id != "":
            await AutoMessage(app, meta, setvar)

    return {"pollid": pollid}

async def patch_poll(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    '''Patch a poll

    `config`: dict containing keys "max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter", "show_stats_when_ended"
    `choices`: list of object choices {"choiceid": int, "orderid": int}
    `end_time`: int/null
    [NOTE] Editing choices is not allowed'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'PATCH /polls', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_polls"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT title, description, config, orderid, is_pinned, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    (title, description, config, orderid, is_pinned, end_time) = t[0]
    if end_time is None:
        end_time = "NULL"
    description = decompress(description)

    old_configl = str2list(config)
    old_config = copy.deepcopy(POLL_DEFAULT_CONFIG)
    for i in range(min(len(old_configl), len(POLL_CONFIG_KEYS))):
        old_config[POLL_CONFIG_KEYS[i]] = POLL_CONFIG_TYPE[POLL_CONFIG_KEYS[i]](old_configl[i])

    await app.db.execute(dhrid, f"SELECT choiceid, orderid FROM poll_choice WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    choices_orderid = {}
    for tt in t:
        choices_orderid[tt[0]] = None

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

        if "choices" in data.keys():
            # NOTE
            # The choice item must be dict!
            # {"choiceid": N, "orderid": N}
            choices = data["choices"]
            if type(choices) is not list:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            if len(choices) > 10:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "choices", "limit": "10"}, force_lang = au["language"])}
            for choice in choices:
                if "choiceid" in choice.keys() and "orderid" in choice.keys() and int(choice["choiceid"]) in choices_orderid.keys():
                    choices_orderid[choice["choiceid"]] = choice["orderid"]

        if "config" in data.keys():
            config = data["config"]
            if type(config) is not dict:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            new_config = old_config
            for key in POLL_CONFIG_KEYS:
                if key in config.keys():
                    new_config[key] = config[key]
            config = new_config
            try:
                config["max_choice"] = int(config["max_choice"])
                for key in ["allow_modify_vote", "show_stats", "show_voter", "show_stats_before_vote", "show_stats_when_ended"]:
                    config[key] = int(bool(config[key]))
            except:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
            new_config = []
            for key in config.keys():
                new_config.append(int(config[key]))
            config = list2str(new_config)

        if "end_time" in data.keys():
            end_time = nint(data["end_time"])
            if end_time <= 0:
                end_time = "NULL"
            else:
                if abs(end_time) > 9223372036854775807:
                    response.status_code = 400
                    return {"error": ml.tr(request, "value_too_large", var = {"item": "end_time", "limit": "9,223,372,036,854,775,807"}, force_lang = au["language"])}

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

    await app.db.execute(dhrid, f"UPDATE poll SET title = '{convertQuotation(title)}', description = '{convertQuotation(compress(description))}', config = '{config}', orderid = {orderid}, is_pinned = {is_pinned}, end_time = {end_time} WHERE pollid = {pollid}")
    for choiceid in choices_orderid.keys():
        orderid = choices_orderid[choiceid]
        if orderid is not None:
            await app.db.execute(dhrid, f"UPDATE poll_choice SET orderid = {orderid} WHERE choiceid = {choiceid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "updated_poll", var = {"id": pollid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def delete_poll(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'DELETE /polls', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["administrator", "manage_polls"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT * FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM poll WHERE pollid = {pollid}")
    await app.db.execute(dhrid, f"DELETE FROM poll_choice WHERE pollid = {pollid}")
    await app.db.execute(dhrid, f"DELETE FROM poll_vote WHERE pollid = {pollid}")
    await AuditLog(request, au["uid"], ml.ctr(request, "deleted_poll", var = {"id": pollid}))
    await app.db.commit(dhrid)

    return Response(status_code=204)
