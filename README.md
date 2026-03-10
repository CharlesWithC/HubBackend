# Drivers Hub: Backend

```text
    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_   
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \  
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /  
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/  

```

## Features

1. Custom routing mechanism to run multiple Drivers Hubs under one server instance.
2. Very-high level of customizability and a very-complex configuration file.
3. Custom security features on role-based authentication and rate limiting.
4. Advanced real-time summary + chart + aggregated/detailed statistics.
5. Advanced reward system with multiple customizable ranking structures and bonus points.
6. Support for multiple upstream trackers (Trucky, UniTracker, TrackSim, Custom).
7. Built-in + Discord notification system.
8. Support for user-level and drivers-hub-level localization.
9. Support for plugins and external plugins (i.e. build your own addon without poking this code base).

One main feature of this project is that I built a lot of *wheels* and strange stuff - partially for fun and partially because I did not look into using existing libraries. This is a legacy of competitive programming, as well as the project being started when I was in high school. However, this implies that I did some interesting custom optimizations, and that the overall project is relatively light-weight.

Also, despite this being a python project, it turns out the compiled binary runs suprisingly efficiently and uses relatively little memory. We were able to run more than 20 Drivers Hubs on a 1 vCPU / 1024MB RAM machine with reasonable response time. Typically the database is the bottleneck on low-spec servers.

See [drivershub.charlws.com](https://drivershub.charlws.com/) for details on user-facing features.

## The Philosophy

The backend was designed under an "open" philosophy, which means that it is supposed to work with any client, rather than a specific client. It is supposed to support the infrastructure of a general drivers hub service, in a stable and efficient way.

That said, the [frontend repo](https://github.com/CharlesWithC/HubFrontend) can be considered as a working demonstration of a web client. It does not utilize all features provided by the backend, and the backend does not provide convenient endpoints tailored to the frontend. Developers are encouraged to build their own client based on specific needs.

This philosophy led to a light code base, high-customizability and generalized features that conveniently satisfy the needs of multiple communities. Unfortunately, this prevented certain potentially-useful features from being added, as they were deemed to be against the philosophy (i.e. too community-specific, or overlapping with existing features). Requests to add such features will be rejected, and such features should be implemented with external plugins (see [/docs/extension.md](/docs/extension.md) for more information).

## Getting Started

### Prerequisite

- Python 3.12

- MariaDB 10.11.14

- Redis 8.0.2

**Note**: This documentation assumes a Ubuntu / Debian environment.

**Note**: Nuitka (<=4.0.3) only works with Python <=3.12 due to `asyncio` changes.

**Note**: If using MariaDB >= 11, you must configure `innodb-snapshot-isolation = 0` to prevent "Record has changed since last read in table 'X'" error. MariaDB 11 introduced stricter InnoDB snapshot isolation to ensure data consistency, but this is not required by the drivers hub, which assumes inconsistent data by design.

### Database Setup

```bash
mariadb -u root -p

# create user and database
MariaDB [(none)]> CREATE USER 'drivershub'@'localhost' IDENTIFIED BY '<password>';
MariaDB [(none)]> CREATE DATABASE drivershub;
MariaDB [(none)]> GRANT ALL ON drivershub.* TO 'drivershub'@'localhost';
MariaDB [(none)]> GRANT FILE ON *.* TO 'drivershub'@'localhost'; -- required for DATA DIRECTORY

# exit
MariaDB [(none)]> ^DBye
```

### Basic Configuration

Copy `config_sample.json` to `config.json`.

Configure at least the following fields (replace sample values):

```jsonc
{
    // 'abbr' and 'prefix' are used in multi-hub but required in single-hub as well
    // typically, it's recommended to use the same value (except for the leading '/')
    "abbr": "hub", // any alphanumeric string
    "prefix": "/api", // prefix of all API routes, must start with /
    
    "name": "The Drivers Hub Project (CHub)", // full company name

    // 'domain' is the domain where all API requests hit
    // it may be the same domain as the user-facing domain
    "domain": "drivershub.charlws.com", // hostname of API server

    "db_user": "drivershub", // database user
    "db_password": "<password>", // database password
    "db_name": "drivershub", // database name

    // keep all other fields from config_sample.json
}
```

See [/docs/config.jsonc](/docs/config.jsonc) for a commented version of the configuration file.

### Using Prebuilt Binary

```bash
# python is not needed (hooray)

# install curl and unzip
sudo apt install curl unzip

# download the prebuilt binary (requires glibc >= 2.38)
curl -L -o hub.zip https://github.com/CharlesWithC/HubBackend/releases/latest/download/hub.zip

# unzip the archive
unzip hub.zip -d ./hub/

# start the server
cd ./hub/
./main --config config.json

# in a separate shell, start bannergen
./bannergen
```

### Using Python Environment

```bash
# install git
sudo apt install git

# clone the repo
git clone https://github.com/CharlesWithC/HubBackend
cd ./HubBackend/

# create python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install python dependencies
pip3 install -r requirements.txt

# start the server
cd ./src/
python3 main.py --config config.json

# in a separate shell, start bannergen
cd ./bannergen/
python3 main.py
```

### Banner Generator

Banner Generator is not part of the main program and must be started separately. See [/docs/spec/bannergen.md](/docs/spec/bannergen.md) for more information on this design.

If `bannergen` is not started, `/member/banner` will return a `503` error.

You may also run `bannergen` on a separate server to offload computation and configure the main program to fetch banner from that server. See [/docs/usage/bannergen.md](/docs/usage/bannergen.md) for more information.

### Building with Nuitka

```bash
# install build dependencies
sudo apt install make gcc ccache patchelf p7zip-full

# install system dependencies
sudo apt install libmariadb-dev python3-simplejson python3-numpy python3-nacl python3-markupsafe

# build it
make -j
```

Building a python project may seem unusual, but this originates from the early times of the project where we had to host the program on servers managed by untrusted sources, where obfuscation from the binary format provided *some* protection.

The building mechanism was preserved because it arguably has *some* benefits to the performance, and it removes the need of a python runtime and environment when distributing the program.

**Note**: `gcc>=13` should be used. `gcc-12` may lead to broken error traceback information (i.e. missing source lines and frames).

## Resources

- [openapi.json](/openapi.json) provides full specification on the API
  - You may find the interactive version rendered by Swagger UI more helpful
  - You can load Swagger UI by setting `"openapi": true` in config and visiting `{prefix}/doc`
- [docs](/docs) contains some documentations about the history and the design principle and philosophy
  - And of course, some technical documentations on how things work
- [wiki.charlws.com](https://wiki.charlws.com/books/chub) provides some (possibly outdated) information on using the drivers hub

## License

This repository is licensed under the GNU Affero General Public License v3.0.  

Copyright &copy; 2022-2026 [CharlesWithC](https://charlws.com)  
