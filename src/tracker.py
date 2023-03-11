import asyncio
import json
import os
import sys
import time
import traceback
from datetime import datetime

import pymysql
from websockets import connect

drivershub = """    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_ 
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \\
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/ 
                                                         """

if len(sys.argv) == 1:
    print("Config file not specified")
    sys.exit(1)

config_path = ""
for argv in sys.argv:
    if argv.endswith(".json"): # prevent nuitka compilation adding unexpected parameters
        config_path = argv

if config_path == "" and "HUB_CONFIG_FILE" in os.environ.keys() and os.environ["HUB_CONFIG_FILE"] != "":
    config_path = os.environ["HUB_CONFIG_FILE"]

if config_path == "":
    print("Config file not specified")
    sys.exit(1)

if not os.path.exists(config_path):
    print("Config file not found")
    sys.exit(1)

class Dict2Obj(object):
    def __init__(self, d):
        for key in d:
            if type(d[key]) is dict:
                data = Dict2Obj(d[key])
                setattr(self, key, data)
            else:
                setattr(self, key, d[key])

config_txt = open(config_path, "r", encoding="utf-8").read()
config = json.loads(config_txt)
config = Dict2Obj(config)

host = config.mysql_host
user = config.mysql_user
passwd = config.mysql_passwd
dbname = config.mysql_db

def genconn():
    conn = pymysql.connect(host = host, user = user, passwd = passwd, db = dbname)
    cur = conn.cursor()
    cur.execute("SET session wait_timeout=10;")
    return conn

async def work(uri):
    lasthandshake = 0
    lastcommit = 0
    conn = genconn()
    cur = conn.cursor()
    async with connect(uri, ping_interval=30) as websocket:
        print(f"Company Name: {config.name}")
        print(f"Company Abbreviation: {config.abbr}")
        print(f"Tracker Company ID: {config.tracker_company_id}\n")
        await websocket.send(json.dumps({"op": 1, "data": {"subscribe_to_company": int(config.tracker_company_id)}}))
        data = await websocket.recv()
        lasthandshake = int(time.time())
        while True:
            data = await websocket.recv()
            data = json.loads(data)
            if data["type"] == "TELEMETRY_UPDATE":
                d = data["data"]
                steamid = d["driver"]
                game = d["game"]["id"]
                if game == "eut2":
                    game = 1
                elif game == "ats":
                    game = 2
                else:
                    game = 999
                x = int(d["truck"]["position"]["x"])
                y = int(d["truck"]["position"]["y"])
                z = int(d["truck"]["position"]["z"])
                mods = ""
                for mod in d["mods"]:
                    mods += mod["name"]
                mods = mods.lower()
                if mods.find("promod") != -1:
                    mods = "promod"
                elif mods.find("coast to coast") != -1:
                    mods = "coast to coast"
                else:
                    mods = ""
                if d["job"] is None:
                    # print(f"Received telemetry update for {steamid} in game {game} free roaming at {x}, {y}, {z}")
                    continue
                uuid = d["job"]["uuid"]
                # print(f"Received telemetry update for {steamid} in game {game} regarding job {uuid} at {x}, {y}, {z}")
                try:
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, '{uuid}', {game}, {x}, {y}, {z}, '{mods}', {int(time.time())})")
                except:
                    conn = genconn()
                    cur = conn.cursor()
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, '{uuid}', {game}, {x}, {y}, {z}, '{mods}', {int(time.time())})")
                    pass
            if int(time.time()) - lasthandshake >= 30:
                # print("Heartbeat")
                lasthandshake = int(time.time())
                await websocket.send(json.dumps({"op": 2}))
            if int(time.time()) - lastcommit >= 2:
                lastcommit = int(time.time())
                # print("Commit")
                conn.commit() # less commit
                if int(time.time()) - lasthandshake >= 20:
                    try:
                        cur.execute(f"DELETE FROM temptelemetry WHERE timestamp < {int(time.time() - 86400 * 3)}") # cache for 3 days
                        conn.commit()
                    except:
                        traceback.print_exc()
                try:
                    cur.close()
                    conn.close()
                except:
                    traceback.print_exc()

                conn = genconn()
                cur = conn.cursor()
            await asyncio.sleep(0.01)

if not "tracker" in config.enabled_plugins:
    print(f"Tracker not enabled for {config.name}")
    print("To enable, add 'tracker' in config.enabled_plugins")
    sys.exit(1)

if config.tracker_company_id == "":
    print("Tracker Company ID not set")
    sys.exit(1)

currentDateTime = datetime.now()
date = currentDateTime.date()
year = date.strftime("%Y")
print(drivershub)
print(f"Drivers Hub: Backend | Tracker")
print(f"Copyright (C) {year} CharlesWithC All rights reserved.")
print("")

while 1:
    try:
        if config.tracker == "tracksim":
            asyncio.run(work("wss://gateway.tracksim.app"))
        elif config.tracker == "navio":
            asyncio.run(work("wss://gateway.navio.app"))
    except:
        time.sleep(3)
        pass