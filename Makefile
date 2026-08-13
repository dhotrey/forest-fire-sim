CXX ?= g++

TARGET     ?= bin/fire
O1_TARGET  ?= $(TARGET)-o1timised
O2_TARGET  ?= $(TARGET)-o2timised
O3_TARGET  ?= $(TARGET)-o3timised
SOURCES    := main.cpp build_info.cpp save_file.cpp

.DEFAULT_GOAL := $(TARGET)

# These values are compiled into the startup banner so it describes the
# binary that is actually being run, rather than relying on runtime guesses.
COMPILER_TARGET  ?= $(shell $(CXX) -dumpmachine 2>/dev/null || echo unknown)
BUILD_TARGET_NAME ?= $(TARGET)
BUILD_PROFILE     ?= Standard
OPTIMISATION     ?= compiler-default

STANDARD := -std=c++2a
WARNINGS := -Wall -Wextra -Wpedantic -Werror

# Optimised binaries omit visualisation unless it is explicitly requested.
VISUALISE ?= 0
ifeq ($(VISUALISE),1)
OPT_VISUALISE_FLAGS :=
else
OPT_VISUALISE_FLAGS := -DNO_VISUALIZATION
endif

BUILD_DEFINES = \
	-DBUILD_TARGET_NAME=\"$(BUILD_TARGET_NAME)\" \
	-DBUILD_COMPILER_TARGET=\"$(COMPILER_TARGET)\" \
	-DBUILD_PROFILE=\"$(BUILD_PROFILE)\" \
	-DBUILD_OPTIMISATION=\"$(OPTIMISATION)\"

.PHONY: all o1timised o2timised o3timised debug anim clean help FORCE

all: $(TARGET) o1timised o2timised o3timised

$(TARGET): $(SOURCES)
	@mkdir -p $(dir $@)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(CXXFLAGS) $(LDFLAGS) $^ $(LDLIBS) -o $@

# The FORCE prerequisite makes `make o1timised VISUALISE=1` rebuild the
# binary even when an earlier non-visualisation build already exists.
$(O1_TARGET): $(SOURCES) FORCE
	@mkdir -p $(dir $@)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(OPT_VISUALISE_FLAGS) $(CXXFLAGS) -O1 -DNDEBUG $(LDFLAGS) $(SOURCES) $(LDLIBS) -o $@

$(O2_TARGET): $(SOURCES) FORCE
	@mkdir -p $(dir $@)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(OPT_VISUALISE_FLAGS) $(CXXFLAGS) -O2 -DNDEBUG $(LDFLAGS) $(SOURCES) $(LDLIBS) -o $@

$(O3_TARGET): $(SOURCES) FORCE
	@mkdir -p $(dir $@)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(OPT_VISUALISE_FLAGS) $(CXXFLAGS) -O3 -DNDEBUG $(LDFLAGS) $(SOURCES) $(LDLIBS) -o $@

o1timised: BUILD_TARGET_NAME = $(O1_TARGET)
o1timised: BUILD_PROFILE = O1timised
o1timised: OPTIMISATION = -O1
o1timised: $(O1_TARGET)

o2timised: BUILD_TARGET_NAME = $(O2_TARGET)
o2timised: BUILD_PROFILE = O2timised
o2timised: OPTIMISATION = -O2
o2timised: $(O2_TARGET)

o3timised: BUILD_TARGET_NAME = $(O3_TARGET)
o3timised: BUILD_PROFILE = O3timised
o3timised: OPTIMISATION = -O3
o3timised: $(O3_TARGET)

debug: BUILD_TARGET_NAME = $(TARGET)
debug: BUILD_PROFILE = Debug
debug: OPTIMISATION = -O0
debug:
	@mkdir -p $(dir $(TARGET))
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(CXXFLAGS) -O0 -g3 -DDEBUG $(LDFLAGS) $(SOURCES) $(LDLIBS) -o $(TARGET)

SAVE_FILE ?= $(shell find out -maxdepth 1 -type f -name 'fire-*.bin' -printf '%T@ %p\n' 2>/dev/null | sort -nr | sed -n '1s/^[^ ]* //p')

anim:
	@test -n "$(SAVE_FILE)" || (echo "No save file found; use SAVE_FILE=out/fire-....bin"; exit 1)
	uv run --project animation python animation/visualise.py "$(SAVE_FILE)"

FORCE:

clean:
	rm -f $(TARGET) $(O1_TARGET) $(O2_TARGET) $(O3_TARGET)
	rm -rf out

help:
	@echo "make                         Build the default and all optimised binaries"
	@echo "make o1timised               Build with -O1"
	@echo "make o2timised               Build with -O2"
	@echo "make o3timised               Build with -O3"
	@echo "make o3timised VISUALISE=1  Include visualisation in an optimised build"
	@echo "make debug                   Build the default binary with debug symbols"
	@echo "make anim                    Visualise the newest save file"
	@echo "make clean                   Delete binaries and out/"
