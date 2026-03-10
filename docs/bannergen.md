# Banner Generator

This is a practical usage on the evolution of `bannergen`.

For technical documentation, see [/docs/spec/bannergen.md](/docs/spec/bannergen.md).

## Basic Setup

`bannergen` is self-contained, and so you may run `./bannergen` directly to launch the program.

`main` program is able to communicate with `bannergen` through the default port without extra configuration.

You may change the port with `--port=<new-port>` if there is a conflict. In that case, you have to use `--banner-service-url=http://127.0.0.1:<new-port>/banner` in `main` program to instruct it to use a different url.

## Advanced Setup

It is possible to run `bannergen` on a separate server, expose it through a private network, then use `--banner-service-url` in `main` program to connect `bannergen` to `main`.

However, this should be unnecessary since the latest version of `bannergen` is very resource-efficient, and should consume less resource than a normal database server.
