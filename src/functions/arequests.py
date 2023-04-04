# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import aiohttp
import requests


class arequests():
    async def get(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        await app.db.extend_conn(dhrid, timeout)
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.get(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.content.read()
                await app.db.extend_conn(dhrid, 1)
                return r

    async def post(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        await app.db.extend_conn(dhrid, timeout)
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.post(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.content.read()
                await app.db.extend_conn(dhrid, 1)
                return r

    async def patch(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        await app.db.extend_conn(dhrid, timeout)
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.patch(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.content.read()
                await app.db.extend_conn(dhrid, 1)
                return r
                
    async def put(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        await app.db.extend_conn(dhrid, timeout)
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.put(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.content.read()
                await app.db.extend_conn(dhrid, 1)
                return r
                
    async def delete(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        await app.db.extend_conn(dhrid, timeout)
        async with aiohttp.ClientSession(trust_env = True) as session:
            async with session.delete(url, data = data, headers = headers, timeout = timeout) as resp:
                r = requests.Response()
                r.status_code = resp.status
                r._content = await resp.content.read()
                await app.db.extend_conn(dhrid, 1)
                return r