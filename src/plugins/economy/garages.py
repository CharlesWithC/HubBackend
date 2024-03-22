# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *
from plugins.economy.trucks import GetTruckInfo


async def get_all_garages(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/garages', 60, 30)
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

    return app.config.economy.garages

async def get_garage_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_garageid: Optional[str] = None,
        min_trucks: Optional[int] = None, max_trucks: Optional[int] = None,
        min_income: Optional[int] = None, max_income: Optional[int] = None,
        order_by: Optional[str] = "income", order: Optional[str] = "desc"):
    '''Get a list of garages.

    `order_by` can be `income`, `truck`, `slot`'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/garages/list', 60, 60)
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
    await ActivityUpdate(request, au["uid"], "economy_garages")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    having = ""
    if min_trucks is not None:
        having += f"AND tot_truck >= {min_trucks} "
    if max_trucks is not None:
        having += f"AND tot_truck <= {max_trucks} "
    if min_income is not None:
        having += f"AND tot_income >= {min_income} "
    if max_income is not None:
        having += f"AND tot_income <= {max_income} "
    if having.startswith("AND "):
        having = "HAVING " + having[4:]

    cvt = {"income": "tot_income", "truck": "tot_truck", "slot": "tot_slot"}
    if order_by in cvt.keys():
        order_by = cvt[order_by]
    if order_by not in ['garageid', 'tot_income', 'tot_truck', 'tot_slot']:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order_by"})}

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT economy_garage.garageid, MIN(economy_garage.purchase_timestamp) AS first_purchase, COUNT(DISTINCT economy_garage.slotid) AS tot_slot, COUNT(DISTINCT economy_garage.userid) AS tot_owner, COUNT(DISTINCT economy_truck.vehicleid) AS tot_truck, SUM(economy_truck.income) AS tot_income FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid >= 0 \
                         GROUP BY economy_garage.garageid {having} ORDER BY {order_by} {order}, economy_garage.garageid ASC")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_garageid is not None:
        for tt in t:
            if tt[0] == after_garageid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT economy_garage.garageid, MIN(economy_garage.purchase_timestamp) AS first_purchase, COUNT(DISTINCT economy_garage.slotid) AS tot_slot, COUNT(DISTINCT economy_garage.userid) AS tot_owner, COUNT(DISTINCT economy_truck.vehicleid) AS tot_truck, SUM(economy_truck.income) AS tot_income FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid >= 0 \
                         GROUP BY economy_garage.garageid {having} ORDER BY {order_by} {order}, economy_garage.garageid ASC LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        await app.db.execute(dhrid, f"SELECT userid FROM economy_garage WHERE garageid = '{tt[0]}' AND note = 'garage-owner'")
        p = await app.db.fetchall(dhrid)
        ret.append({"garageid": tt[0], "garage_owner": (await GetUserInfo(request, userid = p[0][0])), "slots": tt[2], "slot_owners": nint(tt[3]), "trucks": nint(tt[4]), "income": nint(tt[5]), "purchase_timestamp": tt[1]})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_garage(request: Request, response: Response, garageid: str, authorization: str = Header(None)):
    '''Get info of a specific garage.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/garages/garageid', 60, 60)
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
    await ActivityUpdate(request, au["uid"], f"economy_garages_{garageid}")

    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT economy_garage.garageid, MIN(economy_garage.purchase_timestamp) AS first_purchase, COUNT(DISTINCT economy_garage.slotid) AS tot_slot, COUNT(DISTINCT economy_garage.userid) AS tot_owner, COUNT(DISTINCT economy_truck.vehicleid) AS tot_truck, SUM(economy_truck.income) AS tot_income FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid >= 0 AND economy_garage.garageid = '{garageid}' \
                         GROUP BY economy_garage.garageid")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "garage_not_found", force_lang = au["language"])}
    tt = t[0]
    await app.db.execute(dhrid, f"SELECT userid FROM economy_garage WHERE garageid = '{tt[0]}' AND note = 'garage-owner'")
    p = await app.db.fetchall(dhrid)
    return {"garageid": tt[0], "garage_owner": (await GetUserInfo(request, userid = p[0][0])), "slots": tt[2], "slot_owners": nint(tt[3]), "trucks": nint(tt[4]), "income": nint(tt[5]), "purchase_timestamp": tt[1]}

