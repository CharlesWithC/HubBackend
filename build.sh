cd src/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
cd bannergen/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
cd ..
nuitka3 tracker.py --standalone --include-package=websockets --show-progress --prefer-source-code
nuitka3 launcher.py --standalone --show-progress --prefer-source-code
rm -rf releases
mkdir releases
mv main.dist/main* main.dist/main
cp main.dist/* releases/ -r
mv bannergen/main.dist/main* bannergen/main.dist/bannergen
cp bannergen/main.dist/* releases/ -r
mv tracker.dist/tracker* tracker.dist/tracker
cp tracker.dist/* releases/ -r
mv launcher.dist/launcher* launcher.dist/launcher
cp launcher.dist/* releases/ -r
cp languages/ releases/ -r
cp bannergen/fonts releases/ -r
mkdir releases/config
cp ../config_sample.json releases/config/
cp ../openapi.json releases/
cd releases/
7z a hub.zip ./*
mv hub.zip ../