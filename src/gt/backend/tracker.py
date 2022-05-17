import asyncio, json, time
from websockets import connect
from db import newconn
import traceback
import time

async def navio(uri):
    lasthandshake = 0
    conn = newconn()
    cur = conn.cursor()
    async with connect(uri, ping_interval=30) as websocket:
        await websocket.send(json.dumps({"op": 1, "data": {"subscribe_to_company": 72}}))
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
                x = round(d["truck"]["position"]["x"],2)
                y = round(d["truck"]["position"]["y"],2)
                z = round(d["truck"]["position"]["z"],2)
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
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, -1, '{uuid}', '{game}', {x}, {y}, {z}, '{mods}', {int(time.time())})")
                except:
                    traceback.print_exc()
                    conn = newconn()
                    cur.execute(f"INSERT INTO temptelemetry VALUES ({steamid}, -1, '{uuid}', '{game}', {x}, {y}, {z}, '{mods}', {int(time.time())})")
                    pass
            if int(time.time()) - lasthandshake >= 30:
                print("Heartbeat")
                await websocket.send(json.dumps({"op": 2}))
                lasthandshake = int(time.time())
                cur.execute(f"DELETE FROM temptelemetry WHERE timestamp < {int(time.time() - 86400 * 7)}") # cache for one week
                conn.commit() # less commit
            await asyncio.sleep(0.01)

while 1:
    try:
        asyncio.run(navio("wss://gateway.navio.app"))
    except:
        time.sleep(3)
        import traceback
        traceback.print_exc()
        pass