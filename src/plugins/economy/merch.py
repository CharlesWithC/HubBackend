# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *


# The beneficial party of merch income is "company".
# All merch income will be transferred to the "company" account.

async def get_all_merch(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/merch', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    return app.config.economy.merch

async def get_merch_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_itemid: Optional[int] = None, \
        merchid: Optional[str] = "", owner: Optional[int] = None, \
        min_price: Optional[int] = None, max_price: Optional[int] = None, \
        purchased_after: Optional[int] = None, purchased_before: Optional[int] = None, \
        order_by: Optional[str] = "price", order: Optional[int] = "desc"):
    '''Get a list of merch.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/merch/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(request, au["uid"], "economy_merch")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    limit = ""
    if merchid != "":
        merchid = convertQuotation(merchid).lower()
        limit += f"AND LOWER(merchid) LIKE '%{merchid[:200]}%' "

    if owner is not None:
        limit += f"AND userid = {owner} "

    if min_price is not None:
        limit += f"AND buy_price >= {min_price} "
    if max_price is not None:
        limit += f"AND buy_price <= {max_price} "

    if purchased_after is not None:
        limit += f"AND purchase_timestamp >= {purchased_after} "
    if purchased_before is not None:
        limit += f"AND purchase_timestamp <= {purchased_before} "

    if order_by not in ['merchid', 'itemid', 'userid', 'price', 'purchase_timestamp']:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}

    order_by = "buy_price" if order_by == "price" else order_by

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT itemid FROM economy_merch WHERE itemid >= 0 AND userid >= 0 {limit} ORDER BY {order_by} {order},merchid ASC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_itemid is not None:
        for tt in t:
            if tt[0] == after_itemid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT itemid, merchid, userid, buy_price, sell_price, purchase_timestamp FROM economy_merch WHERE itemid >= 0 AND userid >= 0 {limit} ORDER BY {order_by} {order}, merchid ASC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"itemid": tt[0], "merchid": tt[1], "owner": await GetUserInfo(request, userid = tt[2]), "price": tt[3], "purchase_timestamp": tt[5]})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def post_merch_purchase(request: Request, response: Response, merchid: str, authorization: str = Header(None)):
    '''Purchase a merch, returns `itemid`, `cost`, `balance`.

    JSON: `{"owner": Optional[str]}`

    `owner` can be `self` | `user-{userid}`'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/merch/purchase', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    data = await request.json()
    try:
        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if merchid not in app.merch.keys():
        response.status_code = 404
        return {"error": ml.tr(request, "merch_not_found", force_lang = au["language"])}
    merch = app.merch[merchid]
    merchid = convertQuotation(merchid)

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_merch"])

    # check access
    if owner == "company" and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_company_forbidden", var = {"item": ml.tr(request, "merch", force_lang = au["language"])}, force_lang = au["language"])}

    # check owner
    if owner == "self":
        foruser = userid
        opuserid = userid
    elif owner.startswith("user-"):
        foruser = owner.split("-")[1]
        opuserid = userid
        if not isint(foruser):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
        foruser = int(foruser)
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    else:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}

    # check balance
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {opuserid} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, opuserid) if balance == 0 else None
    await app.db.execute(dhrid, "SELECT balance FROM economy_balance WHERE userid = -1000 FOR UPDATE")
    company_balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, -1000) if company_balance == 0 else None

    if merch["buy_price"] > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    ts = int(time.time())
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {merch['buy_price']} WHERE userid = {opuserid}")
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {merch['buy_price']} WHERE userid = {-1000}")
    await app.db.execute(dhrid, f"INSERT INTO economy_merch(merchid, userid, buy_price, sell_price, purchase_timestamp) VALUES ('{merchid}', {foruser}, {merch['buy_price']}, {merch['sell_price']}, {ts})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    itemid = (await app.db.fetchone(dhrid))[0]
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({opuserid}, -1000, {merch['buy_price']}, 'm{itemid}-purchase', 'for-user-{foruser}', {round(balance - merch['buy_price'])}, {int(company_balance + merch['buy_price'])}, {ts})")
    await app.db.commit(dhrid)

    return {"itemid": itemid, "cost": merch['buy_price'], "balance": round(balance - merch['buy_price'])}

async def post_merch_transfer(request: Request, response: Response, itemid: int, authorization: str = Header(None)):
    '''Transfer a merch (ownership).

    JSON: `{"owner": Optional[str], "message": Optional[str]}`

    `owner` can be `self` | `user-{userid}`'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/merch/transfer', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    data = await request.json()
    try:
        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"

        if "message" in data.keys():
            message = data["message"]
        else:
            message = ""
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    # check owner
    if owner == "self":
        foruser = userid
    elif owner.startswith("user-"):
        foruser = owner.split("-")[1]
        if not isint(foruser):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
        foruser = int(foruser)
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    else:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT merchid, userid FROM economy_merch WHERE itemid = {itemid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "merch_not_found", force_lang = au["language"])}
    (merchid, current_owner) = (t[0][0], t[0][1])
    if current_owner == foruser:
        response.status_code = 409
        return {"error": ml.tr(request, "new_owner_conflict", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_merch"])

    # company garage but not manager or not owned garage
    # manager can transfer anyone's garage
    if not permok:
        if current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "merch", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_merch SET userid = {foruser} WHERE itemid = {itemid}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_owner}, {foruser}, NULL, 'm{itemid}-transfer', '{convertQuotation(message)}', NULL, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    from_user = await GetUserInfo(request, userid = current_owner, is_internal_function = True)
    to_user = await GetUserInfo(request, userid = foruser, is_internal_function = True)
    from_user_language = await GetUserLanguage(request, from_user["uid"])
    to_user_language = await GetUserLanguage(request, to_user["uid"])

    from_message = ""
    to_message = ""
    if message != "":
        from_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = from_user_language)
        to_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = to_user_language)

    merch = ml.ctr(request, "unknown") + " (" + merchid + ")"
    if merchid in app.merch.keys():
        merch = app.merch[merchid]["name"]

    await notification(request, "economy", from_user["uid"], ml.tr(request, "economy_sent_transaction_item", var = {"type": "1x " + ml.tr(request, "merch", force_lang = from_user_language).title(), "name": merch, "to_user": to_user["name"], "to_userid": to_user["userid"] if to_user["userid"] is not None else "N/A", "message": from_message}, force_lang = from_user_language))
    await notification(request, "economy", to_user["uid"], ml.tr(request, "economy_received_transaction_item", var = {"type": "1x " + ml.tr(request, "merch", force_lang = from_user_language).title(), "name": merch, "from_user": from_user["name"], "from_userid": from_user["userid"] if from_user["userid"] is not None else "N/A", "message": to_message}, force_lang = to_user_language))

    return Response(status_code=204)

async def post_merch_sell(request: Request, response: Response, itemid: int, authorization: str = Header(None)):
    '''Sell a merch, returns `refund`, `balance`.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/merch/sell', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    await app.db.new_conn(dhrid, db_name = app.config.db_name)

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    # check current owner
    await app.db.execute(dhrid, f"SELECT userid, sell_price FROM economy_merch WHERE itemid = {itemid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "merch_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    refund = t[0][1]

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_merch"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "merch", force_lang = au["language"])}, force_lang = au["language"])}

    # check balance
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, current_owner) if balance == 0 else None
    await app.db.execute(dhrid, "SELECT balance FROM economy_balance WHERE userid = -1000 FOR UPDATE")
    company_balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, -1000) if company_balance == 0 else None

    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {refund} WHERE userid = -1000")
    await app.db.execute(dhrid, f"DELETE FROM economy_merch WHERE itemid = {itemid}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1000, {current_owner}, {refund}, 'm{itemid}-sell', '', {round(company_balance - refund)}, {round(balance + refund)}, {int(time.time())})")
    await app.db.commit(dhrid)

    return {"refund": refund, "balance": round(balance + refund)}
