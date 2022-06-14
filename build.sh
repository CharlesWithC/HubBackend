nuitka3 main.py --standalone --onefile --include-package=websockets --show-progress --remove-output
mv main.bin main
nuitka3 tracker.py --standalone --onefile --include-package=websockets --show-progress --remove-output
mv tracker.bin tracker
nuitka3 run.py --standalone --onefile --include-package=websockets --show-progress --remove-output
mv run.bin run