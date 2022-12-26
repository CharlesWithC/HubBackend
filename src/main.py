#!/usr/bin/python3

# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import os, sys, time, json, threading
import uvicorn
import traceback

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

from app import app, config, version
from db import genconn
import multilang

for external_plugin in config.external_plugins:
    if not os.path.exists(f"./external_plugins/{external_plugin}.py"):
        print(f"Error: External plugin \"{external_plugin}\" not found, exited.")
        sys.exit(1)

if __name__ == "__main__":
    from datetime import datetime
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    print(drivershub)
    print(f"Drivers Hub: Backend ({version})")
    print(f"Copyright (C) {year} CharlesWithC All rights reserved.")

    if "upgrade" in sys.argv:
        print("")
        if os.path.exists(f"./upgrade.py"):
            print("Detected upgrade")
            import upgrade
            try:
                if upgrade.target_version == version or upgrade.target_version + ".rc" == version:
                    upgrade.run()
                    print("Upgrade completed")
                else:
                    print("Version mismatch, aborted")
            except:
                traceback.print_exc()
                print("Upgrade failed due to errors above, main program exited")
                sys.exit(1)
        else:
            print("Upgrade failed due to upgrade.py not found.")
            sys.exit(1)
        
    conn = genconn()
    cur = conn.cursor()
    cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
    conn.commit()
    cur.close()
    conn.close()

import api
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