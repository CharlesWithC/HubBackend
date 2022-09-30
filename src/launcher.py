#!/usr/bin/python3

# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

import os, sys, json

userbase = os.path.expanduser('~')
hubbase = os.path.expanduser('~') + "/hub"
serconf = """[Unit]
Description={} Drivers Hub
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=60
ExecStart="""+hubbase+"""/launcher hub main {}

[Install]
WantedBy=default.target"""

traconf = """[Unit]
Description={} Tracker
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=60
ExecStart="""+hubbase+"""/launcher tracker main {}

[Install]
WantedBy=default.target"""

# bannergen might stuck randomly so restart every 30 minutes
bgenconf = """[Unit]
Description=Drivers Hub Banner Generator
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=5
RuntimeMaxSec=1800s
ExecStart="""+hubbase+"""/launcher bannergen main

[Install]
WantedBy=default.target"""

serdir = userbase + "/.local/share/systemd/user/"
pfi = hubbase + "/main.py"
fi = hubbase + "/main"
tpfi = hubbase + "/tracker.py"
tfi = hubbase + "/tracker"
bfi = hubbase + "/bannergen"
cf = hubbase + "/config"

args = sys.argv[1:]

if len(args) != 3 and len(args) != 2:
    print("Usage: launcher <hub|tracker|bannergen> <test|main|start|restart|stop|enable|disable> <abbr>")
    sys.exit(1)
    
app = args[0]
op = args[1]
if app == "bannergen":
    if op == "main": # executive file - should only be executed by systemctl
        os.chdir("/".join(bfi.split("/")[:-1]))
        os.system(f"{bfi}")

    elif op == "start":
        os.system(f"systemctl --user start bannergen.service")

    elif op == "restart":
        os.system(f"systemctl --user start bannergen.service")

    elif op == "stop":
        os.system(f"systemctl --user stop bannergen.service")

    elif op == "enable":
        os.system(f"rm -f {serdir}/bannergen.service")
        open(f"{serdir}/bannergen.service", "w").write(bgenconf)
        os.system(f"systemctl --user enable bannergen.service")
    
    elif op == "disable":
        os.system(f"systemctl --user disable bannergen.service")
        os.system(f"rm -f {serdir}/bannergen.service")
        os.system(f"systemctl --user daemon-reload")

    sys.exit(0)
    
if len(args) != 3:
    print("Usage: launcher <hub|tracker|bannergen> <test|main|start|restart|stop|enable|disable> <abbr>")
    sys.exit(1)
abbr = args[2]

if not os.path.exists(cf + "/" + abbr + ".json"):
    print("Config file not found")
    sys.exit(1)
conf = open(cf + "/" + abbr + ".json", "r").read()
conf = json.loads(conf)
name = conf["name"]

if app == "hub":
    if op == "test": # python test
        os.system(f"systemctl --user stop hub{abbr}.service")
        os.chdir("/".join(pfi.split("/")[:-1]))
        os.system(f"python3 {pfi} {cf}/{abbr}.json")
        os.system(f"systemctl --user start hub{abbr}.service")

    elif op == "main": # executive file - should only be executed by systemctl
        os.chdir("/".join(fi.split("/")[:-1]))
        os.system(f"{fi} {cf}/{abbr}.json")

    elif op == "start":
        os.system(f"systemctl --user start hub{abbr}.service")

    elif op == "restart":
        os.system(f"systemctl --user restart hub{abbr}.service")

    elif op == "stop":
        os.system(f"systemctl --user stop hub{abbr}.service")

    elif op == "enable":
        os.system(f"rm -f {serdir}/hub{abbr}.service")
        open(f"{serdir}/hub{abbr}.service", "w").write(serconf.format(name, abbr))
        os.system(f"systemctl --user enable hub{abbr}.service")
    
    elif op == "disable":
        os.system(f"systemctl --user disable hub{abbr}.service")
        os.system(f"rm -f {serdir}/hub{abbr}.service")
        os.system(f"systemctl --user daemon-reload")

    else:
        print("Unknown verb")

elif app == "tracker":
    if op == "test": # python test
        os.system(f"systemctl --user stop tracker{abbr}.service")
        os.chdir("/".join(tpfi.split("/")[:-1]))
        os.system(f"python3 {tpfi} {cf}/{abbr}.json")
        os.system(f"systemctl --user start tracker{abbr}.service")

    elif op == "main": # executive file - should only be executed by systemctl
        os.chdir("/".join(tfi.split("/")[:-1]))
        os.system(f"{tfi} {cf}/{abbr}.json")

    elif op == "start":
        os.system(f"systemctl --user start tracker{abbr}.service")

    elif op == "restart":
        os.system(f"systemctl --user start tracker{abbr}.service")

    elif op == "stop":
        os.system(f"systemctl --user stop tracker{abbr}.service")

    elif op == "enable":
        os.system(f"rm -f {serdir}/tracker{abbr}.service")
        open(f"{serdir}/tracker{abbr}.service", "w").write(traconf.format(name, abbr))
        os.system(f"systemctl --user enable tracker{abbr}.service")
    
    elif op == "disable":
        os.system(f"systemctl --user disable tracker{abbr}.service")
        os.system(f"rm -f {serdir}/tracker{abbr}.service")
        os.system(f"systemctl --user daemon-reload")

    else:
        print("Unknown verb")

else:
    print("Unknown Application")