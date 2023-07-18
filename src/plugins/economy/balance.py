# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import math
import time
from io import BytesIO
from typing import Optional

from fastapi import Header, Request, Response
from fastapi.responses import StreamingResponse

import multilang as ml
from functions import *


async def get_balance_leaderboard(request: Request, response: Response, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 20, after_userid: Optional[int] = None, \
        exclude_company: Optional[bool] = True, \
        min_balance: Optional[int] = None, max_balance: Optional[int] = None, order: Optional[str] = "desc"):
    '''Get balance leaderboard.

    [NOTE] If authorized user is not a balance_manager, and the user chose to hide their balance, they will not be included in the leaderboard.
    If authorized user is a balance_manager, they can view the full leaderboard.
    User balance is by default private.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/balance/leaderboard', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    limit = ""
    if min_balance is not None:
        limit += f"AND balance >= {min_balance} "
    if max_balance is not None:
        limit += f"AND balance <= {max_balance} "
    if exclude_company:
        limit += "AND userid >= 0 "

    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"])
    public_userids = [au["userid"]]
    included_userids = []

    if not permok:
        await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'public-balance'")
    else:
        await app.db.execute(dhrid, "SELECT userid FROM user WHERE userid >= 0")
        public_userids.append(-1000)
    t = await app.db.fetchall(dhrid)
    for tt in t:
        public_userids.append(int(tt[0]))
    if public_userids.count(au["userid"]) == 2:
        public_userids.remove(au["userid"])
    if exclude_company:
        public_userids.remove(-1000)

    await app.db.execute(dhrid, f"SELECT userid, balance FROM economy_balance WHERE (userid >= 0 OR userid = -1000) AND balance > 0 {limit} ORDER BY balance {order}")
    t = await app.db.fetchall(dhrid)
    d = []

    # get only public users
    for tt in t:
        if tt[0] in public_userids:
            d.append(tt)
            included_userids.append(tt[0])

    # add users that are not in list
    for tuserid in included_userids:
        public_userids.remove(tuserid)
    public_userids = sorted(public_userids)
    to_add = []
    for tuserid in public_userids:
        to_add.append((tuserid, 0))
    if order == "asc":
        d = to_add + d
    elif order == "desc":
        d = d + to_add

    # filter balance
    p = []
    for dd in d:
        if (min_balance is None or dd[1] >= min_balance) and (max_balance is None or dd[1] <= max_balance):
            p.append(dd)

    # select ?after_userid
    if after_userid is not None:
        while len(p) > 0 and p[0][0] != after_userid:
            p = p[1:]

    tot = len(p)

    # select only those in page
    d = p[page_size*max(page-1, 0):page_size*page]

    # create ret[]
    ret = []
    for dd in d:
        ret.append({"user": await GetUserInfo(request, userid = dd[0]), "balance": dd[1]})

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def post_balance_transfer(request: Request, response: Response, authorization: str = Header(None)):
    '''Transfer balance.

    JSON: `{"from_userid": Optional[int], "to_userid": int, "amount": int, "message": Optional[str]}`'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'POST /economy/balance/transfer', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au
    opuserid = au["userid"]

    data = await request.json()
    try:
        if "from_userid" in data.keys():
            from_userid = int(data["from_userid"])
        else:
            from_userid = opuserid
        to_userid = int(data["to_userid"])
        amount = int(data["amount"])

        if abs(amount) > 4294967296:
            response.status_code = 400
            return {"error": ml.tr(request, "value_too_large", var = {"item": "amount", "limit": "4,294,967,296"}, force_lang = au["language"])}

        if "message" in data.keys():
            message = data["message"]
        else:
            message = ""
    except:
        response.status_code = 400
        return {"error": ml.tr(request, "bad_json", force_lang = au["language"])}
    if amount <= 0:
        response.status_code = 400
        return {"error": ml.tr(request, "amount_must_be_positive", force_lang = au["language"])}

    balance_manager_perm_ok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"])
    company_balance_perm_ok = balance_manager_perm_ok or checkPerm(app, au["roles"], "accountant")

    if from_userid == -1000 and not company_balance_perm_ok:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_company_balance_forbidden", force_lang = au["language"])}
    if from_userid != opuserid and not balance_manager_perm_ok:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_user_balance_forbidden", force_lang = au["language"])}

    if from_userid != -1000: # can only send FROM company to user
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {from_userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "from_user_not_found", force_lang = au["language"])}
    if to_userid not in list(range(-1006,-999)): # can send TO any virtual account
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {to_userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "to_user_not_found", force_lang = au["language"])}
    if from_userid == to_userid:
        if from_userid != opuserid:
            response.status_code = 400
            return {"error": ml.tr(request, "from_to_user_must_not_be_same", force_lang = au["language"])}
        else:
            response.status_code = 400
            return {"error": ml.tr(request, "cannot_transfer_to_oneself", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {from_userid} FOR UPDATE")
    from_balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, from_userid) if from_balance == 0 else None
    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {to_userid} FOR UPDATE")
    to_balance = nint(await app.db.fetchone(dhrid))
    await EnsureEconomyBalance(request, to_userid) if to_balance == 0 else None

    if from_balance < amount:
        response.status_code = 402
        return {"error": ml.tr(request, "insufficient_balance", force_lang = au["language"])}

    await app.db.execute(dhrid, f"INSERT INTO economy_transaction(from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp) VALUES ({from_userid}, {to_userid}, {amount}, 'regular-tx/by-{opuserid}', '{convertQuotation(message)}', {from_balance - amount}, {to_balance - amount}, {int(time.time())})")
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance - {amount} WHERE userid = {from_userid}")
    await app.db.execute(dhrid, f"UPDATE economy_balance SET balance = balance + {amount} WHERE userid = {to_userid}")
    await app.db.commit(dhrid)

    from_user = await GetUserInfo(request, userid = from_userid)
    to_user = await GetUserInfo(request, userid = to_userid)
    from_user_language = await GetUserLanguage(request, from_user["uid"])
    to_user_language = await GetUserLanguage(request, to_user["uid"])

    from_message = ""
    to_message = ""
    if message != "":
        from_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = from_user_language)
        to_message = "  \n" + ml.tr(request, "economy_transaction_message", var = {"message": message}, force_lang = to_user_language)

    await notification(request, "economy", from_user["uid"], ml.tr(request, "economy_sent_transaction", var = {"amount": amount, "currency_name": app.config.economy.currency_name, "to_user": to_user["name"], "to_userid": to_user["userid"] if to_user["userid"] is not None else "N/A", "message": from_message}, force_lang = from_user_language))
    await notification(request, "economy", to_user["uid"], ml.tr(request, "economy_received_transaction", var = {"amount": amount, "currency_name": app.config.economy.currency_name, "from_user": from_user["name"], "from_userid": from_user["userid"] if from_user["userid"] is not None else "N/A", "message": to_message}, force_lang = to_user_language))

    if company_balance_perm_ok:
        return {"from_balance": from_balance - amount, "to_balance": to_balance + amount}
    else:
        return {"from_balance": from_balance - amount}

