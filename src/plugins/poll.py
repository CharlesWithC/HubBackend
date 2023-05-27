# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *

POLL_CONFIG_KEYS = ["max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter"]
POLL_DEFAULT_CONFIG = {"max_choice": 1, "allow_modify_vote": False, "show_stats": True, "show_stats_before_vote": False, "show_voter": False}
# show_stats(before_vote) must be 1 to show_voter
# show_stats => show stats after vote
# show_stats_before_vote => overwrite show_stats (aka show stats after/before vote)

# NOTE: To end a poll, set its `end_time` to current timestamp

async def get_list(request: Request, response: Response, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_pollid: Optional[int] = None, \
        order_by: Optional[str] = "orderid", order: Optional[str] = "asc", \
        query: Optional[str] = "", creator_userid: Optional[int] = None):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /polls/list', 60, 60)
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
    isstaff = checkPerm(app, au["roles"], ["admin", "poll"])
    await ActivityUpdate(request, au["uid"], "poll")

    limit = ""
    if query != "":
        query = convertQuotation(query).lower()
        limit += f"AND LOWER(title) LIKE '%{query[:200]}%' "
    if creator_userid is not None:
        limit += f"AND userid = {creator_userid} "

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order_by not in ["orderid", "pollid", "timestamp", "end_time", "title"]:
        order_by = "orderid"
        order = "asc"
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
        config = {}
        for j in range(len(POLL_CONFIG_KEYS)):
            config[POLL_CONFIG_KEYS[j]] = configl[j]
        qstr += f"OR pollid = {tt[0]} "
        idx[tt[0]] = i
        ret.append({"pollid": tt[0], "title": tt[2], "description": decompress(tt[3]), "choices": [], "config": config, "end_time": tt[8], "creator": await GetUserInfo(request, userid = tt[1]), "orderid": tt[5], "is_pinned": TF[tt[6]], "timestamp": tt[7]})

    await app.db.execute(dhrid, f"SELECT DISTINCT pollid FROM poll_vote WHERE userid = {userid} AND ({qstr[3:]})")
    t = await app.db.fetchall(dhrid)
    voted = []
    for tt in t:
        voted.append(tt[0])

    choiceidx = {}
    await app.db.execute(dhrid, f"SELECT pollid, choiceid, orderid, content FROM poll_choice WHERE {qstr[3:]} ORDER BY pollid ASC, orderid ASC")
    t = await app.db.fetchall(dhrid)
    for i in range(len(t)):
        (pollid, choiceid, orderid, content) = t[i]
        choiceidx[choiceid] = i
        if isstaff or (config["show_stats_before_vote"] or pollid in voted and config["show_stats"]):
            ret[idx[pollid]]["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": 0})
        else:
            ret[idx[pollid]]["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": None})

    await app.db.execute(dhrid, f"SELECT pollid, choiceid, COUNT(userid) FROM poll_vote WHERE {qstr[3:]} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        (pollid, choiceid, count) = tt
        config = ret[idx[pollid]]["config"]
        if isstaff or (config["show_stats_before_vote"] or pollid in voted and config["show_stats"]):
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
    isstaff = checkPerm(app, au["roles"], ["admin", "poll"])
    await ActivityUpdate(request, au["uid"], "poll")

    await app.db.execute(dhrid, f"SELECT pollid, userid, title, description, config, orderid, is_pinned, timestamp, end_time FROM poll WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "poll_not_found", force_lang = au["language"])}
    tt = t[0]

    configl = str2list(tt[4])
    config = {}
    for i in range(len(POLL_CONFIG_KEYS)):
        config[POLL_CONFIG_KEYS[i]] = configl[i]
    ret = {"pollid": tt[0], "title": tt[2], "description": decompress(tt[3]), "choices": [], "config": config, "end_time": tt[8], "creator": await GetUserInfo(request, userid = tt[1]), "orderid": tt[5], "is_pinned": TF[tt[6]], "timestamp": tt[7]}

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
        if isstaff or (ret["config"]["show_stats_before_vote"] or voted and ret["config"]["show_stats"]):
            votes = 0
            if isstaff or ret["config"]["show_voter"]:
                voters = []
        ret["choices"].append({"choiceid": choiceid, "orderid": orderid, "content": content, "votes": votes, "voters": voters})

    if isstaff or (ret["config"]["show_stats_before_vote"] or voted and ret["config"]["show_stats"]):
        await app.db.execute(dhrid, f"SELECT pollid, choiceid, COUNT(userid) FROM poll_vote WHERE pollid = {pollid} GROUP BY choiceid ORDER BY pollid ASC, choiceid ASC")
        t = await app.db.fetchall(dhrid)
        for tt in t:
            (_, choiceid, count) = tt
            ret["choices"][choiceidx[choiceid]]["votes"] = count

        if isstaff or ret["config"]["show_voter"]:
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
    config = {}
    for i in range(len(POLL_CONFIG_KEYS)):
        config[POLL_CONFIG_KEYS[i]] = configl[i]

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
    config = {}
    for i in range(len(POLL_CONFIG_KEYS)):
        config[POLL_CONFIG_KEYS[i]] = configl[i]

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
    config = {}
    for i in range(len(POLL_CONFIG_KEYS)):
        config[POLL_CONFIG_KEYS[i]] = configl[i]

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

    `config`: dict containing optional keys "max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter"
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

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "poll"])
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    data = await request.json()
    try:
        title = convertQuotation(data["title"])
        if len(data["title"]) > 200:
            response.status_code = 400
            return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        description = compress(data["description"])
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
                    new_config[key] = POLL_DEFAULT_CONFIG[key]
                else:
                    new_config[key] = config[key]
            config = new_config
            try:
                config["max_choice"] = int(config["max_choice"])
                for key in ["allow_modify_vote", "show_stats", "show_voter", "show_stats_before_vote"]:
                    config[key] = int(bool(config[key]))
            except:
                response.status_code = 400
                return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
        else:
            config = POLL_DEFAULT_CONFIG
        new_config = []
        for key in config.keys():
            new_config.append(int(config[key]))
        config = list2str(new_config)

        if "end_time" not in data.keys():
            data["end_time"] = 0
        end_time = nint(data["end_time"])
        if end_time <= 0:
            end_time = "NULL"

        if "orderid" not in data.keys():
            data["orderid"] = 0
        if "is_pinned" not in data.keys():
            data["is_pinned"] = False
        orderid = int(data["orderid"])
        if orderid < -2147483647 or orderid > 2147483647:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO poll(userid, title, description, config, orderid, is_pinned, end_time, timestamp) VALUES ({au['userid']}, '{title}', '{description}', '{config}', {orderid}, {is_pinned}, {end_time}, {int(time.time())})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    pollid = (await app.db.fetchone(dhrid))[0]
    for i in range(len(choices)):
        await app.db.execute(dhrid, f"INSERT INTO poll_choice(pollid, orderid, content) VALUES ({pollid}, {i}, '{convertQuotation(choices[i])}')")
    await app.db.commit(dhrid)
    await AuditLog(request, au["uid"], ml.ctr(request, "created_poll", var = {"id": pollid}))

    await notification_to_everyone(request, "new_poll", ml.spl("new_poll_with_title", var = {"title": title}), discord_embed = {"title": title, "description": decompress(description), "fields": [{"name": ml.spl("choices"), "value": " - " + "\n - ".join(choices)}], "footer": {"text": ml.spl("new_poll"), "icon_url": app.config.logo_url}})

    return {"pollid": pollid}

