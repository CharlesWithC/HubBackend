# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from functions import *
from plugins.economy.balance import *
from plugins.economy.garages import *
from plugins.economy.merch import *
from plugins.economy.trucks import *

# NOTE
# If driver leaves the company, they'll take away their truck and balance.
# However, their garage will be transferred to the company.

async def get_economy(request: Request, response: Response, authorization: str = Header(None)):
    app = request.app
    dhrid = request.state.dhrid
    await app.db.new_conn(dhrid)

    rl = await ratelimit(request, 'GET /economy', 60, 60)
    if rl[0]:
        return rl[1]
    for k in rl[1].keys():
        response.headers[k] = rl[1][k]

    au = await auth(authorization, request, allow_application_token = True)
    if au["error"]:
        response.status_code = au["code"]
        del au["code"]
        return au

    ret = app.config.economy.__dict__
    del ret["trucks"]
    del ret["garages"]
    del ret["merch"]
    return ret