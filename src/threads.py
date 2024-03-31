# Copyright (C) 2024 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import asyncio
import copy
import json
import os
import time
import traceback

from fastapi import Request

import static
from config import validateConfig
from functions.dataop import *
from functions.discord import DiscordAuth
from functions.general import *
from functions.userinfo import DeleteRoleConnection
from logger import logger


async def DetectConfigChanges(app):
    # NOTE Why? When running in multiple workers, app is not synced between workers, hence config cannot be synced
    while 1:
        try:
            if not os.path.exists(app.config_path):
                # just in case
                try:
                    await asyncio.sleep(600)
                except:
                    return
                continue

            if app.config_last_modified != os.path.getmtime(app.config_path):
                # modified
                config_txt = open(app.config_path, "r", encoding="utf-8").read()
                config = validateConfig(json.loads(config_txt))
                config = Dict2Obj(config)
                app.config = config
                app.backup_config = copy.deepcopy(config.__dict__)
                app.config_last_modified = os.path.getmtime(app.config_path)
                logger.info(f"[{app.config.abbr}] [PID: {os.getpid()}] Config modification detected, reloaded config.")
                app = static.load(app)

        except:
            pass

        try:
            await asyncio.sleep(30)
        except:
            return

async def ClearOutdatedData(app):
    while 1:
        # combined thread
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)
            request = Request(scope={"type":"http", "app": app, "headers": []})
            request.state.dhrid = dhrid

            await app.db.execute(dhrid, f"DELETE FROM banned WHERE expire_timestamp < {int(time.time())}")
            await app.db.commit(dhrid)

            await app.db.execute(dhrid, f"SELECT uid, discordid FROM user WHERE email = 'pending' AND join_timestamp < {int(time.time() - 86400)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                uid = tt[0]
                discordid = tt[1]
                await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM pending_user_deletion WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")

                await DeleteRoleConnection(request, discordid)

            await app.db.execute(dhrid, f"SELECT uid FROM pending_user_deletion WHERE expire_timestamp < {int(time.time())}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                uid = tt[0]

                await app.db.execute(dhrid, f"SELECT discordid FROM user WHERE uid = {uid}")
                p = await app.db.fetchall(dhrid)
                if len(p) > 0:
                    discordid = p[0][0]
                    await DeleteRoleConnection(request, discordid)

                await app.db.execute(dhrid, f"DELETE FROM user WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM pending_user_deletion WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM email_confirmation WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_password WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_activity WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM user_notification WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM session WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM auth_ticket WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM application_token WHERE uid = {uid}")
                await app.db.execute(dhrid, f"DELETE FROM settings WHERE uid = {uid}")

            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)
        except:
            pass

        try:
            await asyncio.sleep(60)
        except:
            return

async def RefreshDiscordAccessToken(app):
    rrnd = 0
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)

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

            await app.db.execute(dhrid, f"SELECT discordid, callback_url, refresh_token FROM discord_access_token WHERE expire_timestamp <= {int(time.time() + 3600)}")
            t = await app.db.fetchall(dhrid)
            for tt in t:
                (discordid, callback_url, refresh_token) = (tt[0], tt[1], tt[2])
                await app.db.extend_conn(dhrid, 30)
                discord_auth = DiscordAuth(app.config.discord_client_id, app.config.discord_client_secret, callback_url)
                tokens = await discord_auth.refresh_token(refresh_token)
                await app.db.extend_conn(dhrid, 2)
                await app.db.execute(dhrid, f"DELETE FROM discord_access_token WHERE discordid = {discordid}")
                if "error" in tokens.keys():
                    continue

                (access_token, refresh_token, expire_timestamp) = (convertQuotation(tokens["access_token"]), convertQuotation(tokens["refresh_token"]), tokens["expires_in"] + int(time.time()) - 60)
                await app.db.execute(dhrid, f"INSERT INTO discord_access_token VALUES ({discordid}, '{convertQuotation(callback_url)}', '{access_token}', '{refresh_token}', {expire_timestamp})")

            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)

        except:
            pass

        await asyncio.sleep(600)

