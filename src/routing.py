# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

from fastapi import FastAPI
from starlette.routing import Mount
import os

import app as base

routes = [
    Mount(f"/{base.app.config.abbr}", base.app)
]
app = FastAPI(routes = routes)

# gracefully stops all async tasks
@app.on_event("shutdown")
def shutdownEvent():
    os._exit(42)