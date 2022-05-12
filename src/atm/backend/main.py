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

# @bot.event
# async def on_ready():
#     print(f"[Discord Bot] Logged in as {bot.user} (ID: {bot.user.id})")

# class Server(uvicorn.Server):
#     def install_signal_handlers(self):
#         pass

#     @contextlib.contextmanager
#     def run_in_thread(self):
#         thread = threading.Thread(target=self.run)
#         thread.start()
#         try:
#             while not self.started:
#                 time.sleep(1e-3)
#             yield
#         finally:
#             self.should_exit = True
#             thread.join()

# print("DriversHub For At The Mile Logistics v1.0 by Charles")
# sconfig = Config("app:app", host=config.server_ip, port=config.server_port, log_level="info")
# server = Server(config=sconfig)
# with server.run_in_thread():
#     bot.run(config.bottoken)

uvicorn.run("app:app", host=config.server_ip, port=config.server_port, log_level="info")