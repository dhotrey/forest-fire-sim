CXX        ?= g++
TARGET     ?= bin/fire
OPT_TARGET := $(TARGET)-o
LOPT_TARGET := $(TARGET)-lo
SOURCES    := main.cpp build_info.cpp save_file.cpp

# These values are compiled into the startup banner so it describes the
# binary that is actually being run, rather than relying on runtime guesses.
COMPILER_TARGET ?= $(shell $(CXX) -dumpmachine 2>/dev/null || echo unknown)
BUILD_TARGET_NAME ?= $(TARGET)
BUILD_PROFILE   ?= Standard
OPTIMISATION    ?= compiler-default
VISUALIZATION_DEFINES ?= -DVISUALIZATION_AVAILABLE

BUILD_DEFINES := \
	-DBUILD_TARGET_NAME=\"$(BUILD_TARGET_NAME)\" \
	-DBUILD_COMPILER_TARGET=\"$(COMPILER_TARGET)\" \
	-DBUILD_PROFILE=\"$(BUILD_PROFILE)\" \
	-DBUILD_OPTIMISATION=\"$(OPTIMISATION)\" \
	$(VISUALIZATION_DEFINES)

STANDARD := -std=c++2a
WARNINGS := -Wall -Wextra -Wpedantic -Werror

.PHONY: all optimized optimised liltimised debug anim clean help

all: $(TARGET) optimized liltimised

$(TARGET) $(OPT_TARGET) $(LOPT_TARGET): $(SOURCES)
	$(CXX) $(STANDARD) $(WARNINGS) $(BUILD_DEFINES) $(CXXFLAGS) $(LDFLAGS) $^ $(LDLIBS) -o $@

optimized:
	$(MAKE) BUILD_TARGET_NAME=$(OPT_TARGET) BUILD_PROFILE=Optimised OPTIMISATION="-O3,-march=native,-mtune=native,-flto" VISUALIZATION_DEFINES=-DNO_VISUALIZATION CXXFLAGS="$(CXXFLAGS) -O3 -march=native -mtune=native -flto -DNDEBUG" $(OPT_TARGET)

optimised: optimized

liltimised:
	$(MAKE) BUILD_TARGET_NAME=$(LOPT_TARGET) BUILD_PROFILE=Optimised OPTIMISATION="-O2,-march=native,-mtune=native,-flto" VISUALIZATION_DEFINES=-DNO_VISUALIZATION CXXFLAGS="$(CXXFLAGS) -O2 -march=native -mtune=native -flto -DNDEBUG" $(LOPT_TARGET)

debug:
	$(MAKE) BUILD_PROFILE=Debug OPTIMISATION="-O0" VISUALIZATION_DEFINES=-DVISUALIZATION_AVAILABLE CXXFLAGS="$(CXXFLAGS) -O0 -g3 -DDEBUG" $(TARGET)

anim:
	cd animation && uv run visualise.py ../out/fire.bin

clean:
	rm -f $(TARGET) $(OPT_TARGET) $(LOPT_TARGET)

help:
	@echo "make            Build with strict warnings"
	@echo "make all        Build all three binaries"
	@echo "make optimized  Build an optimized release binary"
	@echo "make liltimised  Build an optimized release binary with -O2"
	@echo "make anim        Run the animation visualiser"
	@echo "make debug      Build with debug symbols and DEBUG enabled"
	@echo "make clean      Delete the binaries"
