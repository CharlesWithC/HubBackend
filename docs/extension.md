# Extension

This will be an extensive documentation on building addons on the Drivers Hub.

It is currently a placeholder with the below sections copied from the old README.

## Official Plugins

Announcement, Application, Banner, Challenge, Division, Downloads, Economy, Event, Poll, Route  
See [the website](https://drivershub.charlws.com) for more information about these plugins.

## External Plugins

External plugins can add new routes and background tasks to the existing app. It may also modify existing routes by using the same route path.  
To use an external plugin, place the `.py` file in `./external_plugins` folder, add the name of the file to `config.external_plugins` and it'll be automatically loaded.  
To create an external plugin, create a `.py` with `init` function and some route functions. The `init` function must take `config: dict` and `print_log: bool = False` (log should only be written when `print_log = True`) as the only arguments (`def init(app, print_log = False)`) and return `(True, routes: list, states: dict, middlewares: dict)`, or `False` if plugin should not be loaded. It will be called when the plugin is loaded.  
Regarding `middlewares`, it must be a dict with keys no other than `startup`, `request`, `response_ok`, `response_fail`, `error_handler`, `discord_request` (not all keys must be provided), the value for each key should either be a callable function or a list of multiple callable functions. The function(s) will be called by the default middleware.  
-> For `startup` middleware, `app` will be passed.  
-> For `request` middleware, `request` will be passed. It must return either `None` or a tuple of `(request, response)`. `response` in the tuple may be `None` or a valid response, and if a valid `Response` is provided, it will be returned directly without further processing the request. `request` must be a valid request object with `await request.body()` able to return the valid request body. (NOTE: Due to streaming requests, the body may be only readable the first time it is accessed, and the `request` object must be modified to be able to return valid body data.)  
-> For `response_ok` middleware, `request` and `response` will be passed. It must return either `None` or a valid `Response`.  
-> For `response_fail` middleware, `request`, `exception` and `traceback` will be passed. It must return either `None` or a valid `Response`.  
-> For `error_handler` handler, `request`, `exception` and `traceback` will be passed. It must return a valid `Response`. If another exception occurs in the handler, the app will fall back to use default error handler. Also, there must be only one `error_handler` when loading external plugins, otherwise only the first one will be loaded.  
-> For `discord_request` handler, `method`, `url` and `data` will be passed. It must return a valid `data` which will be sent to Discord API. Note that the `data` may be `None` for certain requests (e.g. update member roles) and it should not be modified.  
**Note** To get the `app` when it's not passed directly, use `request.app`. Exceptions should be handled by the middleware, otherwise they will lead to `500` responses.  
Reference: [example.py](./src/external_plugins/example.py)  

## Security API

1.Authorization  
`await auth(authorization, request, allow_application_token = False, check_member = True, required_permission = ["admin", "driver"])`  
returns `{error: bool, discordid: int, userid: int, name: str, roles: list, application_token: bool}`  
2.Rate limit  
`await ratelimit(request, endpoint, limittime, limitcnt)`  
When rate limited, returns `(True, JSONResponse)`  
When not rate limited, returns `(False, resp_headers: dict)`  
