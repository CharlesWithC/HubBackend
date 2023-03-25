# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from app import app, config
from functions import *
from plugins.economy.truck import *


@app.get(f"/{config.abbr}/economy/trucks")
async def get_economy_trucks():
    return config.economy.trucks

@app.get(f"/{config.abbr}/economy/garages")
async def get_economy_garages():
    return config.economy.garages

# TODO garage slot purchase (if no slot is purchased, then purchase garage (= base_slots slot))
# TODO garage slot sell (if remaining slot = base_slots, then sell garage) | if there's truck in the slot, prevent sell, ask them to contact the truck owner
# TODO garage slot transfer
# TODO garage info (overview, e.g. owner, total slots / trucks, total revenue)
# TODO garage slot info (list based, include truck parked there, only slot owner + company manager has access)

# TODO balance transfer
# TODO balance list (company manager / config.enable_balance_leaderboard)
# TODO balance transaction list
# TODO balance of user / company (company manager / balance owner)

# NOTE convert quotation for garageid