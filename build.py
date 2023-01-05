# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# A python version of build.sh with threading

import os, threading, time, sys

def finalize():
    cmds = """rm -rf ../build
mkdir ../build
cp main.dist/* ../build/ -r
cp bannergen/main.dist/* ../build/ -r
cp tracker.dist/* ../build/ -r
cp launcher.dist/* ../build/ -r
cp languages/ ../build/ -r
cp bannergen/fonts ../build/ -r
mkdir ../build/config
cp ../config_sample.json ../build/config/
cp ../openapi.json ../build/""".split("\n")
    for cmd in cmds:
        os.system(cmd)

done = 0

def build_main():
    os.system("nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code")
    global done
    done += 1

def build_bannergen():
    os.chdir("bannergen/")
    os.system("nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code")
    os.system("mv main.dist/main main.dist/bannergen")
    os.chdir("../")
    global done
    done += 1

def build_tracker():
    os.system("nuitka3 tracker.py --standalone --include-package=websockets --show-progress --prefer-source-code")
    global done
    done += 1

def build_launcher():
    os.system("nuitka3 launcher.py --standalone --show-progress --prefer-source-code")
    global done
    done += 1

req = 4
os.chdir("src")
if "--rebuild-main" in sys.argv and os.path.exists("main.dist") or not os.path.exists("main.dist"):
    threading.Thread(target = build_main, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped main")

if "--rebuild-tracker" in sys.argv and os.path.exists("tracker.dist") or not os.path.exists("tracker.dist"):
    threading.Thread(target = build_tracker, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped tracker")

if "--rebuild-launcher" in sys.argv and os.path.exists("launcher.dist") or not os.path.exists("launcher.dist"):
    threading.Thread(target = build_launcher, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped launcher")

if "--rebuild-bannergen" in sys.argv and os.path.exists("bannergen/main.dist") or not os.path.exists("bannergen/main.dist"):
    threading.Thread(target = build_bannergen, daemon = True).start()
    time.sleep(1)
else:
    req -= 1
    print("skipped bannergen")

while 1:
    if done == req:
        finalize()
        os.chdir("../build")
        os.system("7z a hub.zip ./*")
        os.system("mv hub.zip ../")
        break
    time.sleep(1)