async def UpdateDlogStats(app):
    request = Request(scope={"type":"http", "app": app, "headers": [], "mocked": True})
    rrnd = 0
    while 1:
        try:
            dhrid = genrid()
            await app.db.new_conn(dhrid)

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

            await app.db.execute(dhrid, "SELECT sval FROM settings WHERE skey = 'dlog_stats_up_to'")
            t = await app.db.fetchall(dhrid)
            dlog_stats_up_to = int(t[0][0])

            await app.db.execute(dhrid, "SELECT MAX(logid) FROM dlog")
            t = await app.db.fetchone(dhrid)
            max_log_id = t[0]

            for logid in range(dlog_stats_up_to + 1, max_log_id + 1):
                try:
                    await app.db.execute(dhrid, f"SELECT logid, userid, data FROM dlog WHERE logid = {logid}")
                    t = await app.db.fetchall(dhrid)
                    if len(t) == 0:
                        continue
                    tt = t[0]
                    userid = tt[1]
                    try:
                        d = json.loads(decompress(tt[2]))
                    except:
                        continue

                    dlog_stats = {}

                    obj = d["data"]["object"]

                    dlog_stats[3] = []

                    truck = obj["truck"]
                    if truck is not None:
                        if "unique_id" in truck.keys() and "name" in truck.keys() and \
                                truck["brand"] is not None and "name" in truck["brand"].keys():
                            dlog_stats[1] = [[convertQuotation(truck["unique_id"]), convertQuotation(truck["brand"]["name"]) + " " + convertQuotation(truck["name"]), 1, 0]]
                        if "license_plate_country" in truck.keys() and truck["license_plate_country"] is not None and \
                                "unique_id" in truck["license_plate_country"].keys() and "name" in truck["license_plate_country"].keys():
                            dlog_stats[3] = [[convertQuotation(truck["license_plate_country"]["unique_id"]), convertQuotation(truck["license_plate_country"]["name"]), 1, 0]]

                    for trailer in obj["trailers"]:
                        if "body_type" in trailer.keys():
                            body_type = trailer["body_type"]
                            dlog_stats[2]  = [[convertQuotation(body_type), convertQuotation(body_type), 1, 0]]
                        if "license_plate_country" in trailer.keys() and trailer["license_plate_country"] is not None and \
                                "unique_id" in trailer["license_plate_country"].keys() and "name" in trailer["license_plate_country"].keys():
                            item = [convertQuotation(trailer["license_plate_country"]["unique_id"]), convertQuotation(trailer["license_plate_country"]["name"]), 1, 0]
                            duplicate = False
                            for i in range(len(dlog_stats[3])):
                                if dlog_stats[3][i][0] == item[0] and dlog_stats[3][i][1] == item[1]:
                                    dlog_stats[3][i][2] += 1
                                    duplicate = True
                                    break
                            if not duplicate:
                                dlog_stats[3].append(item)

                    cargo = obj["cargo"]
                    if cargo is not None and "unique_id" in cargo.keys() and "name" in cargo.keys():
                        dlog_stats[4] = [[convertQuotation(cargo["unique_id"]), convertQuotation(cargo["name"]), 1, 0]]

                    if "market" in obj.keys():
                        dlog_stats[5] = [[convertQuotation(obj["market"]), convertQuotation(obj["market"]), 1, 0]]

                    source_city = obj["source_city"]
                    if source_city is not None and "unique_id" in source_city.keys() and "name" in source_city.keys():
                        dlog_stats[6] = [[convertQuotation(source_city["unique_id"]), convertQuotation(source_city["name"]), 1, 0]]
                    source_company = obj["source_company"]
                    if source_company is not None and "unique_id" in source_company.keys() and "name" in source_company.keys():
                        dlog_stats[7] = [[convertQuotation(source_company["unique_id"]), convertQuotation(source_company["name"]), 1, 0]]
                    destination_city = obj["destination_city"]
                    if destination_city is not None and "unique_id" in destination_city.keys() and "name" in destination_city.keys():
                        dlog_stats[8] = [[convertQuotation(destination_city["unique_id"]), convertQuotation(destination_city["name"]), 1, 0]]
                    destination_company = obj["destination_company"]
                    if destination_company is not None and "unique_id" in destination_company.keys() and "name" in destination_company.keys():
                        dlog_stats[9] = [[convertQuotation(destination_company["unique_id"]), convertQuotation(destination_company["name"]), 1, 0]]

                    mode = ("single_player", "Single Player")
                    if obj["multiplayer"] is not None:
                        if obj["multiplayer"]["type"] == "truckersmp":
                            mode = ("truckersmp", "TruckersMP")
                        elif obj["multiplayer"]["type"] == "scs_convoy":
                            mode = ("scs_convoy", "SCS Convoy")
                        elif obj["multiplayer"]["type"] == "multiplayer":
                            mode = ("multiplayer", "Multi Player")
                        else:
                            mode = (obj["multiplayer"]["type"], obj["multiplayer"]["type"])
                    dlog_stats[17] = [[mode[0], mode[1], 1, 0]]

                    for i in range(10, 17):
                        dlog_stats[i] = []

                    for event in d["data"]["object"]["events"]:
                        etype = event["type"]
                        if etype == "fine":
                            item = [event["meta"]["offence"], event["meta"]["offence"], 1, int(event["meta"]["amount"])]
                            item[3] = item[3] if item[3] <= 51200 else 0
                            duplicate = False
                            for i in range(len(dlog_stats[10])):
                                if dlog_stats[10][i][0] == item[0] and dlog_stats[10][i][1] == item[1]:
                                    dlog_stats[10][i][2] += 1
                                    dlog_stats[10][i][3] += item[3]
                                    duplicate = True
                                    break
                            if not duplicate:
                                dlog_stats[10].append(item)

                        elif etype in ["collision", "speeding", "teleport"]:
                            K = {"collision": 15, "speeding": 11, "teleport": 16}
                            item = [etype, etype, 1, 0]
                            duplicate = False
                            for i in range(len(dlog_stats[K[etype]])):
                                if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                                    dlog_stats[K[etype]][i][2] += 1
                                    duplicate = True
                                    break
                            if not duplicate:
                                dlog_stats[K[etype]].append(item)

                        elif etype in ["tollgate"]:
                            K = {"tollgate": 12}
                            item = [etype, etype, 1, int(event["meta"]["cost"])]
                            item[3] = item[3] if item[3] <= 51200 else 0
                            duplicate = False
                            for i in range(len(dlog_stats[K[etype]])):
                                if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                                    dlog_stats[K[etype]][i][2] += 1
                                    dlog_stats[K[etype]][i][3] += item[3]
                                    duplicate = True
                                    break
                            if not duplicate:
                                dlog_stats[K[etype]].append(item)

                        elif etype in ["ferry", "train"]:
                            K = {"ferry": 13, "train": 14}
                            item = [f'{convertQuotation(event["meta"]["source_id"])}/{convertQuotation(event["meta"]["target_id"])}', f'{convertQuotation(event["meta"]["source_name"])}/{convertQuotation(event["meta"]["target_name"])}', 1, int(event["meta"]["cost"])]
                            item[3] = item[3] if item[3] <= 51200 else 0
                            duplicate = False
                            for i in range(len(dlog_stats[K[etype]])):
                                if dlog_stats[K[etype]][i][0] == item[0] and dlog_stats[K[etype]][i][1] == item[1]:
                                    dlog_stats[K[etype]][i][2] += 1
                                    dlog_stats[K[etype]][i][3] += item[3]
                                    duplicate = True
                                    break
                            if not duplicate:
                                dlog_stats[K[etype]].append(item)

                    await app.db.extend_conn(dhrid, 5)
                    for stat_userid in [userid, -1]:
                        # -1 refers to company
                        p = {}
                        pname = {}
                        await app.db.execute(dhrid, f"SELECT item_type, item_key, item_name FROM dlog_stats WHERE userid = {stat_userid}")
                        t = await app.db.fetchall(dhrid)
                        for tt in t:
                            if tt[0] not in p.keys():
                                p[tt[0]] = [tt[1]]
                            else:
                                p[tt[0]].append(tt[1])
                            pname[(tt[0], tt[1])] = tt[2]

                        for itype in dlog_stats.keys():
                            if itype not in p.keys():
                                for dd in dlog_stats[itype]:
                                    if dd[0] == "None":
                                        continue
                                    await app.db.execute(dhrid, f"INSERT INTO dlog_stats VALUES ({itype}, {stat_userid}, '{dd[0]}', '{dd[1]}', {dd[2]}, {dd[3]})")
                                    await app.db.commit(dhrid)
                            else:
                                for dd in dlog_stats[itype]:
                                    if dd[0] not in p[itype]:
                                        if dd[0] == "None":
                                            continue
                                        await app.db.execute(dhrid, f"INSERT INTO dlog_stats VALUES ({itype}, {stat_userid}, '{dd[0]}', '{dd[1]}', {dd[2]}, {dd[3]})")
                                        await app.db.commit(dhrid)
                                    else:
                                        if dd[0] == "None":
                                            continue
                                        await app.db.execute(dhrid, f"UPDATE dlog_stats SET count = count + {dd[2]}, sum = sum + {dd[3]} WHERE item_type = {itype} AND item_key = '{dd[0]}' AND userid = {stat_userid}")
                                        await app.db.commit(dhrid)
                                        if pname[(itype, dd[0])] != dd[1]:
                                            await app.db.execute(dhrid, f"UPDATE dlog_stats SET item_name = '{dd[1]}' WHERE item_type = {itype}  AND item_key = '{dd[0]}' AND userid = {stat_userid}")
                                            await app.db.commit(dhrid)

                    await app.db.execute(dhrid, f"UPDATE settings SET sval = {logid} WHERE skey = 'dlog_stats_up_to'")
                    await app.db.commit(dhrid)
                except Exception as exc:
                    from api import tracebackHandler
                    await tracebackHandler(request, exc, traceback.format_exc())

            await app.db.commit(dhrid)
            await app.db.close_conn(dhrid)

        except Exception as exc:
            from api import tracebackHandler
            await tracebackHandler(request, exc, traceback.format_exc())

        await asyncio.sleep(60)
