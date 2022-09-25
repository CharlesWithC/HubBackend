#!/usr/bin/python3

# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import os, sys, time, json
import uvicorn

drivershub = """    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_ 
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \\
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/ 
                                                         """

if len(sys.argv) == 1:
    print("You must specify a config file")
    sys.exit(1)

config_path = ""
for argv in sys.argv:
    if argv.endswith(".json"): # prevent nuitka compilation adding unexpected parameters
        config_path = argv

if config_path == "" and "HUB_CONFIG_FILE" in os.environ.keys() and os.environ["HUB_CONFIG_FILE"] != "":
    config_path = os.environ["HUB_CONFIG_FILE"]

if config_path == "":
    print("You must specify a config file")
    sys.exit(1)

if not os.path.exists(config_path):
    print("Config file not found")
    sys.exit(1)

if not "HUB_CONFIG_FILE" in os.environ.keys() or os.environ["HUB_CONFIG_FILE"] == "":
    os.environ["HUB_CONFIG_FILE"] = config_path

from app import app, config, version
from db import newconn
import api
import multilang

if __name__ == "__main__":
    from datetime import datetime
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    print(drivershub)
    print(f"Drivers Hub: Backend ({version})")
    print(f"Copyright (C) {year} CharlesWithC All rights reserved.")
    print("")

    if os.path.exists(f"./upgrade.py"):
        print("Detected upgrade")
        import upgrade
        try:
            if upgrade.target_version == version or upgrade.target_version + ".rc" == version:
                upgrade.run()
                print("Upgrade completed\n")
            else:
                print("Version mismatch, aborted\n")
        except:
            import traceback
            traceback.print_exc()
            print("Upgrade failed due to errors above, main program exited")
            sys.exit(1)
    
    conn = newconn()
    cur = conn.cursor()
    cur.execute(f"UPDATE settings SET sval = '{version}' WHERE skey = 'version'")
    conn.commit()

    print(f"Company Name: {config.vtc_name}")
    print(f"Company Abbreviation: {config.vtc_abbr}\n")
    os.system(f"rm -rf /tmp/hub/logo/{config.vtc_abbr}.png")
    os.system(f"rm -rf /tmp/hub/logo/{config.vtc_abbr}_bg.png")
    if not version.endswith(".rc"):
        time.sleep(1)
    uvicorn.run("app:app", host=config.server_ip, port=int(config.server_port), log_level="info", workers = int(config.server_workers))