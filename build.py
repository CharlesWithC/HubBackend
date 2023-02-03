# Copyright (C) 2023 CharlesWithC All rights reserved.
# Author: @CharlesWithC

# A python version of build.sh with threading

import os, threading, time, sys

def finalize():
    cmds = """rm -rf ../releases
mkdir ../releases
mv main.dist/main* main.dist/main
cp main.dist/* ../releases/ -r
mv bannergen/main.dist/main* bannergen/main.dist/bannergen
cp bannergen/main.dist/* ../releases/ -r
mv tracker.dist/tracker* tracker.dist/tracker
cp tracker.dist/* ../releases/ -r
mv launcher.dist/launcher* launcher.dist/launcher
cp launcher.dist/* ../releases/ -r
cp languages/ ../releases/ -r
cp bannergen/fonts ../releases/ -r
mkdir ../releases/config
cp ../config_sample.json ../releases/config/
cp ../openapi.json ../releases/""".split("\n")
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
        os.chdir("../releases")
        os.system("7z a hub.zip ./*")
        os.system("mv hub.zip ../")
        break
    time.sleep(1)