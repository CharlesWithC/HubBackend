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

serdir = userbase + "/.local/share/systemd/user/"
pfi = hubbase + "/main.py"
fi = hubbase + "/main"
tpfi = hubbase + "/tracker.py"
tfi = hubbase + "/tracker"
cf = hubbase + "/configs"

args = sys.argv[1:]

if len(args) != 3:
    print("Usage: launcher <hub|tracker> <operation> <config>")
    sys.exit(1)
    
app = args[0]
op = args[1]
vtc = args[2]

if not os.path.exists(cf + "/" + vtc + ".json"):
    print("Config file not found")
    sys.exit(1)
conf = open(cf + "/" + vtc + ".json", "r").read()
conf = json.loads(conf)
vtcfull = conf["vtcname"]

if app == "hub":
    if op == "test": # python test
        os.system(f"systemctl --user stop hub{vtc}.service")
        os.chdir("/".join(pfi.split("/")[:-1]))
        os.system(f"python3 {pfi} {cf}/{vtc}.json")
        os.system(f"systemctl --user start hub{vtc}.service")

    elif op == "main": # executive file - should only be executed by systemctl
        os.chdir("/".join(fi.split("/")[:-1]))
        os.system(f"{fi} {cf}/{vtc}.json")

    elif op == "start":
        os.system(f"systemctl --user start hub{vtc}.service")

    elif op == "restart":
        os.system(f"systemctl --user restart hub{vtc}.service")

    elif op == "stop":
        os.system(f"systemctl --user stop hub{vtc}.service")

    elif op == "enable":
        os.system(f"rm -f {serdir}/hub{vtc}.service")
        open(f"{serdir}/hub{vtc}.service", "w").write(serconf.format(vtcfull, vtc))
        os.system(f"systemctl --user enable hub{vtc}.service")
    
    elif op == "disable":
        os.system(f"systemctl --user disable hub{vtc}.service")
        os.system(f"rm -f {serdir}/hub{vtc}.service")

    else:
        print("Unknown Service")

elif app == "tracker":
    if op == "test": # python test
        os.system(f"systemctl --user stop tracker{vtc}.service")
        os.chdir("/".join(tpfi.split("/")[:-1]))
        os.system(f"python3 {tpfi} {cf}/{vtc}.json")
        os.system(f"systemctl --user start tracker{vtc}.service")

    elif op == "main": # executive file - should only be executed by systemctl
        os.chdir("/".join(tfi.split("/")[:-1]))
        os.system(f"{tfi} {cf}/{vtc}.json")

    elif op == "start":
        os.system(f"systemctl --user start tracker{vtc}.service")

    elif op == "restart":
        os.system(f"systemctl --user start tracker{vtc}.service")

    elif op == "stop":
        os.system(f"systemctl --user stop tracker{vtc}.service")

    elif op == "enable":
        os.system(f"rm -f {serdir}/tracker{vtc}.service")
        open(f"{serdir}/tracker{vtc}.service", "w").write(traconf.format(vtcfull, vtc))
        os.system(f"systemctl --user enable tracker{vtc}.service")
    
    elif op == "disable":
        os.system(f"systemctl --user disable tracker{vtc}.service")
        os.system(f"rm -f {serdir}/tracker{vtc}.service")

    else:
        print("Unknown Service")

else:
    print("Unknown Application")