async def get_garage_slots_list(request: Request, response: Response, garageid: str, authorization: str = Header(None),
        page: Optional[int] = 1, page_size: Optional[int] = 20, after_slotid: Optional[int] = None, \
        owner: Optional[int] = None, must_have_truck: Optional[bool] = False, \
        purchased_after: Optional[int] = None, purchased_before: Optional[int] = None,
        order: Optional[str] = "asc"):
    '''Get the slots of a specific garage.

    `order_by` is `purchase_timestamp`.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/garages/slots/list', 60, 60)
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
    await ActivityUpdate(request, au["uid"], f"economy_garages_{garageid}")

    if page < 1:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page"})}
    if page_size < 1 or page_size > 250:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "page_size"})}

    order = order.lower()
    if order not in ["asc", "desc"]:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_value", var = {"key": "order"})}

    garageid = convertQuotation(garageid)

    having = ""
    if must_have_truck:
        having += "AND economy_truck.vehicleid != NULL "
    if purchased_after is not None:
        having += f"AND economy_garage.purchase_timestamp >= {purchased_after} "
    if purchased_before is not None:
        having += f"AND economy_garage.purchase_timestamp <= {purchased_before} "
    if owner is not None:
        having += f"AND economy_garage.userid = {owner} "

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT economy_garage.slotid, economy_garage.userid, economy_truck.vehicleid, economy_truck.userid, economy_garage.purchase_timestamp FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid >= 0 AND economy_garage.garageid = '{garageid}' \
                         ORDER BY economy_garage.purchase_timestamp {order}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_slotid is not None:
        for tt in t:
            if tt[0] == after_slotid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT economy_garage.slotid, economy_garage.userid, economy_truck.vehicleid, economy_truck.userid, economy_garage.purchase_timestamp, economy_garage.note FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid >= 0 AND economy_garage.garageid = '{garageid}' \
                         ORDER BY economy_garage.purchase_timestamp {order} LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"slotid": tt[0], "slot_owner": await GetUserInfo(request, userid = tt[1]), "purchase_timestamp": tt[4], "note": tt[5], "truck": await GetTruckInfo(request, tt[2]), "truck_owner": await GetUserInfo(request, userid = tt[3])})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_garage_slot(request: Request, response: Response, garageid: str, slotid: int, authorization: str = Header(None)):
    '''Get info of a specific garage slot.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'GET /economy/garages/slots/slotid', 60, 60)
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

    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT economy_garage.slotid, economy_garage.userid, economy_truck.vehicleid, economy_truck.userid, economy_garage.purchase_timestamp, economy_garage.note FROM economy_garage \
                         LEFT JOIN economy_truck ON economy_truck.slotid = economy_garage.slotid \
                         WHERE economy_garage.slotid = {slotid} AND economy_garage.garageid = '{garageid}'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    tt = t[0]

    return {"slotid": tt[0], "slot_owner": await GetUserInfo(request, userid = tt[1]), "purchase_timestamp": tt[4], "note": tt[5], "truck": await GetTruckInfo(request, tt[2]), "truck_owner": await GetUserInfo(request, userid = tt[3])}

