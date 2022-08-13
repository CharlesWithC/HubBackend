nuitka3 main.py --standalone --include-package=websockets --show-progress --remove-output
cd bannergen/
nuitka3 main.py --standalone --include-package=websockets --show-progress --remove-output
mv main.dist/main main.dist/bannergen
cd ..
nuitka3 tracker.py --standalone --include-package=websockets --show-progress --remove-output
nuitka3 launcher.py --standalone --show-progress --remove-output
mkdir build
cp main.dist/* build/ -r
cp bannergen/main.dist/* build/ -r
cp tracker.dist/* build/ -r
cp launcher.dist/* build/ -r
cp languages/ build/ -r
cp bannergen/fonts build/ -r
mkdir build/config