DEPS_MAIN := $(shell find src/ -type f -not -path "src/bannergen/*" -not -path "src/languages/*" -not -path "src/launcher.py")
DEPS_BANNERGEN := $(shell find src/bannergen/ -type f)
DEPS_LAUNCHER := src/launcher.py

BUILD_DIR := build
DIST_DIR := dist
RELEASE_DIR := releases

.PHONY: release build clean

release: build
	cd $(DIST_DIR); \
	7z a hub.zip *; \
	cd ..; \
	mkdir -p $(RELEASE_DIR); \
	mv $(DIST_DIR)/hub.zip $(RELEASE_DIR)/

build: $(DIST_DIR)/main $(DIST_DIR)/bannergen $(DIST_DIR)/launcher
	cp -r src/languages/ $(DIST_DIR)/languages/; \
	cp -r src/bannergen/fonts $(DIST_DIR)/fonts/; \
	mkdir -p $(DIST_DIR)/config; \
	cp config_sample.json $(DIST_DIR)/config/; \
	cp openapi.json $(DIST_DIR)/

$(DIST_DIR)/main: $(DEPS_MAIN)
	python3 -m nuitka src/main.py --output-dir=$(BUILD_DIR)/main --output-filename=main \
		--standalone --include-package=websockets,tzdata --include-package-data=tzdata \
		--show-progress --prefer-source-code; \
	mkdir -p $(DIST_DIR); \
	cp -r $(BUILD_DIR)/main/main.dist/* $(DIST_DIR)/

$(DIST_DIR)/bannergen: $(DEPS_BANNERGEN)
	python3 -m nuitka src/bannergen/main.py --output-dir=$(BUILD_DIR)/bannergen \
		--output-filename=bannergen --standalone --include-package=websockets \
		--show-progress --prefer-source-code; \
	mkdir -p $(DIST_DIR); \
	cp -r $(BUILD_DIR)/bannergen/main.dist/* $(DIST_DIR)/

$(DIST_DIR)/launcher: $(DEPS_LAUNCHER)
	python3 -m nuitka src/launcher.py --output-dir=$(BUILD_DIR)/launcher \
		--output-filename=launcher --standalone --show-progress --prefer-source-code; \
	mkdir -p $(DIST_DIR); \
	cp -r $(BUILD_DIR)/launcher/launcher.dist/* $(DIST_DIR)/

clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR)