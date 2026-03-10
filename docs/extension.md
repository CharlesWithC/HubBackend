# Extension

The base drivers hub is mostly about the infrastructure, the job logging and user/member management. There are currently two methods to extend this base drivers hub: official plugin and external plugin.

Official plugins can be found under [/src/plugins](/src/plugins). They provide additional features that are the most popular. The plugins are mostly self-contained, i.e. the base drivers hub does not depend on them, and plugin X does not depend on plugin Y.

External plugins allow adding major features like official plugins, as well as tweaking existing functionalities with the help of middlewares. Some examples can be found in [/src/external_plugins](/src/external_plugins).

## Official Plugins

Announcement, Application, Banner, Challenge, Division, Downloads, Economy, Event, Poll, Route

Note that `banner` and `route` are two special plugins. The code is included in the base drivers hub, but they are designated as plugins so the functionalities can be enabled or disabled.

See [drivershub.charlws.com](https://drivershub.charlws.com/) for more information about these plugins.

## External Plugins

External plugins allow developers to:

- Override existing routes with custom logic
- Run custom background tasks
- Add middleware that is executed on every route
- Add middleware that processes requests sent to discord
- Add custom error handling logic

### Using External Plugin

To load an external plugin,

- Place the python file under `external_plugins` directory (if it does not exist, create this directory under the `main` program's directory)
- Add the name of the file to `external_plugins` in config (omit `.py` extension)

Note that external plugins would be loaded in the same order as listed in `config.external_plugins`.

### Building External Plugin

An external plugin may consist of multiple files, but there must be a standardized entry file, which would be loaded by the drivers hub.

The entry file must have an `init` function that takes `config: dict` and `print_log: bool = False` arguments

- `config` is the sanitized configuration in dictionary format
- `print_log` indicates whether the external plugin should enable logging during `init`
  - The drivers hub would ask `init` to print logs on first load, and surpress logs on subsequent loads
  - The plugin may be loaded multiple times due to using multiple workers processes with `uvicorn`

The `init` function should return `False` (if plugin cannot be initialized), or a four-item tuple of form `(True, routes, states, {middlewares})` (if plugin is initialized successfully). The return value should be consistent when the same arguments are passed into `init`. Otherwise, inconsistent behaviors may occur across worker processes. The drivers hub does not check if the return value is consistent.

#### Routes

`routes` is a list of `APIRoute` object, representing additional routes to load into the drivers hub.

```python
routes = [APIRoute("/", get_index, methods=["GET"], response_class=JSONResponse)]
```

If a route has the same path as a route provided by the drivers hub, or a route loaded by a previous external plugin, the new route will override the old route, i.e. the old route handling logic will be effectively dropped.

It is recommended to refer to existing code base on using authorization and rate limit APIs. However, some basic information is provided below.

```python
auth = await auth(authorization, request, allow_application_token = False, check_member = True, required_permission = ["admin", "driver"])`  
auth: {error: bool, discordid: int, userid: int, name: str, roles: list, application_token: bool}
```

```python
rl = await ratelimit(request, endpoint, limittime, limitcnt)
rl: (is_rate_limited: bool, JSONResponse | dict)
# The second item of the tuple is JSONResponse when rate limited. This response may be diretly returned.
# Otherwise, the second item is a dictionary containing current rate limit quota use for the user/IP.
```

#### States

Additional attributes may be initialized in `app.state`.

Note that additional states may always be set with `request.app` through middlewares (`request.app` exposes the `app` object).

```python
states = {"message": "External plugin loaded!"}
```

#### Middlewares

`middlewares` is a dictionary of `middleware_type: [middleware_function]`. The following middlewares are supported:

- Event: `startup`
- Request/Response: `request`, `response_ok`, `response_fail`
- Error handling: `error_handler`
- Discord request: `discord_request`

All middleware functions except `discord_request` may be either asynchronous or synchronous. `discord_request` must be synchronous, or the middleware will not be loaded.

All middleware functions should not raise any errors (i.e. they should catch all errors), otherwise they would cause 500 Internal Server Error. The errors would still be caught by the built-in error handler.

For convenience, if only one middleware function is to be loaded for a middleware type, the function does not need to be wrapped inside a list (i.e. use `type: func` rather than `type: [func]`).

In order to access the `app` object, use `request.app` if `request` object is provided. Otherwise, the middleware function may not access the `app` object.

For `startup(app: FastAPI)`, it is called when the drivers hub starts up. `app` includes states of the FastAPI application, as well as the drivers hub config (object `app.config`, or dictionary `app.config_dict`). The return value is ignored.

The `startup` middleware is typically used to create background tasks. For example,

```python
async def startup(app):
    loop = asyncio.get_event_loop()
    loop.create_task(BackgroundTask(app))
```

For `request(request: Request)`, it is called before all requests. Three types of return values are accepted:

- `None`: original request will be processed by the corresponding route handler
- `(new_request: Request, None)`: `new_request` will be processed by the corresponding route handler
- `(_, response: Response)`: `response` will be returned immediately and the original request will not be processed

If the middleware reads the content (e.g. with `await request.json()`) of a non-GET request, it must return a new request with the content stream restored. Otherwise, the content stream would be considered "consumed", and the route handler may not be able to read any data. *There used to be an example code on this, but it is unfortunately lost; If requests arise, I would provide a new example on restoring the request content.*

For `response_ok(request: Request, response: Response)` and `response_fail(request: Request, exception: Exception, traceback: str)`, it is called after a request completes. Two types of return values are accepted:

- `None`: original response will be returned
- `new_response: Response`: new response will be returned immediately and the original response will be dropped

Note that when multiple request/response middlewares are loaded, if any of them triggers an immediate return, then all subsequent middlewares will not run. The order that middlewares execute is based on the order that the external plugins are loaded (i.e. first external plugin has middlewares loaded first).

For `error_handler(request: Request, exception: Exception, traceback: str)`, it is called when an error occurs. Only the first `error_handler` loaded into the drivers hub (among possibly multiple error handlers from multiple plugins) would be considered. It must return `response: Response`, which would be sent to the user.

Note that `response_fail` and `error_handler` overlap in terms of triggering conditions, but `response_fail` is designed to be a route-specific response mechanism when something goes wrong, while `error_handler` is supposed to be an universal error catcher that replaces the default handler (which filters error, logs error and forwards error to discord).

For `discord_request(method: str, url: str, data: str|None)`, it is called before all discord api requests. It must return a dictionary containing possibly modified `data`. It should not modify the structure of `data` unless the modified structure is also accepted by the discord api endpoint. Currently, the middleware is not allowed to modify the `method` or `url`, but this may change in the near future.

Note that `data` may be `None` when no data is sent, and it should be preserved as is.

### Examples

Examples may be found in [/src/external_plugins](/src/external_plugins) directory.

[/src/external_plugins/example.py](/src/external_plugins/example.py) contains basic usage of all external plugin features.
