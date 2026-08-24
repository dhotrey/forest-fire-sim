CXX ?= g++

# Program version is set here and compiled into the binary.
VERSION ?= 0.5
VERSION_NAME ?= 1d-grid

SOURCES := main.cpp build_info.cpp save_file.cpp
DEV_SOURCES := $(SOURCES) hash_grid.cpp

BIN_DIR := bin

COMPILER_TARGET ?= $(shell $(CXX) -dumpmachine 2>/dev/null || echo unknown)

STANDARD := -std=c++17
WARNINGS := -Wall -Wextra -Wpedantic -Werror
LDLIBS   ?= -lstdc++fs

COMMON_FLAGS := $(STANDARD) $(WARNINGS) -g -fno-omit-frame-pointer

VISUALISE ?= 0
ifeq ($(VISUALISE),1)
VIS_FLAGS :=
VIZ_SUFFIX := -viz
VISUALISE_NOTE := VISUALISE=1
else
VIS_FLAGS := -DNO_VISUALIZATION
VIZ_SUFFIX :=
endif

BUILD_DEFINES = \
	-DPROGRAM_VERSION=\"$(VERSION)\" \
	-DPROGRAM_VERSION_NAME=\"$(VERSION_NAME)\" \
	-DBUILD_COMPILER_TARGET=\"$(COMPILER_TARGET)\"

DEV_BIN := $(BIN_DIR)/fire-v$(VERSION)-dev$(VIZ_SUFFIX)
O1_BIN  := $(BIN_DIR)/fire-v$(VERSION)-o1$(VIZ_SUFFIX)
O2_BIN  := $(BIN_DIR)/fire-v$(VERSION)-o2$(VIZ_SUFFIX)
O3_BIN  := $(BIN_DIR)/fire-v$(VERSION)-o3$(VIZ_SUFFIX)

.DEFAULT_GOAL := dev

.PHONY: all dev o1 o2 o3 anim clean help FORCE

all: dev o1 o2 o3

define compile
	mkdir -p $(BIN_DIR)
	$(CXX) $(COMMON_FLAGS) $(BUILD_DEFINES) $(VIS_FLAGS) $(CXXFLAGS) $(1) $(LDFLAGS) $(3) $(LDLIBS) '-DBUILD_FLAGS="$(2) $(VISUALISE_NOTE)"' -o $@
endef

# FORCE prerequisites let `make o2 VISUALISE=1` rebuild even when a
# non-visualisation binary with the same version already exists.
$(DEV_BIN): $(DEV_SOURCES) hash_grid.hpp FORCE
	$(call compile,-O0 -DDEBUG,O0 DEBUG,$(DEV_SOURCES))

$(O1_BIN): $(SOURCES) FORCE
	$(call compile,-O1 -DNDEBUG,O1 NDEBUG,$(SOURCES))

$(O2_BIN): $(SOURCES) FORCE
	$(call compile,-O2 -DNDEBUG,O2 NDEBUG,$(SOURCES))

$(O3_BIN): $(SOURCES) FORCE
	$(call compile,-O3 -DNDEBUG,O3 NDEBUG,$(SOURCES))

dev: $(DEV_BIN)
o1:  $(O1_BIN)
o2:  $(O2_BIN)
o3:  $(O3_BIN)

SAVE_FILE ?= $(shell find out -maxdepth 1 -type f -name 'fire-*.bin' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed -n '1s/^[^ ]* //p')

anim:
	@test -n "$(SAVE_FILE)" || (echo "No save file found; use SAVE_FILE=out/fire-....bin"; exit 1)
	uv run --project tools/animation python tools/animation/visualise.py "$(SAVE_FILE)"

FORCE:

clean:
	rm -rf $(BIN_DIR) out

help:
	@echo "make dev                     Build the -O0 debug binary"
	@echo "make o1                      Build with -O1"
	@echo "make o2                      Build with -O2"
	@echo "make o3                      Build with -O3"
	@echo "make <mode> VISUALISE=1      Include visualisation (adds -viz to the name)"
	@echo "make VERSION=0.1 <mode>      Override the compiled-in program version"
	@echo "make anim                    Visualise the newest save file"
	@echo "make clean                   Delete binaries and out/"
