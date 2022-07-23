#!/usr/bin/python3

# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import os, sys
import contextlib
import time
import threading
import uvicorn
import json
import asyncio

from sys import exit

drivershub = """    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_ 
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \\
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/ 
                                                         """
if __name__ == "__main__":
    from datetime import datetime
    currentDateTime = datetime.now()
    date = currentDateTime.date()
    year = date.strftime("%Y")
    print(drivershub)
    print("Drivers Hub: Backend (v1.10.1)")
    print(f"Copyright (C) {year} CharlesWithC All rights reserved.")
    print("")

if len(sys.argv) == 1:
    print("Usage: python3 main.py <config.json>")
    exit(1)

config_path = ""
for argv in sys.argv:
    if argv.endswith(".json"): # prevent nuitka compilation adding unexpected parameters
        config_path = argv

if config_path == "" and "HUB_CONFIG_FILE" in os.environ.keys() and os.environ["HUB_CONFIG_FILE"] != "":
    config_path = os.environ["HUB_CONFIG_FILE"]

if config_path == "":
    print("No config file specified")
    exit(1)

if not os.path.exists(config_path):
    print("Config file not found")
    exit(1)

if not "HUB_CONFIG_FILE" in os.environ.keys() or os.environ["HUB_CONFIG_FILE"] == "":
    print(f"Using config: {config_path}")
    os.environ["HUB_CONFIG_FILE"] = config_path
    print(f"Environment variable HUB_CONFIG_FILE set to {config_path}")
    print("")

from app import app, config
from db import newconn
import api
import multilang

if __name__ == "__main__":
    print(f"Company Name: {config.vtc_name}")
    print(f"Company Abbreviation: {config.vtc_abbr}")
    print("")
    time.sleep(1)
    uvicorn.run("app:app", host=config.server_ip, port=int(config.server_port), log_level="info", workers = 3)