# Copyright (C) 2022 Charles All rights reserved.
# Author: @CharlesWithC

# A python version of build.sh with threading

import os, threading, time

def finalize():
    cmds = """mkdir build
cp main.dist/* build/ -r
cp bannergen/main.dist/* build/ -r
cp tracker.dist/* build/ -r
cp launcher.dist/* build/ -r
cp languages/ build/ -r
cp bannergen/fonts build/ -r
mkdir build/config
cp config_sample.json build/config/
cp apidoc.json build/""".split("\n")
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

threading.Thread(target = build_main, daemon = True).start()
time.sleep(1)
threading.Thread(target = build_tracker, daemon = True).start()
time.sleep(1)
threading.Thread(target = build_launcher, daemon = True).start()
time.sleep(1)
threading.Thread(target = build_bannergen, daemon = True).start()
time.sleep(1)
while 1:
    if done == 4:
        finalize()
        break
    time.sleep(1)