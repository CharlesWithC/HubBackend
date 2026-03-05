# Drivers Hub: Backend

```
    ____       _                         __  __      __  
   / __ \_____(_)   _____  __________   / / / /_  __/ /_   
  / / / / ___/ / | / / _ \/ ___/ ___/  / /_/ / / / / __ \  
 / /_/ / /  / /| |/ /  __/ /  (__  )  / __  / /_/ / /_/ /  
/_____/_/  /_/ |___/\___/_/  /____/  /_/ /_/\__,_/_.___/  

```

## Features

The main feature of this project is that I built a lot of *wheels* - partially for fun and partially because I did not look into using existing libraries. This is a legacy of competitive programming, as well as the project being started when I was in high school. However, this implies that I did some intersting custom optimizations, and the overall project being light-weight.

1. Custom routing mechanism to run multiple Drivers Hubs in one server process.
2. Very-high level of customizability and a very-complex configuration file.
3. Custom security features on role-based authentication and rate limiting.
4. Advanced real-time summary + chart + aggregated/detailed statistics.
5. Advanced reward system with multiple customizable ranking structures and bonus points.
6. Support for multiple upstream trackers (Trucky, UniTracker, TrackSim, Custom).
7. Built-in + Discord notification system.
8. Support for user-level and drivers-hub-level localization.
9. Support for plugins and external plugins (i.e. build your own addon without poking this code base).

See [drivershub.charlws.com](https://drivershub.charlws.com/) for details on user-facing features.

**NOTE**: This repo is undergoing *heavy* updates to include proper documentations.

## Getting Started

### Prerequisite

- Debian 13

- Python 3.13

- MariaDB 11.8.3

- Redis 5:8.0.2-3

### Configuration

> This part will be updated soon to include instruction on writing a minimal configuraion.

### Quick Start

```bash
# install system dependencies
sudo apt install unzip
sudo apt install libmariadb-dev python3-simplejson python3-numpy python3-nacl python3-markupsafe

# download the prebuilt binary (requires glibc >= 2.38)
curl -L -o hub.zip https://github.com/CharlesWithC/HubBackend/releases/latest/download/hub.zip

# unzip the archive
unzip hub.zip -d ./hub/

# start the server
cd hub/
./main --config config.json
```

### Full Setup

```bash
# clone the repo
git clone https://github.com/CharlesWithC/HubBackend
cd ./HubBackend/

# install system dependencies
sudo apt install libmariadb-dev python3-simplejson python3-numpy python3-nacl python3-markupsafe

# (optional) install dependencies for building binary with nuitka
sudo apt install gcc ccache patchelf

# create python virtual environment
python3 -m venv .venv
source .venv/bin/activate

# install python dependencies
pip3 install -r requirements.txt

# start the server
python3 main.py --config config.json
```

### Banner Generator

Banner Generator is not part of the main program and must be started separately. This mechanism prevents loading heavy dependencies such as `pillow` multiple times due to the design of the main program. Read [./docs/multihub.md](./docs/multihub.md) for more information.

```bash
# use prebuilt binary
./bannergen

# alternatively, run python code
cd ./bannergen/
python3 main.py
```

If `bannergen` is not started, `/member/banner` will return a `503` error.

You may also run `bannergen` on a separate server to offload computation and configure the main program to fetch banner from that server. See [./docs/bannergen.md](./docs/bannergen.md) for more information.

### Building with Nuitka

A `build.py` script is included to build the entire repo to binary with Nuitka.

```bash
python3 build.py [--rebuild] [--rebuild-main] [--rebuild-bannergen] [--rebuild-launcher]
```

It is apparently unusual to use a python script for building. It is planned to convert this to a Makefile.

## More Info?

See [openapi.json](./openapi.json) and [wiki](https://wiki.charlws.com/books/chub) for more technical info.

## License

This entire repository, including all commits and history, is licensed under the GNU Affero General Public License v3.0.  

Copyright &copy; 2022-2026 [CharlesWithC](https://charlws.com).  
