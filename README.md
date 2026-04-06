# Drivers Hub: Backend

```text
    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_   
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \  
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /  
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/  

```

An advanced Drivers Hub solution for Euro Truck Simulator 2 / American Truck Simulator VTCs.

## Features

1. Very high level of customizability and a very complex [configuration file](/docs/config.jsonc).
2. Custom routing mechanism to run multiple Drivers Hubs under one server instance.
3. Custom security features including role-based authentication and rate limiting.
4. Advanced real-time summary + chart + aggregated/detailed statistics.
5. Advanced reward system with multiple customizable ranking structures and bonus points.
6. Support for multiple upstream trackers (Trucky, UniTracker, TrackSim, Custom).
7. Support for built-in and Discord notification system.
8. Support for user-level and drivers-hub-level localization.
9. Support for [plugins](/docs/plugins.md) and [external plugins](/docs/extension.md) (i.e. build your own addon without poking this codebase).

One main feature of this project is that I built a lot of *wheels* and strange stuff - partially for fun and partially because I did not look into using existing libraries. This is a legacy of competitive programming, as well as the project being started when I was in high school. However, this implies that I did some interesting custom optimizations, and that the overall project is relatively lightweight.

Also, despite this being a python project, it turns out the compiled binary runs surprisingly efficiently and uses relatively little memory. We were able to run more than 20 Drivers Hubs on a 1 vCPU / 1024MB RAM machine with reasonable response time. Typically the database is the bottleneck on low-spec servers.

See [drivershub.charlws.com](https://drivershub.charlws.com/) for details on user-facing features.

## The Philosophy

The backend was designed under an "open" philosophy, which means that it is supposed to work with any client, rather than a specific client. It is supposed to support the infrastructure of a general drivers hub service, in a stable and efficient way.

That said, the [frontend repo](https://github.com/CharlesWithC/HubFrontend) can be considered as a working demonstration of a web client. It does not utilize all features provided by the backend, and the backend does not provide convenient endpoints tailored to the frontend. Developers are encouraged to build their own client based on specific needs.

This philosophy led to a lightweight codebase, high-customizability and generalized features that conveniently satisfy the needs of multiple communities. Unfortunately, this prevented certain potentially useful features from being added, as they were deemed to be against the philosophy (i.e. too community-specific, or overlapping with existing features). Requests to add such features will be rejected, and such features should be implemented with external plugins (see [/docs/extension.md](/docs/extension.md) for more information).

## Getting Started

### Prerequisite

- Python 3.12

- MariaDB 10.11.14

- Redis 8.0.2

**Note**: This documentation assumes a Ubuntu / Debian environment.

**Note**: Nuitka (<=4.0.x) only works with Python <=3.12 due to `asyncio` changes.

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

Configure **at least** the following fields (replace sample values):

```jsonc
{
    // IMPORTANT: YOU MUST DERIVE THE CONFIG FROM config_sample.json
    //            OTHERWISE THE SERVER MAY REFUSE TO LAUNCH
    //            THE KEYS BELOW DO NOT MAKE UP A FULL VALID CONFIG

    // 'abbr' and 'prefix' are used in multi-hub but required in single-hub as well
    // typically, it's recommended to use the same value (except for the leading '/')
    "abbr": "mycommunity", // any alphanumeric string
    "prefix": "/api", // prefix of all API routes, must start with /
    
    "name": "My Community", // full community name

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

# install curl
sudo apt install curl

# download the prebuilt binary (requires glibc >= 2.41)
curl -L -o drivershub.tar.gz https://github.com/CharlesWithC/HubBackend/releases/latest/download/drivershub.tar.gz

# extract the archive
mkdir -p ./drivershub/
tar -xzf drivershub.tar.gz -C ./drivershub/

cd ./drivershub/
# initialize database
./main --config config.json setup init-db
# start the server
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

cd ./src/
# initialize database
python3 main.py --config config.json setup init-db
# start the server
python3 main.py --config config.json

# in a separate shell, start bannergen
cd ./bannergen/
python3 main.py
```

### Creating a User

A few helpful commands are provided to setup an administrator account.

We create a user with `administrator` permission assuming the role with ID `1` has `administrator` permission.

Note that if such role does not exist in the configuration, a role with `administrator` permission should be configured first.

```bash
# create a new user
./main --config config.json setup create-user <email>
Enter password: 
Created user with UID 77.

# accept the user
./main --config config.json setup accept-user 77
Accepted user 77 as member with user id 42.

# update roles
./main --config config.json setup update-roles 42 1
Updated user 42 roles to [1].
```

You will be able to login as administrator with the credentials used above.

## Building with Nuitka

```bash
# (optional) start a podman container
podman run -it \
    -v $(pwd)/src:/hubbackend/src:ro,z \
    -v $(pwd)/requirements.txt:/hubbackend/requirements.txt:ro,z \
    -v $(pwd)/makefile:/hubbackend/makefile:ro,z \
    -v $(pwd)/config_sample.json:/hubbackend/config_sample.json:ro,z \
    -v $(pwd)/openapi.json:/hubbackend/openapi.json:ro,z \
    -v $(pwd)/build:/hubbackend/build:rw,z \
    -v $(pwd)/dist:/hubbackend/dist:rw,z \
    -v $(pwd)/releases:/hubbackend/releases:rw,z \
    -w /hubbackend \
    --name hubbackend \
    python:3.12-trixie /bin/bash

# install make
apt update && apt install -y make

# install dependencies
make install

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
- [docs](/docs) contains some documentation about the history and the design principle and philosophy
  - And of course, some technical documentation on how things work
  - You may want to start from [/docs/guide.md](/docs/guide.md) for some high-level information on using the Drivers Hub.
- [wiki](https://github.com/CharlesWithC/HubWebsite/wiki) provides some information on using the drivers hub

## License

This repository is licensed under the GNU Affero General Public License v3.0.

Copyright &copy; 2022-2026 [CharlesWithC](https://charlws.com)

<img src="https://drivershub.charlws.com/images/banner.webp" height="80" alt="Logo"> 
