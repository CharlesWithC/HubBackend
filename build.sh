mkdir build
nuitka3 main.py --standalone --onefile --include-package=websockets --show-progress --remove-output -o build/main
nuitka3 tracker.py --standalone --onefile --include-package=websockets --show-progress --remove-output -o build/tracker
nuitka3 launcher.py --standalone --onefile --include-package=websockets --show-progress --remove-output -o build/launcher
