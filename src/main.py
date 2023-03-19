#!/usr/bin/python3

# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import sys
import threading
from datetime import datetime

import uvicorn

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

if not "HUB_CONFIG_FILE" in os.environ.keys() or os.environ["HUB_CONFIG_FILE"] == "":
    os.environ["HUB_CONFIG_FILE"] = config_path

from app import app, version, config
from db import genconn

for external_plugin in config.external_plugins:
    if not os.path.exists(f"./external_plugins/{external_plugin}.py"):
        print(f"Error: External plugin \"{external_plugin}\" not found, exited.")
        sys.exit(1)

if __name__ == "__main__":
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    print(drivershub)
    print(f"Drivers Hub: Backend ({version})")
    print(f"Copyright (C) {year} CharlesWithC All rights reserved.")

    import upgrades.manager
    cur_version = version.replace(".rc", "").replace(".", "_")
    pre_version = cur_version
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"SELECT sval FROM settings WHERE skey = 'version'")
    t = cur.fetchall()
    cur.close()
    conn.close()
    if len(t) != 0:
        pre_version = t[0][0].replace(".rc", "").replace(".", "_")
    if pre_version != cur_version:
        if not pre_version in upgrades.manager.VERSION_CHAIN:
            print(f"Previous version ({t[0][0]}) is not recognized. Aborted launch to prevent incompatability.")
            sys.exit(1)
        pre_idx = upgrades.manager.VERSION_CHAIN.index(pre_version)
        if not cur_version in upgrades.manager.VERSION_CHAIN:
            print(f"Current version ({version}) is not recognized. Aborted launch to prevent incompatability.")
            sys.exit(1)
        cur_idx = upgrades.manager.VERSION_CHAIN.index(cur_version)
        for i in range(pre_idx + 1, cur_idx + 1):
            v = upgrades.manager.VERSION_CHAIN[i]
            if v in upgrades.manager.UPGRADEABLE_VERSION:
                print(f"Updating data to be compatible with {v.replace('_', '.')}...")
                upgrades.manager.UPGRADER[v].run()
    upgrades.manager.unload()
        
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
    conn.commit()
    cur.close()
    conn.close()

from api import *

if __name__ == "__main__":
    print("")
    print(f"Company Name: {config.name}")
    print(f"Company Abbreviation: {config.abbr}")
    if len(config.enabled_plugins) != 0:
        print(f"Plugins: {', '.join(sorted(config.enabled_plugins))}")
    else:
        print(f"Plugins: /")
    if len(config.external_plugins) != 0:
        print(f"External Plugins: {', '.join(sorted(config.external_plugins))}")
    else:
        print("External Plugins: /")
    print("")

    os.system(f"rm -rf /tmp/hub/logo/{config.abbr}.png")
    os.system(f"rm -rf /tmp/hub/logo/{config.abbr}_bg.png")

    if "event" in config.enabled_plugins:
        from plugins.event import EventNotification
        threading.Thread(target = EventNotification, daemon = True).start()

    workers = 1
    try:
        workers = int(config.server_workers)
    except:
        pass
    
    uvicorn.run("app:app", host=config.server_ip, port=int(config.server_port), log_level="info", access_log=False, proxy_headers = True, workers = min(workers, 8))