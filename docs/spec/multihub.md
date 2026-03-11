# Running Multiple Drivers Hubs

This is a technical documentation on the implementation of `multihub`.

For practical usage, run `main --help` for relevant command line arguments.

## Background

The server program was initially designed to run a single drivers hub under each instance, but as we started providing managed service to multiple communities, this became unsustainable due to the substantial RAM overhead for each instance. Most of the RAM was used to load duplicate libraries, and so the goal was to share the RAM so that each library is only loaded once.

Conventional multi-tenancy required a major refactor (i.e. updating almost all database queries), and so I opted to poke routing rules in FastAPI to load multiple drivers hub apps into one master app, and run them under one uvicorn instance.

This perserved the multi-database setup and saved server resources significantly, allowing efficient multi-tenancy without major refactor.

At the point this implementation was created, there was no online resource for such "load the same app multiple times but with different config/state" use case, and the only resources are for "load different sub-apps into one master-app". My implementation may be a hack-y solution, but it works and I have not found a better solution.

**Fun Fact**: This feature was added the night before I attended a competitive programming contest because I was bored with algorithm stuff.

## How it works?

When the main server program starts, it first creates a master-`app`.

Then, for each config file passed into the program, a sub-`app` is created for each drivers hub, then mounted into the master-`app`. The routes are identical inside each sub-`app`, but they live under the `prefix` space when they are mounted. The master-`app` is launched as a whole in `uvicorn`.

Note that there is no startup/shutdown events at sub-`app` level, and so when master-`app` receives a startup/shutdown event, it will iterate through all sub-`app`s and trigger the event for the sub-`app`.

For each API route, the `app` inside the `request` object uses the sub-`app`, rather than the master-`app`. This allows per-drivers-hub config and state to be preserved.

If master database is enabled, then the database is initialized when the master-`app` is created, and the database object is passed into each sub-`app`. This allows the master database connection pool to be shared, balancing connection use among popular and less popular drivers hubs.

See [/src/routing.py](/src/routing.py) for more information.
