#!/usr/bin/python3

# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

import os
import sys
import threading
import time

# create build folder and copy files
os.system("mkdir ./build")
os.chdir("./build")
os.system("cp -r ../src/* ./")

def finalize():
    cmds = """rm -rf ./binary
mkdir ./binary
mv main.dist/main* main.dist/main
cp main.dist/* ./binary/ -r
mv bannergen/main.dist/main* bannergen/main.dist/bannergen
cp bannergen/main.dist/* ./binary/ -r
mv launcher.dist/launcher* launcher.dist/launcher
cp launcher.dist/* ./binary/ -r
cp languages/ ./binary/ -r
cp bannergen/fonts ./binary/ -r
mkdir ./binary/config
cp ../config_sample.json ./binary/config/
cp ../openapi.json ./binary/""".split("\n")
    for cmd in cmds:
        os.system(cmd)

done = 0

def build_main():
    os.system("nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code")
    global done
    done += 1

def build_bannergen(does_build_main):
    if does_build_main:
        time.sleep(300)
    os.chdir("bannergen/")
    os.system("nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code")
    os.chdir("../")
    global done
    done += 1

def build_launcher():
    os.system("nuitka3 launcher.py --standalone --show-progress --prefer-source-code")
    global done
    done += 1

req = 3
if "--rebuild" in sys.argv:
    sys.argv.append("--rebuild-main")
    sys.argv.append("--rebuild-bannergen")
    sys.argv.append("--rebuild-launcher")

does_build_main = False
if "--rebuild-main" in sys.argv and os.path.exists("main.dist") or not os.path.exists("main.dist"):
    does_build_main = True
    threading.Thread(target = build_main, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped main")

if "--rebuild-bannergen" in sys.argv and os.path.exists("bannergen/main.dist") or not os.path.exists("bannergen/main.dist"):
    threading.Thread(target = build_bannergen, args=(does_build_main,), daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped bannergen")

if "--rebuild-launcher" in sys.argv and os.path.exists("launcher.dist") or not os.path.exists("launcher.dist"):
    threading.Thread(target = build_launcher, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped launcher")

while 1:
    if done == req:
        finalize()
        os.chdir("./binary")
        os.system("7z a hub.zip ./*")
        os.chdir("../../releases")
        os.system("mv ../build/binary/hub.zip ./hub.zip")
        break
    time.sleep(1)
