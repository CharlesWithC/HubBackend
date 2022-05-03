#!/usr/bin/python3

# Copyright (C) 2021 Charles All rights reserved.
# Author: @Charles-1414

import os, sys
import uvicorn
import json

from app import app, config
from db import newconn
import api

if __name__ == "__main__":
    print("DriversHub For At The Mile Logistics v1.0 by Charles")
    uvicorn.run("app:app", host = config.server_ip, port = config.server_port)