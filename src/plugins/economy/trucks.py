# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from typing import Optional

from fastapi import Header, Request, Response

import multilang as ml
from app import app, config
from db import aiosql
from functions import *


@app.get(f"/{config.abbr}/economy/trucks")
async def get_economy_trucks():
    return config.economy.trucks

@app.get(f"/{config.abbr}/economy/trucks/list")
async def get_economy_trucks_list(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, truckid: Optional[str] = "", garageid: Optional[str] = "",\
        owner: Optional[int] = None, min_price: Optional[int] = None, max_price: Optional[int] = None, \
        purchased_after: Optional[int] = None, purchased_before: Optional[int] = None, \
        min_income: Optional[int] = None, max_income: Optional[int] = None,
        min_odometer: Optional[int] = None, max_odometer: Optional[int] = None,
        min_damage: Optional[float] = None, max_damage: Optional[float] = None,
        order_by: Optional[str] = "odometer", order: Optional[int] = "desc"):
    '''Get a list of owned trucks.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /economy/trucks/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    await ActivityUpdate(dhrid, au["uid"], f"economy_trucks")

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

    if not order_by in ["vehicleid", "userid", "truckid", "slotid", "garageid", "price", "odometer", "damage", "purchase_timestamp"]:
        order_by = "odometer"
        order = "desc"
    
    if not order.lower() in ["asc", "desc"]:
        order = "asc"
    
    STATUS = {0: ml.tr(request, "inactive", force_lang=au["language"]), 1: ml.tr(request, "active", force_lang=au["language"]), -1: ml.tr(request, "service_required", force_lang=au["language"]), -2: ml.tr(request, "scrapped", force_lang=au["language"])}

    await aiosql.execute(dhrid, f"SELECT vehicleid, truckid, garageid, slotid, userid, price, odometer, damage, purchase_timestamp FROM economy_truck, status, income, service_cost WHERE vehicleid >= 0 AND userid >= 0 {limit} ORDER BY {order_by} {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
    ret = []
    for tt in t:
        ret.append({"vehicleid": tt[0], "truckid": tt[1], "garageid": tt[2], "slotid": tt[3], "owner": await GetUserInfo(dhrid, request, userid = tt[4]), "price": tt[5], "income": tt[10], "service": tt[11], "odometer": tt[6], "damage": tt[7], "repair_cost": round(tt[7] * 100 * config.economy.unit_service_price),"purchase_timestamp": tt[8], "status": STATUS[tt[9]]})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM economy_truck WHERE vehicleid >= 0 {limit}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.get(f"/{config.abbr}/economy/trucks/{{vehicleid}}")
async def get_economy_trucks_vehicle(request: Request, response: Response, vehicleid: int, authorization: str = Header(None)):
    '''Get info of a specific truck'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /economy/trucks/vehicleid', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await aiosql.execute(dhrid, f"SELECT vehicleid, truckid, garageid, slotid, userid, price, odometer, damage, purchase_timestamp, status, income, service_cost FROM economy_truck WHERE vehicleid >= 0 AND userid >= 0 AND vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    tt = t[0]

    await ActivityUpdate(dhrid, au["uid"], f"economy_trucks_{vehicleid}")

    STATUS = {0: ml.tr(request, "inactive", force_lang=au["language"]), 1: ml.tr(request, "active", force_lang=au["language"]), -1: ml.tr(request, "service_required", force_lang=au["language"]), -2: ml.tr(request, "scrapped", force_lang=au["language"])}
    
    return {"vehicleid": tt[0], "truckid": tt[1], "garageid": tt[2], "slotid": tt[3], "owner": await GetUserInfo(dhrid, request, userid = tt[4]), "price": tt[5], "income": tt[10], "service": tt[11], "odometer": tt[6], "damage": tt[7], "repair_cost": round(tt[7] * 100 * config.economy.unit_service_price), "purchase_timestamp": tt[8], "status": STATUS[tt[9]]}

@app.get(f"/{config.abbr}/economy/trucks/{{vehicleid}}/{{operation}}/history")
async def get_economy_trucks_operation_history(request: Request, response: Response, vehicleid: int, operation: str, authorization: str = Header(None), page: Optional[int] = 1, page_size: Optional[int] = 10, order: Optional[str] = "desc"):
    '''Get the transaction history of a specific truck.

    `order_by` is `timestamp`.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'GET /economy/trucks/vehicleid/operation/history', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    await aiosql.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid >= 0 AND vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    ownerid = t[0][0]

    if ownerid != au["userid"] and not checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"]):
        response.status_code = 403
        return {"error": ml.tr(request, "truck_history_forbidden", force_lang = au["language"])}

    await ActivityUpdate(dhrid, au["uid"], f"economy_trucks_{vehicleid}")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    if not order.lower() in ["asc", "desc"]:
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
    
    await aiosql.execute(dhrid, f"SELECT txid, from_userid, to_userid, amount, note, message, timestamp FROM economy_transaction WHERE note {query} ORDER BY timestamp {order} LIMIT {(page-1) * page_size}, {page_size}")
    t = await aiosql.fetchall(dhrid)
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
            ret.append({"type": "dlog", "txid": tt[0], "user": await GetUserInfo(dhrid, request, userid = tt[2]), "amount": revenue, "logid": logid, "timestamp": tt[6]}) 
        elif tt[4] == f"t{vehicleid}-service":
            # from_user => tx sender / user that requested service
            ret.append({"type": "service", "txid": tt[0], "user": await GetUserInfo(dhrid, request, userid = tt[1]), "amount": tt[3], "damage": float(tt[5].split("-")[1]), "timestamp": tt[6]}) # message: damage-{damage}
        elif tt[4] == f"t{vehicleid}-transfer":
            ret.append({"type": "service", "txid": tt[0], "from_user": await GetUserInfo(dhrid, request, userid = tt[1]), "to_user": await GetUserInfo(dhrid, request, userid = tt[2]), "message": tt[5], "timestamp": tt[6]}) # message: real transfer message
        elif tt[4] == f"t{vehicleid}-reassign":
            ret.append({"type": "service", "txid": tt[0], "from_user": await GetUserInfo(dhrid, request, userid = tt[1]), "to_user": await GetUserInfo(dhrid, request, userid = tt[2]), "staff": await GetUserInfo(dhrid, request, userid = int(tt[5].split("-")[1])), "timestamp": tt[6]}) # message: staff-{userid}
        elif tt[4] == f"t{vehicleid}-purchase":
            # from_user => tx sender / user who transferred money to dealership
            ret.append({"type": "purchase", "txid": tt[0], "user": await GetUserInfo(dhrid, request, userid = tt[1]), "amount": tt[3], "timestamp": tt[6]})
        elif tt[4] == f"t{vehicleid}-sell":
            # to_user => tx receiver / user who got the refund from dealership
            p = tt[5].split("/")
            damage = float(p[0].split("-")[1])
            odometer = int(p[1].split("-")[1])
            ret.append({"type": "sell", "txid": tt[0], "user": await GetUserInfo(dhrid, request, userid = tt[2]), "amount": tt[3], "damage": damage, "odometer": odometer, "timestamp": tt[6]})
        elif tt[4] == f"t{vehicleid}-scrap":
            # to_user => tx receiver / user who got a tiny refund from scrap station
            # message: damage-{damage}/odometer-{odometer}/refund-{refund}
            p = tt[5].split("/")
            damage = float(p[0].split("-")[1])
            odometer = int(p[1].split("-")[1])
            ret.append({"type": "scrap", "txid": tt[0], "user": await GetUserInfo(dhrid, request, userid = tt[2]), "amount": tt[3], "damage": damage, "odometer": odometer, "timestamp": tt[6]})
    
    await aiosql.execute(dhrid, f"SELECT COUNT(*) FROM economy_transaction WHERE note {query}")
    t = await aiosql.fetchall(dhrid)
    tot = 0
    if len(t) > 0:
        tot = t[0][0]

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

@app.post(f"/{config.abbr}/economy/trucks/{{truckid}}/purchase")
async def post_economy_trucks_purchase(request: Request, response: Response, truckid: str, authorization: str = Header(None), owner: Optional[str] = "self"):
    '''Purchase a truck, returns `vehicleid`, `cost`, `balance`.
    
    JSON: `{"owner": str, "slotid": int, "assignee": Optional[int]}`
    
    `owner` can be `self` | `company` | `user-{userid}`

    `assignee` is only required when `owner = company`
    
    [NOTE] If the owner / assignee already has a truck of the same model, the purchased truck will be deactivated to prevent conflict on job submission.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/truckid/purchase', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    
    truckid = convertQuotation(truckid)
    data = await request.json()
    try:
        owner = data["owner"] # owner = self | company | user-{userid}
        slotid = int(data["slotid"])

        # assignee only work for company trucks
        if "assignee" in data.keys():
            assigneeid = data["assignee"]
            if assigneeid is None:
                assigneeid = "NULL"
            else:
                assigneeid = int(assigneeid)
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    
    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # check access
    if not config.economy.allow_purchase_truck and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    if owner == "company" and not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "purchase_company_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    # check truckid
    if not truckid in TRUCKS.keys():
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truck = TRUCKS[truckid]
    
    # check owner
    if owner == "self":
        foruser = userid
        opuserid = userid
        assigneeid = userid
    elif owner == "company":
        foruser = -1000
        opuserid = -1000
    elif owner.startswith("user-"):
        foruser = userid.split("-")[1]
        opuserid = userid
        assigneeid = userid
        if not isint(foruser):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
        foruser = int(foruser)
        await aiosql.execute(f"SELECT userid FROM user WHERE userid = {userid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    else:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    
    # check garage slot (existence)
    await aiosql.execute(dhrid, f"SELECT garageid FROM economy_garage WHERE slotid = {slotid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    garageid = t[0][0]
    
    # check garage slot (occupied)
    await aiosql.execute(dhrid, f"SELECT slotid FROM economy_truck WHERE slotid = {slotid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_occupied", force_lang = au["language"])}
    
    # check truck model conflict
    model_conflict = False
    if foruser != -1000:
        await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE userid = {foruser} AND status = 1 AND truckid = '{truckid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    elif assigneeid != "NULL":
        await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE assigneeid = {assigneeid} AND status = 1 AND truckid = '{truckid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    status = not model_conflict

    # check balance
    await aiosql.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {opuserid} FOR UPDATE")
    balance = nint(await aiosql.fetchone(dhrid))
    await EnsureEconomyBalance(dhrid, opuserid) if balance == 0 else None
    
    if truck["price"] > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {truck['price']} WHERE userid = {opuserid}")
    await aiosql.execute(dhrid, f"INSERT INTO economy_truck(truckid, garageid, slotid, userid, price, income, service_cost, odometer, damage, purchase_timestamp, status) VALUES ('{truckid}', '{garageid}', {slotid}, {foruser}, {assigneeid}, {truck['price']}, 0, 0, 0, 0, {int(time.time())}, {status})")
    await aiosql.commit(dhrid)
    await aiosql.execute(dhrid, f"SELECT LAST_INSERT_ID();")
    vehicleid = (await aiosql.fetchone(dhrid))[0]
    await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({opuserid}, -1001, {truck['price']}, 't{vehicleid}-purchase', 'for-user-{foruser}', {int(balance - truck['price'])}, NULL, {int(time.time())})")
    await aiosql.commit(dhrid)

    username = (await GetUserInfo(dhrid, request, userid = foruser))["name"]
    await AuditLog(dhrid, au["uid"], ml.ctr("purchased_truck", var = {"name": truck["brand"] + " " + truck["model"], "id": truckid, "username": username, "userid": foruser}))

    return {"vehicleid": vehicleid, "cost": truck["price"], "balance": round(balance - truck["price"])}

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/transfer")
async def post_economy_trucks_transfer(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Transfer / Reassign a truck, returns 204.
    
    JSON: `{"owner": str, "assignee": Optional[int], "message": Optional[str]}`
    
    `owner` can be `self` | `company` | `user-{userid}`

    `assignee` is only required when `owner = company`
    
    [NOTE] If the new owner / assignee already has a truck of the same model, the transferred truck will be deactivated to prevent conflict on job submission.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/transfer', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    
    data = await request.json()
    try:
        # to reassign a truck, set owner to company and update assigneeid

        owner = data["owner"] # owner = self | company | user-{userid}
        
        # assignee only work for company trucks
        assigneeid = data["assignee"]
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
        foruser = userid.split("-")[1]
        assigneeid = foruser
        if not isint(foruser):
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
        foruser = int(foruser)
        await aiosql.execute(f"SELECT userid FROM user WHERE userid = {userid}")
        t = await aiosql.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 400
            return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    else:
        response.status_code = 400
        return {"error": ml.tr(request, "invalid_owner", force_lang = au["language"])}
    
    # check current owner
    await aiosql.execute(dhrid, f"SELECT truckid, userid, assigneeid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assigneeid = t[0][2]
    if current_owner != -1000 and current_owner == owner:
        response.status_code = 409
        return {"error": ml.tr(request, "new_owner_conflict", force_lang = au["language"])}
    
    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can transfer anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    # check truck model conflict
    model_conflict = False
    if foruser != -1000:
        await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE userid = {foruser} AND status = 1 AND truckid = '{truckid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    elif assigneeid != "NULL":
        await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE assigneeid = {assigneeid} AND status = 1 AND truckid = '{truckid}'")
        t = await aiosql.fetchall(dhrid)
        if len(t) != 0:
            model_conflict = True
    status = not model_conflict

    await aiosql.execute(dhrid, f"UPDATE economy_truck SET userid = {owner}, assigneeid = {assigneeid}, status = {status} WHERE vehicleid = {vehicleid}")
    await aiosql.commit(dhrid)

    if current_owner != owner:
        await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_owner}, {owner}, NULL, 't{vehicleid}-transfer', '{message}', NULL, NULL, {int(time.time())})")

        username = (await GetUserInfo(dhrid, request, userid = foruser))["name"]
        await AuditLog(dhrid, au["uid"], ml.ctr("transferred_truck", var = {"id": vehicleid, "username": username, "userid": foruser}))
    if current_assigneeid != assigneeid:
        await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({current_assigneeid}, {assigneeid}, NULL, 't{vehicleid}-reassign', 'staff-{userid}', NULL, NULL, {int(time.time())})")

        if assigneeid != "NULL":
            username = (await GetUserInfo(dhrid, request, userid = assigneeid))["name"]
            await AuditLog(dhrid, au["uid"], ml.ctr("reassigned_truck", var = {"id": vehicleid, "username": username, "userid": foruser}))
        else:
            await AuditLog(dhrid, au["uid"], ml.ctr("removed_truck_assignee", var = {"id": vehicleid}))

    await aiosql.commit(dhrid)
    
    return Response(status_code=204)

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/relocate")
async def post_economy_trucks_relocate(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Transfer / Reassign a truck, returns 204.
    
    JSON: `{"slotid": int"}`'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/relocate', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
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
    await aiosql.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    # check garage slot (existence)
    await aiosql.execute(dhrid, f"SELECT garageid FROM economy_garage WHERE slotid = {slotid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_not_found", force_lang = au["language"])}
    garageid = t[0][0]
    
    # check garage slot (occupied)
    await aiosql.execute(dhrid, f"SELECT slotid FROM economy_truck WHERE slotid = {slotid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) != 0:
        response.status_code = 400
        return {"error": ml.tr(request, "garage_slot_occupied", force_lang = au["language"])}

    await aiosql.execute(dhrid, f"UPDATE economy_truck SET garageid = '{convertQuotation(garageid)}', slotid = {slotid} WHERE vehicleid = {vehicleid}")
    await aiosql.commit(dhrid)

    garage = ml.ctr("unknown_garage")
    if garage in GARAGES.keys():
        garage = GARAGES[garage]["name"]

    await AuditLog(dhrid, au["uid"], ml.ctr("relocated_truck", var = {"id": vehicleid, "garage": garage, "garageid": garageid, "slotid": slotid}))

    return Response(status_code=204)

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/activate")
async def post_economy_trucks_activate(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Activates a truck, returns 204.
    
    [NOTE] If the owner / assignee has multiple trucks of the same model, other trucks of the same model will be deactivated.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/activate', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]
    
    # check current owner
    await aiosql.execute(dhrid, f"SELECT truckid, userid, assigneeid, status FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assigneeid = t[0][2]
    status = t[0][3]

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    if status == -1:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_repair_required", force_lang = au["language"])}
    if status == -2:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_scrap_required", force_lang = au["language"])}

    # check truck model conflict
    if current_owner != -1000:
        await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE userid = {current_owner} AND truckid = '{truckid}'")
    elif current_assigneeid is not None:
        await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE assigneeid = {current_assigneeid} AND truckid = '{truckid}'")
    await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 1 WHERE vehicleid = {vehicleid}")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/deactivate")
async def post_economy_trucks_deactivate(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Deactivates a truck, returns 204.
    
    [NOTE] If there's no status truck of a model, new jobs of that model will be charged a rental cost.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/deactivate', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    # check current owner
    await aiosql.execute(dhrid, f"SELECT userid FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE vehicleid = {vehicleid}")
    await aiosql.commit(dhrid)

    return Response(status_code=204)

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/repair")
async def post_economy_trucks_repair(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Repairs a truck, returns `cost`, `balance`.
    
    [NOTE] If the truck's damage > config.economy.max_wear_before_service, new jobs will be charged a rental cost. Once the issue is noticed, status state of the truck will be modified to -1. If the truck's state is -1 and a repair is performed, it will be reactivated automatically if there's no other status trucks.'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/repair', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    # check current owner
    await aiosql.execute(dhrid, f"SELECT truckid, userid, assignee, damage, status FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    truckid = t[0][0]
    current_owner = t[0][1]
    current_assignee = t[0][2]
    damage = t[0][3]
    status = t[0][4]

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    # check balance
    await aiosql.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid} FOR UPDATE")
    balance = nint(await aiosql.fetchone(dhrid))
    await EnsureEconomyBalance(dhrid, userid) if balance == 0 else None
    
    cost = round(damage * 100 * config.economy.unit_service_price)
    if cost > balance:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}
    
    await aiosql.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {cost} WHERE userid = {userid}")
    await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({userid}, -1004, {cost}, 't{vehicleid}-service', 'damage-{damage}', {int(balance - cost)}, NULL, {int(time.time())})")
    await aiosql.commit(dhrid)

    await aiosql.execute(dhrid, f"UPDATE economy_truck SET damage = 0, service_cost = service_cost + {cost} WHERE vehicleid = {vehicleid}")
    if status == -1:
        model_conflict = False
        if current_owner != -1000:
            await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE userid = {current_owner} AND status = 1 AND truckid = '{truckid}'")
            t = await aiosql.fetchall(dhrid)
            if len(t) != 0:
                model_conflict = True
        elif current_assignee != "NULL":
            await aiosql.execute(dhrid, f"SELECT vehicleid FROM economy_truck WHERE assigneeid = {current_assignee} AND status = 1 AND truckid = '{truckid}'")
            t = await aiosql.fetchall(dhrid)
            if len(t) != 0:
                model_conflict = True
        if not model_conflict:
            await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 1 WHERE vehicleid = {vehicleid}")
        else:
            await aiosql.execute(dhrid, f"UPDATE economy_truck SET status = 0 WHERE vehicleid = {vehicleid}")
    await aiosql.commit(dhrid)

    return {"cost": cost, "balance": round(balance - cost)}

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/sell")
async def post_economy_trucks_sell(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Sells a truck, returns `refund`, `balance`.
    
    [Note] refund = price * (1 - damage) * config.economy.truck_refund (ratio)'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/sell', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    # check current owner
    await aiosql.execute(dhrid, f"SELECT userid, odometer, damage, price FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    odometer = t[0][1]
    damage = t[0][2]
    price = t[0][3]
    refund = round(price * (1 - damage) * config.economy.truck_refund)

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    # check balance
    await aiosql.execute(dhrid, f"UPDATE economy_truck SET userid = -1001, active = 0 WHERE vehicleid = {vehicleid}")
    await aiosql.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await aiosql.fetchone(dhrid))
    await EnsureEconomyBalance(dhrid, current_owner) if balance == 0 else None
    await aiosql.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1001, {current_owner}, {refund}, 't{vehicleid}-sell', 'damage-{damage}/odometer-{odometer}/refund-{config.economy.truck_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await aiosql.commit(dhrid)

    return {"refund": refund, "balance": round(balance + refund)}

@app.post(f"/{config.abbr}/economy/trucks/{{vehicleid}}/scrap")
async def post_economy_trucks_scrap(request: Request, response: Response, vehicleid: str, authorization: str = Header(None)):
    '''Scraps a truck, returns `refund`, `balance`.
    
    [Note] refund = price * config.economy.scrap_refund (ratio)'''
    dhrid = request.state.dhrid
    await aiosql.new_conn(dhrid)

    rl = await ratelimit(dhrid, request, 'POST /economy/trucks/vehicleid/scrap', 60, 30)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(dhrid, authorization, request, check_member = True, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    userid = au["userid"]

    # check current owner
    await aiosql.execute(dhrid, f"SELECT userid, odometer, damage, price FROM economy_truck WHERE vehicleid = {vehicleid}")
    t = await aiosql.fetchall(dhrid)
    if len(t) == 0:
        response.status_code = 404
        return {"error": ml.tr(request, "truck_not_found", force_lang = au["language"])}
    current_owner = t[0][0]
    odometer = t[0][1]
    damage = t[0][2]
    price = t[0][3]
    refund = round(price * config.economy.scrap_refund)

    # check perm
    permok = checkPerm(au["roles"], ["admin", "economy_manager", "truck_manager"])

    # company truck but not manager or not owned truck
    # manager can relocate anyone's truck
    if not permok:
        if current_owner == -1000 or current_owner != userid:
            response.status_code = 403
            return {"error": ml.tr(request, "modify_forbidden", var = {"item": ml.tr(request, "truck", force_lang = au["language"])}, force_lang = au["language"])}
    
    if odometer < 0.9 * config.economy.max_distance_before_scrap:
        response.status_code = 428
        return {"error": ml.tr(request, "truck_scrap_unncessary", force_lang = au["language"])}

    # check balance
    await aiosql.execute(dhrid, f"UPDATE economy_truck SET userid = -1005, active = 0 WHERE vehicleid = {vehicleid}")
    await aiosql.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {current_owner} FOR UPDATE")
    balance = nint(await aiosql.fetchone(dhrid))
    await EnsureEconomyBalance(dhrid, current_owner) if balance == 0 else None
    await aiosql.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {refund} WHERE userid = {current_owner}")
    await aiosql.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES (-1005, {current_owner}, {refund}, 't{vehicleid}-scrap', 'damage-{damage}/odometer-{odometer}/refund-{config.economy.truck_refund}', NULL, {round(balance + refund)}, {int(time.time())})")
    await aiosql.commit(dhrid)

    return {"refund": refund, "balance": round(balance + refund)}