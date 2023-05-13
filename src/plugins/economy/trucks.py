# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from functions import *

async def GetTruckInfo(request, vehicleid):
    (app, dhrid) = (request.app, request.state.dhrid)
    await app.db.execute(dhrid, f"SELECT vehicleid, truckid, garageid, slotid, userid, price, odometer, damage, purchase_timestamp, status, income, service_cost, assigneeid FROM economy_truck WHERE vehicleid >= 0 AND userid >= -1000 AND vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return None
    tt = t[0]

    STATUS = {0: "inactive", 1: "active", -1: "require_service", -2: "scrapped"}

    truck = {"id": tt[1], "brand": None, "model": None}
    if tt[1] in app.trucks.keys():
        (truck["brand"], truck["model"]) = (app.trucks[tt[1]]["brand"], app.trucks[tt[1]]["model"])

    return {"vehicleid": tt[0], "truck": truck, "garageid": tt[2], "slotid": tt[3], "owner": await GetUserInfo(request, userid = tt[4]), "assignee": await GetUserInfo(request, userid = tt[12]), "price": tt[5], "income": tt[10], "service": tt[11], "odometer": tt[6], "damage": tt[7], "repair_cost": round(tt[7] * 100 * app.config.economy.unit_service_price), "purchase_timestamp": tt[8], "status": STATUS[tt[9]]}

async def get_all_trucks(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/trucks', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    return app.config.economy.trucks

async def get_truck_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_vehicleid: Optional[int] = None, \
        truckid: Optional[str] = "", garageid: Optional[str] = "",\
        owner: Optional[int] = None, min_price: Optional[int] = None, max_price: Optional[int] = None, \
        purchased_after: Optional[int] = None, purchased_before: Optional[int] = None, \
        min_income: Optional[int] = None, max_income: Optional[int] = None,
        min_odometer: Optional[int] = None, max_odometer: Optional[int] = None,
        min_damage: Optional[float] = None, max_damage: Optional[float] = None,
        order_by: Optional[str] = "odometer", order: Optional[str] = "desc"):
    '''Get a list of owned trucks.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/trucks/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(request, au["uid"], "economy_trucks")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    limit = ""
    if truckid != "":
        truckid = convertQuotation(truckid).lower()
        limit += f"AND LOWER(truckid) LIKE '%{truckid[:200]}%' "

    if garageid != "":
        garageid = convertQuotation(garageid).lower()
        limit += f"AND LOWER(garageid) LIKE '%{garageid[:200]}%' "

    if owner is not None:
        limit += f"AND userid = {owner} "

    if min_price is not None:
        limit += f"AND price >= {min_price} "
    if max_price is not None:
        limit += f"AND price <= {max_price} "

    if purchased_after is not None:
        limit += f"AND purchase_timestamp >= {purchased_after} "
    if purchased_before is not None:
        limit += f"AND purchase_timestamp <= {purchased_before} "

    if min_income is not None:
        limit += f"AND income >= {min_income} "
    if max_income is not None:
        limit += f"AND income <= {max_income} "

    if min_odometer is not None:
        limit += f"AND odometer >= {min_odometer} "
    if max_odometer is not None:
        limit += f"AND odometer <= {max_odometer} "

    if min_damage is not None:
        limit += f"AND damage >= {min_damage} "
    if max_damage is not None:
        limit += f"AND damage <= {max_damage} "

    if order_by not in ["vehicleid", "userid", "truckid", "slotid", "garageid", "price", "odometer", "damage", "purchase_timestamp"]:
        order_by = "odometer"
        order = "desc"

    if order not in ["asc", "desc"]:
        order = "asc"

    STATUS = {0: "inactive", 1: "active", -1: "require_service", -2: "scrapped"}

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE vehicleid >= 0 AND userid >= -1000 {limit} ORDER BY {order_by} {order}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_vehicleid is not None:
        for tt in t:
            if tt[0] == after_vehicleid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT vehicleid, truckid, garageid, slotid, userid, price, odometer, damage, purchase_timestamp, status, income, service_cost, assigneeid FROM economy_truck WHERE vehicleid >= 0 AND userid >= -1000 {limit} ORDER BY {order_by} {order} LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        truck = {"id": tt[1], "brand": None, "model": None}
        if tt[1] in app.trucks.keys():
            (truck["brand"], truck["model"]) = (app.trucks[tt[1]]["brand"], app.trucks[tt[1]]["model"])
        ret.append({"vehicleid": tt[0], "truck": truck, "garageid": tt[2], "slotid": tt[3], "owner": await GetUserInfo(request, userid = tt[4]), "assignee": await GetUserInfo(request, userid = tt[12]), "price": tt[5], "income": tt[10], "service": tt[11], "odometer": tt[6], "damage": tt[7], "repair_cost": round(tt[7] * 100 * app.config.economy.unit_service_price),"purchase_timestamp": tt[8], "status": STATUS[tt[9]]})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_truck(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Get info of a specific truck'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/trucks/vehicleid', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT vehicleid, truckid, garageid, slotid, userid, price, odometer, damage, purchase_timestamp, status, income, service_cost, assigneeid FROM economy_truck WHERE vehicleid >= 0 AND userid >= -1000 AND vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    tt = t[0]

    await ActivityUpdate(request, au["uid"], f"economy_trucks_{vehicleid}")

    STATUS = {0: "inactive", 1: "active", -1: "require_service", -2: "scrapped"}

    truck = {"id": tt[1], "brand": None, "model": None}
    if tt[1] in app.trucks.keys():
        (truck["brand"], truck["model"]) = (app.trucks[tt[1]]["brand"], app.trucks[tt[1]]["model"])

    return {"vehicleid": tt[0], "truck": truck, "garageid": tt[2], "slotid": tt[3], "owner": await GetUserInfo(request, userid = tt[4]), "assignee": await GetUserInfo(request, userid = tt[12]), "price": tt[5], "income": tt[10], "service": tt[11], "odometer": tt[6], "damage": tt[7], "repair_cost": round(tt[7] * 100 * app.config.economy.unit_service_price), "purchase_timestamp": tt[8], "status": STATUS[tt[9]]}

async def get_truck_operation_history(request: Request, response: Response, vehicleid: int, operation: str, authorization: str = Header(None), page: Optional[int] = 1, page_size: Optional[int] = 10, after_txid: Optional[int] = None, after: Optional[int] = None, before: Optional[int] = None, order: Optional[str] = "desc"):
    '''Get the transaction history of a specific truck.

    `order_by` is `timestamp`.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/trucks/operation/history', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await app.db.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid >= 0 AND vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    ownerid = t[0][0]

    if ownerid != au["userid"] and not checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"]):
        response.status_code = 403
        return {"error": ml.tr(request, "truck_history_forbidden", force_lang = au["language"])}

    await ActivityUpdate(request, au["uid"], f"economy_trucks_{vehicleid}")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if order not in ["asc", "desc"]:
        order = "asc"

    if operation == "all":
        query = f"LIKE 't{vehicleid}-%'"
    elif operation == "dlog":
        query = f"= 't{vehicleid}-income'"
    elif operation == "service":
        query = f"= 't{vehicleid}-service'"
    elif operation == "transfer":
        query = f"= 't{vehicleid}-transfer'"
    elif operation == "reassign":
        query = f"= 't{vehicleid}-reassign'"
    elif operation == "purchase":
        query = f"= 't{vehicleid}-purchase'"
    elif operation == "sell":
        query = f"= 't{vehicleid}-sell'"
    elif operation == "scrap":
        query = f"= 't{vehicleid}-scrap'"
    else:
        response.status_code = 404
        return {"error": "Not Found"}

    if after is not None:
        query += f" AND timestamp >= {after} "
    if before is not None:
        query += f" AND timestamp <= {before} "
    if after_txid is not None:
        if order == "asc":
            query += f" AND txid >= {after_txid} "
        elif order == "desc":
            query += f" AND txid <= {after_txid} "

    await app.db.execute(dhrid, f"SELECT txid, from_userid, to_userid, amount, note, message, timestamp FROM economy_transaction WHERE note {query} ORDER BY timestamp {order} LIMIT {max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        if tt[4] == f"t{vehicleid}-income":
            # NOTE the t%-income's "amount" is the income for the driver
            # To get the income for the company, use ct%-income
            # The "amount" of t%-income shouldn't be publicly visible and only for internal use
            # Show the revenue in message to public

            # to_user => tx receiver / user that income is sent to
            # message: dlog-{logid}/garage-{garageid}-{slotid}/revenue-{real_revenue}
            p = tt[5].split("/")
            logid = int(p[0].split("-")[1])
            revenue = int(p[2].split("-")[1])
            ret.append({"type": "dlog", "txid": tt[0], "user": await GetUserInfo(request, userid = tt[2]), "amount": revenue, "logid": logid, "timestamp": tt[6]})
        elif tt[4] == f"t{vehicleid}-service":
            # from_user => tx sender / user that requested service
            ret.append({"type": "service", "txid": tt[0], "user": await GetUserInfo(request, userid = tt[1]), "amount": tt[3], "damage": float(tt[5].split("-")[1]), "timestamp": tt[6]}) # message: damage-{damage}
        elif tt[4] == f"t{vehicleid}-transfer":
            ret.append({"type": "service", "txid": tt[0], "from_user": await GetUserInfo(request, userid = tt[1]), "to_user": await GetUserInfo(request, userid = tt[2]), "message": tt[5], "timestamp": tt[6]}) # message: real transfer message
        elif tt[4] == f"t{vehicleid}-reassign":
            ret.append({"type": "service", "txid": tt[0], "from_user": await GetUserInfo(request, userid = tt[1]), "to_user": await GetUserInfo(request, userid = tt[2]), "staff": await GetUserInfo(request, userid = int(tt[5].split("-")[1])), "timestamp": tt[6]}) # message: staff-{userid}
        elif tt[4] == f"t{vehicleid}-purchase":
            # from_user => tx sender / user who transferred money to dealership
            ret.append({"type": "purchase", "txid": tt[0], "user": await GetUserInfo(request, userid = tt[1]), "amount": tt[3], "timestamp": tt[6]})
        elif tt[4] == f"t{vehicleid}-sell":
            # to_user => tx receiver / user who got the refund from dealership
            p = tt[5].split("/")
            damage = float(p[0].split("-")[1])
            odometer = int(p[1].split("-")[1])
            ret.append({"type": "sell", "txid": tt[0], "user": await GetUserInfo(request, userid = tt[2]), "amount": tt[3], "damage": damage, "odometer": odometer, "timestamp": tt[6]})
        elif tt[4] == f"t{vehicleid}-scrap":
            # to_user => tx receiver / user who got a tiny refund from scrap station
            # message: damage-{damage}/odometer-{odometer}/refund-{refund}
            p = tt[5].split("/")
            damage = float(p[0].split("-")[1])
            odometer = int(p[1].split("-")[1])
            ret.append({"type": "scrap", "txid": tt[0], "user": await GetUserInfo(request, userid = tt[2]), "amount": tt[3], "damage": damage, "odometer": odometer, "timestamp": tt[6]})

    await app.db.execute(dhrid, f"SELECT COUNT(*) FROM economy_transaction WHERE note {query}")
    t = await app.db.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def post_truck_purchase(request: Request, response: Response, truckid: str, authorization: str = Header(None), owner: Optional[str] = "self"):
    '''Purchase a truck, returns `vehicleid`, `cost`, `balance`.

    JSON: `{"owner": Optional[str], "slotid": int, "assignee": Optional[int]}`

    `owner` can be `self` | `company` | `user-{userid}`

    `assignee` is only required when `owner = company`

    [NOTE] If the owner / assignee already has a truck of the same model, the purchased truck will be deactivated to prevent conflict on job submission.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/purchase', 60, 30)
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
    try:
        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"
        slotid = int(data["slotid"])

        # assignee only work for company trucks
        assigneeid = "NULL"
        if "assigneeid" in data.keys():
            assigneeid = data["assigneeid"]
            if assigneeid is None:
                assigneeid = "NULL"
            else:
                assigneeid = int(assigneeid)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # check access
    if not app.config.economy.allow_purchase_truck and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}
    if owner == "company" and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_company_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check truckid
    if truckid not in app.trucks.keys():
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truck = app.trucks[truckid]
    truckid = convertQuotation(truckid)

    # check owner
    if owner == "self":
        foruser = userid
        opuserid = userid
        assigneeid = userid
    elif owner == "company":
        foruser = -1000
        opuserid = -1000
    elif owner.startswith("user-"):
        foruser = owner.split("-")[1]
        opuserid = userid
        assigneeid = foruser
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

    # check garage slot (existence)
    await app.db.execute(dhrid, f"SELECT garageid FROM economy_garage WHERE slotid = {slotid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    garageid = t[0][0]

    # check garage slot (occupied)
    await app.db.execute(dhrid, f"SELECT slotid FROM economy_truck WHERE slotid = {slotid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_occupied", force_lang = au["language"])}

    # check truck model conflict
    model_conflict = False
    if foruser != -1000:
        await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {foruser} OR assigneeid = {foruser}) AND status = 1 AND truckid = '{truckid}'")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    elif assigneeid != "NULL":
        await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {assigneeid} OR assigneeid = {assigneeid}) AND status = 1 AND truckid = '{truckid}'")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    status = not model_conflict

    # check balance
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {opuserid} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, opuserid) if balance == 0 else None

    if truck["price"] > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {truck['price']} WHERE userid = {opuserid}")
    await app.db.execute(dhrid, f"INSERT INTO economy_truck(truckid, garageid, slotid, userid, assigneeid, price, income, service_cost, odometer, damage, purchase_timestamp, status) VALUES ('{truckid}', '{garageid}', {slotid}, {foruser}, {assigneeid}, {truck['price']}, 0, 0, 0, 0, {int(time.time())}, {status})")
    await app.db.commit(dhrid)
    await app.db.execute(dhrid, "SELECT LAST_INSERT_ID();")
    vehicleid = (await app.db.fetchone(dhrid))[0]
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({opuserid}, -1001, {truck['price']}, 't{vehicleid}-purchase', 'for-user-{foruser}', {round(balance - truck['price'])}, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    username = (await GetUserInfo(request, userid = foruser))["name"]
    await AuditLog(request, au["uid"], ml.ctr(request, "purchased_truck", var = {"name": truck["brand"] + " " + truck["model"], "id": truckid, "username": username, "userid": foruser}))

    return {"vehicleid": vehicleid, "cost": truck["price"], "balance": round(balance - truck["price"])}

async def post_truck_transfer(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Transfer / Reassign a truck, returns 204.

    JSON: `{"owner": Optional[str], "assignee": Optional[int], "message": Optional[str]}`

    `owner` can be `self` | `company` | `user-{userid}`

    `assignee` is only required when `owner = company`

    [NOTE] If the new owner / assignee already has a truck of the same model, the transferred truck will be deactivated to prevent conflict on job submission.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/transfer', 60, 30)
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
    try:
        # to reassign a truck, set owner to company and update assigneeid

        if "owner" in data.keys():
            owner = data["owner"] # owner = self | company | user-{userid}
        else:
            owner = "self"

        # assignee only work for company trucks
        assigneeid = "NULL"
        if "assigneeid" in data.keys():
            assigneeid = data["assigneeid"]
            if assigneeid is None:
                assigneeid = "NULL"
            else:
                assigneeid = int(assigneeid)

        if "message" in data.keys():
            message = convertQuotation(data["message"])
        else:
            message = ""
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    # check new owner
    if owner == "self":
        # company => me
        foruser = userid
        assigneeid = userid
    elif owner == "company":
        # me => company
        foruser = -1000
    elif owner.startswith("user-"):
        # me/company => another user
        foruser = owner.split("-")[1]
        assigneeid = foruser
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT truckid, userid, assigneeid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assigneeid = t[0][2]
    if current_owner != -1000 and current_owner == foruser:
        response.status_code = 409
        return {"error": ml.tr(request, "new_owner_conflict", force_lang = au["language"])}

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can transfer anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check truck model conflict
    model_conflict = False
    if foruser != -1000:
        await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {foruser} OR assigneeid = {foruser}) AND status = 1 AND truckid = '{truckid}'")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    elif assigneeid != "NULL":
        await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {assigneeid} OR assigneeid = {assigneeid}) AND status = 1 AND truckid = '{truckid}'")
        t = await app.db.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    status = not model_conflict

    await app.db.execute(dhrid, f"UPDATE economy_truck SET userid = {foruser}, assigneeid = {assigneeid}, status = {status} WHERE vehicleid = {vehicleid}")
    await app.db.commit(dhrid)

    if current_owner != foruser:
        await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_owner}, {foruser}, NULL, 't{vehicleid}-transfer', '{message}', NULL, NULL, {int(time.time())})")

        username = (await GetUserInfo(request, userid = foruser))["name"]
        await AuditLog(request, au["uid"], ml.ctr(request, "transferred_truck", var = {"id": vehicleid, "username": username, "userid": foruser}))
    if current_assigneeid != assigneeid:
        if current_assigneeid is None:
            current_assigneeid = "NULL"
        await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_assigneeid}, {assigneeid}, NULL, 't{vehicleid}-reassign', 'staff-{userid}', NULL, NULL, {int(time.time())})")

        if assigneeid != "NULL":
            username = (await GetUserInfo(request, userid = assigneeid))["name"]
            await AuditLog(request, au["uid"], ml.ctr(request, "reassigned_truck", var = {"id": vehicleid, "username": username, "userid": foruser}))
        else:
            await AuditLog(request, au["uid"], ml.ctr(request, "removed_truck_assignee", var = {"id": vehicleid}))

    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_truck_relocate(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Transfer / Reassign a truck, returns 204.

    JSON: `{"slotid": int"}`'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/relocate', 60, 30)
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
    try:
        slotid = int(data["slotid"])
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}

    # check current owner
    await app.db.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check garage slot (existence)
    await app.db.execute(dhrid, f"SELECT garageid FROM economy_garage WHERE slotid = {slotid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    garageid = t[0][0]

    # check garage slot (occupied)
    await app.db.execute(dhrid, f"SELECT slotid FROM economy_truck WHERE slotid = {slotid}")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_occupied", force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_truck SET garageid = '{convertQuotation(garageid)}', slotid = {slotid} WHERE vehicleid = {vehicleid}")
    await app.db.commit(dhrid)

    garage = ml.ctr(request, "unknown_garage")
    if garage in app.garages.keys():
        garage = app.garages[garage]["name"]

    await AuditLog(request, au["uid"], ml.ctr(request, "relocated_truck", var = {"id": vehicleid, "garage": garage, "garageid": garageid, "slotid": slotid}))

    return Response(status_code=204)

async def post_truck_activate(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Activate a truck, returns 204.

    [NOTE] If the owner / assignee has multiple trucks of the same model, other trucks of the same model will be deactivated.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/activate', 60, 30)
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT truckid, userid, assigneeid, status FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assigneeid = t[0][2]
    status = t[0][3]

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    if status == -1:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_repair_required", force_lang = au["language"])}
    if status == -2:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_scrap_required", force_lang = au["language"])}

    # check truck model conflict
    if current_owner != -1000:
        await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE (userid = {current_owner} OR assigneeid = {current_owner}) AND truckid = '{truckid}'")
    elif current_assigneeid is not None:
        await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE (userid = {current_assigneeid} OR assigneeid = {current_assigneeid}) AND truckid = '{truckid}'")
    await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 1 WHERE vehicleid = {vehicleid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_truck_deactivate(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Deactivate a truck, returns 204.

    [NOTE] If there's no status truck of a model, new jobs of that model will be charged a rental cost.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/deactivate', 60, 30)
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE vehicleid = {vehicleid}")
    await app.db.commit(dhrid)

    return Response(status_code=204)

async def post_truck_repair(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Repair a truck, returns `cost`, `balance`.

    [NOTE] If the truck's damage > app.config.economy.max_wear_before_service, new jobs will be charged a rental cost. Once the issue is noticed, status state of the truck will be modified to -1. If the truck's state is -1 and a repair is performed, it will be reactivated automatically if there's no other status trucks.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/repair', 60, 30)
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT truckid, userid, assigneeid, damage, status FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assignee = t[0][2]
    damage = t[0][3]
    status = t[0][4]

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check balance
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, userid) if balance == 0 else None

    cost = round(damage * 100 * app.config.economy.unit_service_price)
    if cost > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    if cost == 0:
        return {"cost": cost, "balance": round(balance - cost)}

    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {cost} WHERE userid = {userid}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({userid}, -1004, {cost}, 't{vehicleid}-service', 'damage-{damage}', {round(balance - cost)}, NULL, {int(time.time())})")
    await app.db.commit(dhrid)

    await app.db.execute(dhrid, f"UPDATE economy_truck SET damage = 0, service_cost = service_cost + {cost} WHERE vehicleid = {vehicleid}")
    if status == -1:
        model_conflict = False
        if current_owner != -1000:
            await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {current_owner} OR assigneeid = {current_owner}) AND status = 1 AND truckid = '{truckid}'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                model_conflict = True
        elif current_assignee != "NULL":
            await app.db.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE (userid = {current_assignee} OR assigneeid = {current_assignee}) AND status = 1 AND truckid = '{truckid}'")
            t = await app.db.fetchall(dhrid)
            if len(t) != 0:
                model_conflict = True
        if not model_conflict:
            await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 1 WHERE vehicleid = {vehicleid}")
        else:
            await app.db.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE vehicleid = {vehicleid}")
    await app.db.commit(dhrid)

    return {"cost": cost, "balance": round(balance - cost)}

async def post_truck_sell(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Sell a truck, returns `refund`, `balance`.

    [Note] refund = price * (1 - damage) * app.config.economy.truck_refund (ratio)'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/sell', 60, 30)
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT userid, odometer, damage, price FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    odometer = t[0][1]
    damage = t[0][2]
    price = t[0][3]
    refund = round(price * (1 - damage) * app.config.economy.truck_refund)

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check balance
    await app.db.execute(dhrid, f"UPDATE economy_truck SET userid = -1001, status = 0, slotid = NULL, garageid = NULL WHERE vehicleid = {vehicleid}")
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, current_owner) if balance == 0 else None
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1001, {current_owner}, {refund}, 't{vehicleid}-sell', 'damage-{damage}/odometer-{odometer}/refund-{app.config.economy.truck_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await app.db.commit(dhrid)

    return {"refund": refund, "balance": round(balance + refund)}

async def post_truck_scrap(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Scrap a truck, returns `refund`, `balance`.

    [Note] refund = price * app.config.economy.scrap_refund (ratio)'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/trucks/scrap', 60, 30)
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

    # check current owner
    await app.db.execute(dhrid, f"SELECT userid, odometer, damage, price FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    odometer = t[0][1]
    damage = t[0][2]
    price = t[0][3]
    refund = round(price * app.config.economy.scrap_refund)

    if current_owner in [-1001, -1005]:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    # check perm
    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "economy_truck", force_lang = au["language"])}, force_lang = au["language"])}

    if odometer < 0.9 * app.config.economy.max_distance_before_scrap:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_scrap_unncessary", force_lang = au["language"])}

    # check balance
    await app.db.execute(dhrid, f"UPDATE economy_truck SET userid = -1005, status = 0, status = 0, slotid = NULL, garageid = NULL WHERE vehicleid = {vehicleid}")
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, current_owner) if balance == 0 else None
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1005, {current_owner}, {refund}, 't{vehicleid}-scrap', 'damage-{damage}/odometer-{odometer}/refund-{app.config.economy.truck_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await app.db.commit(dhrid)

    return {"refund": refund, "balance": round(balance + refund)}
