# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os

import uvicorn

from app import app # uvicorn / nuitka import

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
    print(f"Drivers Hub: Backend | Banner Generator")
    print(f"Copyright (C) {year} CharlesWithC All rights reserved.")
    print("")

    if not os.path.exists("/tmp/hub"):
        os.mkdir("/tmp/hub")
    if not os.path.exists("/tmp/hub/banner"):
        os.mkdir("/tmp/hub/banner")
    if not os.path.exists("/tmp/hub/logo"):
        os.mkdir("/tmp/hub/logo")
    if not os.path.exists("/tmp/hub/template"):
        os.mkdir("/tmp/hub/template")
    if not os.path.exists("/tmp/hub/avatar"):
        os.mkdir("/tmp/hub/avatar")
    uvicorn.run("app:app", host="127.0.0.1", port=8700, log_level="info", timeout_keep_alive=15)