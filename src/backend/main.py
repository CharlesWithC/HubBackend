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
from uvicorn import Config

from app import app, config
from db import newconn
import api

if __name__ == "__main__":
    print(f"{config.vtcname} Drivers Hub")
    uvicorn.run("app:app", host=config.server_ip, port=config.server_port, log_level="info", workers = 5)