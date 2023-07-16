# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import aiohttp
import requests


class arequests:
    async def get(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        exc = ConnectionResetError(f"Failed to GET {url}")
        for _ in range(3):
            try:
                if app is not None:
                    await app.db.extend_conn(dhrid, timeout + 2)
                async with aiohttp.ClientSession(trust_env = True) as session:
                    async with session.get(url, data = data, headers = headers, timeout = timeout) as resp:
                        r = requests.Response()
                        r.status_code = resp.status
                        r._content = await resp.content.read()
                        if app is not None:
                            await app.db.extend_conn(dhrid, 2)
                        return r
            except Exception as e:
                exc = e
                continue
        raise exc

    async def post(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        exc = ConnectionResetError(f"Failed to POST {url}")
        for _ in range(3):
            try:
                if app is not None:
                    await app.db.extend_conn(dhrid, timeout + 2)
                async with aiohttp.ClientSession(trust_env = True) as session:
                    async with session.post(url, data = data, headers = headers, timeout = timeout) as resp:
                        r = requests.Response()
                        r.status_code = resp.status
                        r._content = await resp.content.read()
                        if app is not None:
                            await app.db.extend_conn(dhrid, 2)
                        return r
            except Exception as e:
                exc = e
                continue
        raise exc

    async def patch(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        exc = ConnectionResetError(f"Failed to PATCH {url}")
        for _ in range(3):
            try:
                if app is not None:
                    await app.db.extend_conn(dhrid, timeout + 2)
                async with aiohttp.ClientSession(trust_env = True) as session:
                    async with session.patch(url, data = data, headers = headers, timeout = timeout) as resp:
                        r = requests.Response()
                        r.status_code = resp.status
                        r._content = await resp.content.read()
                        if app is not None:
                            await app.db.extend_conn(dhrid, 2)
                        return r
            except Exception as e:
                exc = e
                continue
        raise exc

    async def put(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        exc = ConnectionResetError(f"Failed to PUT {url}")
        for _ in range(3):
            try:
                if app is not None:
                    await app.db.extend_conn(dhrid, timeout + 2)
                async with aiohttp.ClientSession(trust_env = True) as session:
                    async with session.put(url, data = data, headers = headers, timeout = timeout) as resp:
                        r = requests.Response()
                        r.status_code = resp.status
                        r._content = await resp.content.read()
                        if app is not None:
                            await app.db.extend_conn(dhrid, 2)
                        return r
            except Exception as e:
                exc = e
                continue
        raise exc

    async def delete(app, url, data = None, headers = None, timeout = 10, dhrid = -1):
        exc = ConnectionResetError(f"Failed to DELETE {url}")
        for _ in range(3):
            try:
                if app is not None:
                    await app.db.extend_conn(dhrid, timeout + 2)
                async with aiohttp.ClientSession(trust_env = True) as session:
                    async with session.delete(url, data = data, headers = headers, timeout = timeout) as resp:
                        r = requests.Response()
                        r.status_code = resp.status
                        r._content = await resp.content.read()
                        if app is not None:
                            await app.db.extend_conn(dhrid, 2)
                        return r
            except Exception as e:
                exc = e
                continue
        raise exc
