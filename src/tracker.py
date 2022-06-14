import asyncio, json, time
from websockets import connect
from db import newconn
from app import config
import traceback
import time

async def navio(uri):
    lasthandshake = 0
    conn = newconn()
    cur = conn.cursor()
    async with connect(uri, ping_interval=30) as websocket:
        print(f"{config.vtcname} Tracker")
        print(f"Navio Company ID: {config.navio_company_id}")
        await websocket.send(json.dumps({"op": 1, "data": {"subscribe_to_company": config.navio_company_id}}))
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

while 1:
    try:
        asyncio.run(navio("wss://gateway.navio.app"))
    except:
        time.sleep(3)
        import traceback
        traceback.print_exc()
        pass