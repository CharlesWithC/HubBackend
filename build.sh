cd src/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
cd bannergen/
nuitka3 main.py --standalone --include-package=websockets --show-progress --prefer-source-code
mv main.dist/main main.dist/bannergen
cd ..
nuitka3 tracker.py --standalone --include-package=websockets --show-progress --prefer-source-code
nuitka3 launcher.py --standalone --show-progress --prefer-source-code
rm -rf build
mkdir build
cp main.dist/* build/ -r
cp bannergen/main.dist/* build/ -r
cp tracker.dist/* build/ -r
cp launcher.dist/* build/ -r
cp languages/ build/ -r
cp bannergen/fonts build/ -r
mkdir build/config
cp ../config_sample.json build/config/
cp ../openapi.json build/
cd build/
7z a hub.zip ./*
mv hub.zip ../