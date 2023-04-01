from app import app, config
from fastapi import FastAPI
from starlette.routing import Mount

multi_routes = [
    Mount(f"/{config.abbr}", app)
]
mpp = FastAPI(routes = multi_routes)