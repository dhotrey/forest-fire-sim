CXX        ?= g++
TARGET     ?= bin/fire
OPT_TARGET := $(TARGET)-o
SOURCES    := main.cpp build_info.cpp

# These values are compiled into the startup banner so it describes the
# binary that is actually being run, rather than relying on runtime guesses.
COMPILER_TARGET ?= $(shell $(CXX) -dumpmachine 2>/dev/null || echo unknown)
BUILD_TARGET_NAME ?= $(TARGET)
BUILD_PROFILE   ?= Standard
OPTIMISATION    ?= compiler-default

BUILD_DEFINES := \
	-DBUILD_TARGET_NAME=\"$(BUILD_TARGET_NAME)\" \
	-DBUILD_COMPILER_TARGET=\"$(COMPILER_TARGET)\" \
	-DBUILD_PROFILE=\"$(BUILD_PROFILE)\" \
	-DBUILD_OPTIMISATION=\"$(OPTIMISATION)\"

STANDARD := -std=c++2a
WARNINGS := -Wall -Wextra -Wpedantic -Werror

.PHONY: all optimized optimised debug clean help

all: $(TARGET)

$(TARGET) $(OPT_TARGET): $(SOURCES)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(CXXFLAGS) $(LDFLAGS) $^ $(LDLIBS) -o $@

optimized:
	$(MAKE) clean
	$(MAKE) BUILD_TARGET_NAME=$(OPT_TARGET) BUILD_PROFILE=Optimised OPTIMISATION="-O3,-march=native,-mtune=native,-flto" CXXFLAGS="$(CXXFLAGS) -O3 -march=native -mtune=native -flto -DNDEBUG" $(OPT_TARGET)

optimised: optimized

debug:
	$(MAKE) clean
	$(MAKE) BUILD_PROFILE=Debug OPTIMISATION="-O0" CXXFLAGS="$(CXXFLAGS) -O0 -g3 -DDEBUG" $(TARGET)

clean:
	rm -f $(TARGET) $(OPT_TARGET)

help:
	@echo "make            Build with strict warnings"
	@echo "make optimized  Build an optimized release binary"
	@echo "make debug      Build with debug symbols and DEBUG enabled"
	@echo "make clean      Delete the binaries"