async def post_garage_purchase(request: Request, response: Response, garageid: str, authorization: str = Header(None)):
    '''Purchase a garage, returns `slotids`, `cost`, `balance`.

    JSON: `{"owner": Optional[str]}`

    `owner` can be `self` | `company` | `user-{userid}`

    [NOTE] The garage must not have been purchased before, aka there must be no slots connected to the garage. Otherwise it should be /{garageid}/slots/purchase.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/purchase', 60, 30)
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

    data = await request.json()
    try:
        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if garageid not in app.garages.keys():
        response.status_code = 404
        return {"error": ml.tr(request, "garage_not_found", force_lang = au["language"])}
    garage = app.garages[garageid]
    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT COUNT(slotid) FROM economy_garage WHERE garageid = '{garageid}'")
    slotcnt = nint(await app.db.fetchone(dhrid))
    if slotcnt > 0:
        response.status_code = 409
        return {"error": ml.tr(request, "garage_already_purchased", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # check access
    if not app.config.economy.allow_purchase_garage and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_forbidden", var = {"item": ml.tr(request, "garage", force_lang = au["language"])}, force_lang = au["language"])}
    if owner == "company" and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_company_forbidden", var = {"item": ml.tr(request, "garage", force_lang = au["language"])}, force_lang = au["language"])}

    # check owner
    if owner == "self":
        foruser = userid
        opuserid = userid
    elif owner == "company":
        foruser = -1000
        opuserid = -1000
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

    if garage["price"] > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    slotids = []
    ts = int(time.time())
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {garage['price']} WHERE userid = {opuserid}")
    for i in range(garage["base_slots"]):
        p = garage['price'] if i == 0 else 0
        await app.db.execute(dhrid, f"INSERT INTO economy_garage(garageid, userid, price, note, purchase_timestamp) VALUES ('{garageid}', {foruser}, {p}, 'garage-owner', {ts})")
        await app.db.commit(dhrid)
        await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
        slotid = (await app.db.fetchone(dhrid))[0]
        slotids.append(slotid)
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({opuserid}, -1002, {garage['price']}, 'g-{garageid}-purchase', 'for-user-{foruser}', {round(balance - garage['price'])}, NULL, {ts})")
    await app.db.commit(dhrid)

    return {"slotids": slotids, "cost": garage['price'], "balance": round(balance - garage['price'])}

async def post_garage_slot_purchase(request: Request, response: Response, garageid: str, authorization: str = Header(None)):
    '''Purchase a slot of a garage, returns `slotid`, `cost`, `balance`.

    JSON: `{"owner": Optional[str]}`

    `owner` can be `self` | `company` | `user-{userid}`

    [NOTE] The garage must have been purchased before, aka there must be slots connected to the garage. Otherwise it should be /{garageid}/purchase.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/slots/purchase', 60, 30)
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

    data = await request.json()
    try:
        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    if garageid not in app.garages.keys():
        response.status_code = 404
        return {"error": ml.tr(request, "garage_not_found", force_lang = au["language"])}
    garage = app.garages[garageid]
    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT COUNT(slotid) FROM economy_garage WHERE garageid = '{garageid}'")
    slotcnt = nint(await app.db.fetchone(dhrid))
    if slotcnt == 0:
        response.status_code = 409
        return {"error": ml.tr(request, "garage_not_purchased_before_purchase_slots", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # check access
    if not app.config.economy.allow_purchase_slot and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_forbidden", var = {"item": ml.tr(request, "garage_slot", force_lang = au["language"])}, force_lang = au["language"])}
    if owner == "company" and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_company_forbidden", var = {"item": ml.tr(request, "garage_slot", force_lang = au["language"])}, force_lang = au["language"])}

    # check owner
    if owner == "self":
        foruser = userid
        opuserid = userid
    elif owner == "company":
        foruser = -1000
        opuserid = -1000
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

    if garage["slot_price"] > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {garage['slot_price']} WHERE userid = {opuserid}")
    await app.db.execute(dhrid, f"INSERT INTO economy_garage(garageid, userid, price, note, purchase_timestamp) VALUES ('{garageid}', {foruser}, {garage['slot_price']}, 'slot-owner', {int(time.time())})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    slotid = (await app.db.fetchone(dhrid))[0]
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({opuserid}, -1002, {garage['slot_price']}, 'gs{slotid}-purchase', 'for-user-{foruser}', {round(balance - garage['slot_price'])}, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    return {"slotid": slotid, "cost": garage['slot_price'], "balance": round(balance - garage['slot_price'])}

async def post_garage_transfer(request: Request, response: Response, garageid: str, authorization: str = Header(None)):
    '''Transfer a garage (ownership).

    JSON: `{"owner": Optional[str], "message": Optional[str]}`

    `owner` can be `self` | `company` | `user-{userid}`

    [NOTE] This will transfer the garage ownership and the base slots when purchased.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/transfer', 60, 30)
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

    garageid = convertQuotation(garageid)

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
    elif owner == "company":
        foruser = -1000
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

    await app.db.execute(dhrid, f"SELECT userid FROM economy_garage WHERE garageid = '{garageid}' AND note = 'garage-owner'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "garage_not_purchased", force_lang = au["language"])}
    current_owner = t[0][0]
    if current_owner == foruser:
        response.status_code = 409
        return {"error": ml.tr(request, "new_owner_conflict", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # company garage but not manager or not owned garage
    # manager can transfer anyone's garage
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "garage", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_garage SET userid = {foruser} WHERE garageid = '{garageid}' AND note = 'garage-owner'")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_owner}, {foruser}, NULL, 'g-{garageid}-transfer', '{convertQuotation(message)}', NULL, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    garage = ml.ctr(request, "unknown_garage")
    if garageid in app.garages.keys():
        garage = app.garages[garageid]["name"]
    username = (await GetUserInfo(request, userid = foruser))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "transferred_garage", var = {"garage": garage, "id": garageid, "username": username, "userid": foruser}))

    from_user = await GetUserInfo(request, userid = current_owner)
    to_user = await GetUserInfo(request, userid = foruser)
    from_user_language = await GetUserLanguage(request, from_user["uid"])
    to_user_language = await GetUserLanguage(request, to_user["uid"])

    from_message = ""
    to_message = ""
    if message != "":
        from_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = from_user_language)
        to_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = to_user_language)

    garage = ml.ctr(request, "unknown") + " (" + garageid + ")"
    if garageid in app.garages.keys():
        garage = app.garages[garageid]["name"]

    await notification(request, "economy", from_user["uid"], ml.tr(request, "economy_sent_transaction_item", var = {"type": ml.tr(request, "garage", force_lang = from_user_language).title(), "name": garage, "to_user": to_user["name"], "to_userid": to_user["userid"] if to_user["userid"] is not None else "N/A", "message": from_message}, force_lang = from_user_language))
    await notification(request, "economy", to_user["uid"], ml.tr(request, "economy_received_transaction_item", var = {"type": ml.tr(request, "garage", force_lang = from_user_language).title(), "name": garage, "from_user": from_user["name"], "from_userid": from_user["userid"] if from_user["userid"] is not None else "N/A", "message": to_message}, force_lang = to_user_language))

    return Response(status_code=204)

async def post_garage_slot_transfer(request: Request, response: Response, garageid: str, slotid: int, authorization: str = Header(None)):
    '''Transfer a garage (ownership).

    JSON: `{"owner": Optional[str], "message": Optional[str]}`

    `owner` can be `self` | `company` | `user-{userid}`

    [NOTE] This will transfer the slot ownership.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/slots/transfer', 60, 30)
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

    garageid = convertQuotation(garageid)

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
    elif owner == "company":
        foruser = -1000
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

    await app.db.execute(dhrid, f"SELECT userid FROM economy_garage WHERE slotid = {slotid} AND garageid = '{garageid}'")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    if current_owner != -1000 and current_owner == foruser:
        response.status_code = 409
        return {"error": ml.tr(request, "new_owner_conflict", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # company garage but not manager or not owned garage
    # manager can transfer anyone's garage
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "garage_slot", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_garage SET userid = {foruser} WHERE slotid = {slotid} AND garageid = '{garageid}'")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_owner}, {foruser}, NULL, 'gs{slotid}-transfer', '{convertQuotation(message)}', NULL, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    username = (await GetUserInfo(request, userid = foruser))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "transferred_slot", var = {"id": slotid, "username": username, "userid": foruser}))

    from_user = await GetUserInfo(request, userid = current_owner)
    to_user = await GetUserInfo(request, userid = foruser)
    from_user_language = await GetUserLanguage(request, from_user["uid"])
    to_user_language = await GetUserLanguage(request, to_user["uid"])

    from_message = ""
    to_message = ""
    if message != "":
        from_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = from_user_language)
        to_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = to_user_language)

    garage = ml.ctr(request, "unknown") + " (" + garageid + ")"
    if garageid in app.garages.keys():
        garage = app.garages[garageid]["name"]

    await notification(request, "economy", from_user["uid"], ml.tr(request, "economy_sent_transaction_item", var = {"type": ml.tr(request, "garage_slot", force_lang = from_user_language).title(), "name": f"#{slotid} ({garage})", "to_user": to_user["name"], "to_userid": to_user["userid"] if to_user["userid"] is not None else "N/A", "message": from_message}, force_lang = from_user_language))
    await notification(request, "economy", to_user["uid"], ml.tr(request, "economy_received_transaction_item", var = {"type": ml.tr(request, "garage_slot", force_lang = from_user_language).title(), "name": f"#{slotid} ({garage})", "from_user": from_user["name"], "from_userid": from_user["userid"] if from_user["userid"] is not None else "N/A", "message": to_message}, force_lang = to_user_language))

    return Response(status_code=204)

async def post_garage_sell(request: Request, response: Response, garageid: str, authorization: str = Header(None)):
    '''Sell a garage (ownership), returns `refund`, `balance`.

    [NOTE] There must be no slots under the garage and no trucks parked in the base slots.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/sell', 60, 30)
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

    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT userid, price FROM economy_garage WHERE garageid = '{garageid}' AND note = 'garage-owner' AND price != 0") # only the first slot contains a price info
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 428
        return {"error": ml.tr(request, "garage_not_purchased", force_lang = au["language"])}
    current_owner = t[0][0]
    price = t[0][1]
    refund = price * app.config.economy.garage_refund

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # company garage but not manager or not owned garage
    # manager can transfer anyone's garage
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "garage", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT COUNT(slotid) FROM economy_garage WHERE garageid = '{garageid}' AND note != 'garage-owner'")
    t = nint(await app.db.fetchone(dhrid))
    if t != 0:
        response.status_code = 428
        return {"error": ml.tr(request, "garage_has_slots", force_lang = au["language"])}
    await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE garageid = '{garageid}'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 428
        return {"error": ml.tr(request, "garage_has_truck", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM economy_garage WHERE garageid = '{garageid}'")
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, current_owner) if balance == 0 else None
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1002, {current_owner}, {refund}, 'g-{garageid}-sell', 'refund-{app.config.economy.garage_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await app.db.commit(dhrid)

    garage = ml.ctr(request, "unknown_garage")
    if garageid in app.garages.keys():
        garage = app.garages[garageid]["name"]
    username = (await GetUserInfo(request, userid = current_owner))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "sold_garage", var = {"garage": garage, "id": garageid, "username": username, "userid": current_owner}))

    return {"refund": refund, "balance": round(balance + refund)}

async def post_garage_slot_sell(request: Request, response: Response, garageid: str, slotid: int, authorization: str = Header(None)):
    '''Sell a garage (ownership), returns `refund`, `balance`.

    [NOTE] There must be no slots under the garage and no trucks parked in the base slots.'''
    app = request.app
    dhrid = request.state.dhrid
    rl = await ratelimit(request, 'POST /economy/garages/slots/sell', 60, 30)
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

    garageid = convertQuotation(garageid)

    await app.db.execute(dhrid, f"SELECT userid, price, note FROM economy_garage WHERE slotid = {slotid} AND garageid = '{garageid}'") # only the first slot contains a price info
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    price = t[0][1]
    refund = price * app.config.economy.slot_refund
    note = t[0][2]
    if note == "garage-owner":
        response.status_code = 403
        return {"error": ml.tr(request, "garage_slot_is_base_slot", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["administrator", "manage_economy", "manage_economy_garage"])

    # company garage but not manager or not owned garage
    # manager can transfer anyone's garage
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "garage", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE slotid = {slotid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 428
        return {"error": ml.tr(request, "garage_slot_has_truck", force_lang = au["language"])}

    await app.db.execute(dhrid, f"DELETE FROM economy_garage WHERE slotid = {slotid}")
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, current_owner) if balance == 0 else None
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1002, {current_owner}, {refund}, 'gs{slotid}-sell', 'refund-{app.config.economy.slot_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await app.db.commit(dhrid)

    username = (await GetUserInfo(request, userid = current_owner))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "sold_slot", var = {"id": slotid, "username": username, "userid": current_owner}))

    return {"refund": refund, "balance": round(balance + refund)}