async def get_balance(request: Request, response: Response, authorization: str = Header(None), userid: Optional[int] = None):
    '''Get user balance.

    [NOTE] If authorized user is not a balance_manager, and the user chose to hide their balance, 403 will be returned.
    If authorized user is a balance_manager, they can view the user's balance without restrictions.
    User balance is by default private.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/balance/userid', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if userid is None:
        userid = au["userid"]

    if userid != -1000:
        await app.db.execute(dhrid, f"SELECT userid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"]) or userid == au["userid"]

    if not permok:
        await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE sval = '{userid}' AND skey = 'public-balance'")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 403
            return {"error": ml.tr(request, "view_balance_forbidden", force_lang = au["language"])}
        # NOTE To make balance private, delete the row from settings.

    await app.db.execute(dhrid, f"SELECT balance FROM economy_balance WHERE userid = {userid}")
    balance = nint(await app.db.fetchone(dhrid))

    return {"balance": balance}

async def get_balance_transaction_list(request: Request, response: Response, userid: int, authorization: str = Header(None), \
        page: Optional[int] = 1, page_size: Optional[int] = 10, after_txid: Optional[int] = None, \
        after: Optional[int] = None, before: Optional[int] = None, \
        from_userid: Optional[int] = None, to_userid: Optional[int] = None, \
        min_amount: Optional[int] = None, max_amount: Optional[int] = None, \
        order: Optional[str] = "desc", order_by: Optional[str] = "timestamp"):
    '''Get a user's transaction history.

    [NOTE] This can only be viewed by balance manager and user. The user cannot make this info public.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/balance/userid/transactions/list', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if userid != -1000:
        await app.db.execute(dhrid, f"SELECT uid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    balance_manager_perm_ok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"])
    permok = balance_manager_perm_ok or userid == au["userid"]

    if not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "view_transaction_history_forbidden", force_lang = au["language"])}

    await ActivityUpdate(request, au["uid"], "economy_transactions")

    if page_size <= 1:
        page_size = 1
    elif page_size >= 250:
        page_size = 250

    limit = ""
    if after is not None:
        limit += f"AND timestamp >= {after} "
    if before is not None:
        limit += f"AND timestamp <= {before} "

    if from_userid is not None:
        limit += f"AND from_userid = {from_userid} "
    if to_userid is not None:
        limit += f"AND to_userid = {to_userid} "

    if min_amount is not None:
        limit += f"AND amount >= {min_amount} "
    if max_amount is not None:
        limit += f"AND amount <= {max_amount} "

    if order_by not in ["timestamp", "amount"]:
        order_by = "timestamp"
        order = "desc"

    order = order.lower()
    if order not in ["asc", "desc"]:
        order = "asc"

    base_rows = 0
    tot = 0
    await app.db.execute(dhrid, f"SELECT txid FROM economy_transaction WHERE txid >= 0 AND note LIKE 'regular-tx/%' {limit} ORDER BY {order_by} {order}")
    t = await app.db.fetchall(dhrid)
    if len(t) == 0:
        return {"list": [], "total_items": 0, "total_pages": 0}
    tot = len(t)
    if after_txid is not None:
        for tt in t:
            if tt[0] == after_txid:
                break
            base_rows += 1
        tot -= base_rows

    await app.db.execute(dhrid, f"SELECT txid, from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp FROM economy_transaction WHERE txid >= 0 AND note LIKE 'regular-tx/%' {limit} ORDER BY {order_by} {order} LIMIT {base_rows + max(page-1, 0) * page_size}, {page_size}")
    t = await app.db.fetchall(dhrid)
    ret = []
    for tt in t:
        note = tt[4].split("/")
        executorid = int(note[1].split("-")[1])
        d = {"txid": tt[0], "from_user": await GetUserInfo(request, userid = tt[1]), "to_user": await GetUserInfo(request, userid = tt[2]), "executor": await GetUserInfo(request, userid = executorid),"amount": tt[3], "from_new_balance": tt[6], "to_new_balance": tt[7], "message": tt[5]}
        if not balance_manager_perm_ok:
            if tt[1] != au["userid"]:
                d["from_new_balance"] = None
            elif tt[2] != au["userid"]:
                d["to_new_balance"] = None
        ret.append(d)

    return {"list": ret, "total_items": tot, "total_pages": int(math.ceil(tot / page_size))}