async def patch_poll(request: Request, response: Response, pollid: int, authorization: str = Header(None)):
    '''Patch a poll

    `config`: dict containing keys "max_choice", "allow_modify_vote", "show_stats", "show_stats_before_vote", "show_voter"
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

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "poll"])
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
    if end_time == None:
        end_time = "NULL"

    old_configl = str2list(config)
    old_config = {}
    for i in range(len(POLL_CONFIG_KEYS)):
        old_config[POLL_CONFIG_KEYS[i]] = old_configl[i]

    await app.db.execute(dhrid, f"SELECT choiceid, orderid FROM poll_choice WHERE pollid = {pollid}")
    t = await app.db.fetchall(dhrid)
    choices_orderid = {}
    for tt in t:
        choices_orderid[tt[0]] = None

    data = await request.json()
    try:
        if "title" in data.keys():
            title = convertQuotation(data["title"])
            if len(data["title"]) > 200:
                response.status_code = 400
                return {"error": ml.tr(request, "content_too_long", var = {"item": "title", "limit": "200"}, force_lang = au["language"])}
        if "description" in data.keys():
            description = compress(data["description"])
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
                for key in ["allow_modify_vote", "show_stats", "show_voter", "show_stats_before_vote"]:
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

        if "orderid" in data.keys():
            orderid = int(data["orderid"])
            if orderid < -2147483647 or orderid > 2147483647:
                response.status_code = 400
                return {"error": ml.tr(request, "value_too_large", var = {"item": "orderid", "limit": "2,147,483,647"}, force_lang = au["language"])}
        if "is_pinned" in data.keys():
            is_pinned = int(bool(data["is_pinned"]))
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE poll SET title = '{title}', description = '{description}', config = '{config}', orderid = {orderid}, is_pinned = {is_pinned}, end_time = {end_time} WHERE pollid = {pollid}")
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

    au = await auth(authorization, request, allow_application_token = True, required_permission = ["admin", "poll"])
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
