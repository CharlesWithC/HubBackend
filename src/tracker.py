import asyncio, json, time, os, sys
from websockets import connect
import traceback
import time

from sys import exit

drivershub = """    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_ 
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \\
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/ 
                                                         """

if len(sys.argv) == 1:
    print("You must specify a config file")
    exit(1)

config_path = ""
for argv in sys.argv:
    if argv.endswith(".json"): # prevent nuitka compilation adding unexpected parameters
        config_path = argv

if config_path == "" and "HUB_CONFIG_FILE" in os.environ.keys() and os.environ["HUB_CONFIG_FILE"] != "":
    config_path = os.environ["HUB_CONFIG_FILE"]

if config_path == "":
    print("You must specify a config file")
    exit(1)

if not os.path.exists(config_path):
    print("Config file not found")
    exit(1)

os.environ["HUB_CONFIG_FILE"] = config_path

from db import newconn
from app import config, version

async def work(uri):
    lasthandshake = 0
    conn = newconn()
    cur = conn.cursor()
    async with connect(uri, ping_interval=30) as websocket:
        print(f"Company Name: {config.vtc_name}")
        print(f"Company Abbreviation: {config.vtc_abbr}")
        print(f"Navio Company ID: {config.navio_company_id}\n")
        await websocket.send(json.dumps({"op": 1, "data": {"subscribe_to_company": int(config.navio_company_id)}}))
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
                    print(f"Received telemetry update for {steamid} in game {game} free roaming at {x}, {y}, {z}")
                    continue
                uuid = d["job"]["uuid"]
                print(f"Received telemetry update for {steamid} in game {game} regarding job {uuid} at {x}, {y}, {z}")
                try:
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, '{uuid}', {game}, {x}, {y}, {z}, '{mods}', {int(time.time())})")
                except:
                    traceback.print_exc()
                    conn = newconn()
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, '{uuid}', {game}, {x}, {y}, {z}, '{mods}', {int(time.time())})")
                    pass
            if int(time.time()) - lasthandshake >= 30:
                print("Commit")
                conn.commit() # less commit
                conn = newconn()
                cur = conn.cursor()
                print("Heartbeat")
                await websocket.send(json.dumps({"op": 2}))
                lasthandshake = int(time.time())
                try:
                    cur.execute(f"DELETE FROM temptelemetry WHERE timestamp < {int(time.time() - 86400 * 7)}") # cache for one week
                except:
                    traceback.print_exc()
            await asyncio.sleep(0.01)

if not "tracker" in config.enabled_plugins:
    print(f"Tracker not enabled for {config.vtc_name}")
    print("To enable, add 'tracker' in config.enabled_plugins")
    exit(1)

if config.navio_company_id == "":
    print("Navio Company ID not set")
    exit(1)

from datetime import datetime
currentDateTime = datetime.now()
date = currentDateTime.date()
year = date.strftime("%Y")
print(drivershub)
print(f"Drivers Hub: Backend ({version}) | Tracker")
print(f"Copyright (C) {year} CharlesWithC All rights reserved.")
print("")

while 1:
    try:
        asyncio.run(work("wss://gateway.navio.app"))
    except:
        time.sleep(3)
        import traceback
        traceback.print_exc()
        pass