async def get_balance_transaction_export(request: Request, response: Response, userid: int, authorization: str = Header(None), after: Optional[int] = None, before: Optional[int] = None):
    '''Export a user's transaction history.

    [NOTE] This can only be done by balance manager and user. The user cannot make this info public.'''
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/balance/userid/transactions/export', 300, 3)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if userid != -1000:
        await app.db.execute(dhrid, f"SELECT uid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}

    balance_manager_perm_ok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"])
    permok = balance_manager_perm_ok or userid == au["userid"]

    if not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "view_transaction_history_forbidden", force_lang = au["language"])}

    limit = ""
    if after is not None:
        limit += f"AND timestamp >= {after} "
    if before is not None:
        limit += f"AND timestamp <= {before} "

    f = BytesIO()
    f.write(b"txid, from_userid, to_userid, executor_userid, amount, message, from_new_balance, to_new_balance, time\n")

    await app.db.execute(dhrid, f"SELECT txid, from_userid, to_userid, amount, note, message, from_new_balance, to_new_balance, timestamp FROM economy_transaction WHERE txid >= 0 AND note LIKE 'regular-tx/%' {limit} ORDER BY timestamp DESC")
    t = await app.db.fetchall(dhrid)
    for tt in t:
        note = tt[4].split("/")
        executorid = int(note[1].split("-")[1])

        from_userid = tt[1]
        to_userid = tt[2]
        if from_userid == -1000:
            from_userid = "company"
        if to_userid == -1000:
            to_userid = "company"

        from_new_balance = tt[7]
        to_new_balance = tt[8]
        if not balance_manager_perm_ok:
            if tt[1] != au["userid"] or from_new_balance is None:
                from_new_balance = "/"
            elif tt[2] != au["userid"] or to_new_balance is None:
                to_new_balance = "/"

        data = [tt[0], from_userid, to_userid, executorid, tt[3], tt[5], from_new_balance, to_new_balance, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(tt[8]))]

        for i in range(len(data)):
            if data[i] is None:
                data[i] = '""'
            else:
                data[i] = '"' + str(data[i]) + '"'

        f.write(",".join(data).encode("utf-8"))
        f.write(b"\n")

    response = StreamingResponse(iter([f.getvalue()]), media_type="text/csv")
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]
    response.headers["Content-Disposition"] = "attachment; filename=transactions.csv"

    return response

