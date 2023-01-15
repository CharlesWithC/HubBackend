cd src/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
cd bannergen/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
mv main.dist/main main.dist/bannergen
cd ..
nuitka3 tracker.py --standalone --include-package=websockets --show-progress --prefer-source-code
nuitka3 launcher.py --standalone --show-progress --prefer-source-code
rm -rf releases
mkdir releases
cp main.dist/* releases/ -r
cp bannergen/main.dist/* releases/ -r
cp tracker.dist/* releases/ -r
cp launcher.dist/* releases/ -r
cp languages/ releases/ -r
cp bannergen/fonts releases/ -r
mkdir releases/config
cp ../config_sample.json releases/config/
cp ../openapi.json releases/
cd releases/
7z a hub.zip ./*
mv hub.zip ../