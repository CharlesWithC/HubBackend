# Drivers Hub: Backend

```text
    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_   
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \  
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /  
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/  

```

## Features

1. Custom routing mechanism to run multiple Drivers Hubs with one parent server process.
2. Very-high level of customizability and a very-complex configuration file.
3. Custom security features on role-based authentication and rate limiting.
4. Advanced real-time summary + chart + aggregated/detailed statistics.
5. Advanced reward system with multiple customizable ranking structures and bonus points.
6. Support for multiple upstream trackers (Trucky, UniTracker, TrackSim, Custom).
7. Built-in + Discord notification system.
8. Support for user-level and drivers-hub-level localization.
9. Support for plugins and external plugins (i.e. build your own addon without poking this code base).

One main feature of this project is that I built a lot of *wheels* - partially for fun and partially because I did not look into using existing libraries. This is a legacy of competitive programming, as well as the project being started when I was in high school. However, this implies that I did some intersting custom optimizations, and that the overall project is relatively light-weight.

Also, despite this being a python project, it turns out the compiled binary runs suprisingly efficiently and uses relatively low memory. We were able to run more than 20 Drivers Hubs on a 1 vCPU / 1024MB RAM server with reasonable response time. Typically the database is the bottleneck on low-spec servers.

See [drivershub.charlws.com](https://drivershub.charlws.com/) for details on user-facing features.

**NOTE**: This repo is undergoing *heavy* updates to include proper documentations.

## Getting Started

### Prerequisite

- Debian 13

- Python 3.13

- MariaDB 11.8.3

- Redis 5:8.0.2-3

**Note**: Technically, older system and software such as Debian 11 and MariaDB 10.11.14 are supported. However, current development uses above versions, and the prebuilt binaries are made to work with above versions. You may use `docker` / `podman` to create a container and setup the environment manually. In the future, we may provide a `docker-compose.yaml` file to setup the environment.

### Setup Database

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
    "prefix": "/hub", // prefix of all API routes, must start with /
    
    "name": "The Drivers Hub Project (CHub)", // full company name

    // 'domain' is the domain where all API requests hit
    // it may be the same domain as the user-facing domain
    "domain": "driverhsub.charlws.com", // hostname of API server

    "db_user": "drivershub", // database user
    "db_password": "<password>", // database password
    "db_name": "drivershub", // database name

    // keep all other fields from config_sample.json
}
```

The `config.json` file will be referenced below. You may have to copy it to the working directory or adjust the path.

See [docs/config.jsonc](./docs/config.jsonc) for detailed documentation on the configuration file.

### Quick Start

```bash
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

### Full Setup

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

Banner Generator is not part of the main program and must be started separately. This mechanism prevents loading heavy dependencies such as `pillow` multiple times due to the design of the main program. Read [docs/multihub.md](./docs/multihub.md) for more information.

If `bannergen` is not started, `/member/banner` will return a `503` error.

You may also run `bannergen` on a separate server to offload computation and configure the main program to fetch banner from that server. See [docs/bannergen.md](./docs/bannergen.md) for more information.

### Building with Nuitka

A `build.py` script is included to build the entire repo to binary with Nuitka.

```bash
# install build dependencies
sudo apt install gcc ccache patchelf p7zip

# install system dependencies
sudo apt install libmariadb-dev python3-simplejson python3-numpy python3-nacl python3-markupsafe

python3 build.py [--rebuild] [--rebuild-main] [--rebuild-bannergen] [--rebuild-launcher]
```

It is apparently unusual to use a python script for building. This will be converted to a Makefile.

## More Info?

See [openapi.json](./openapi.json) and [wiki](https://wiki.charlws.com/books/chub) for more technical info.

## License

This entire repository, including all commits and history, is licensed under the GNU Affero General Public License v3.0.  

Copyright &copy; 2022-2026 [CharlesWithC](https://charlws.com)  