async def post_balance_visibility(request: Request, response: Response, userid: int, visibility: str, authorization: str = Header(None)):
    '''Make user balance public.'''
    app = request.app
    if visibility not in ["public", "private"]:
        response.status_code = 404
        return {"error": "Not Found"}

    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy/balance/userid/visibility', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    if userid != -1000:
        await app.db.execute(dhrid, f"SELECT uid FROM user WHERE userid = {userid}")
        t = await app.db.fetchall(dhrid)
        if len(t) == 0:
            response.status_code = 404
            return {"error": ml.tr(request, "user_not_found", force_lang = au["language"])}
        uid = t[0][0]
    else:
        uid = "NULL"

    permok = checkPerm(app, au["roles"], ["admin", "economy_manager", "balance_manager"]) or userid == au["userid"]

    if not permok:
        response.status_code = 403
        return {"error": ml.tr(request, "modify_balance_visibility_forbidden", force_lang = au["language"])}

    await app.db.execute(dhrid, f"SELECT sval FROM settings WHERE sval = '{userid}' AND skey = 'public-balance'")
    t = await app.db.fetchall(dhrid)
    if len(t) != 0:
        if visibility == "public":
            response.status_code = 409
            return {"error": ml.tr(request, "balance_visibility_already_public", force_lang = au["language"])}
        elif visibility == "private":
            await app.db.execute(dhrid, f"DELETE FROM settings WHERE sval = '{userid}' AND skey = 'public-balance'")
            await app.db.commit(dhrid)
            return Response(status_code=204)
    else:
        if visibility == "private":
            response.status_code = 409
            return {"error": ml.tr(request, "balance_visibility_already_private", force_lang = au["language"])}
        elif visibility == "public":
            await app.db.execute(dhrid, f"INSERT INTO settings VALUES ({uid}, 'public-balance', '{userid}')")
            await app.db.commit(dhrid)
            return Response(status_code=204)
