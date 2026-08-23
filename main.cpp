#include "pcg32.h"
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "build_info.hpp"
#include "save_file.hpp"

#ifndef PROGRAM_VERSION
#error "PROGRAM_VERSION must be defined by the build system"
#endif

const std::string VERSION = PROGRAM_VERSION;
const std::string VERSION_NAME = PROGRAM_VERSION_NAME;

int main(int argc, char *argv[]) {
#ifndef NO_VISUALIZATION
  bool visualise = false;
  bool verbose = false;
  const bool valid_arguments = argc >= 5 && argc <= 7;

  if (valid_arguments && argc >= 6 && std::string(argv[5]) == "--visualise") {
    visualise = true;
    if (argc == 7 &&
        (std::string(argv[6]) == "--v" || std::string(argv[6]) == "-v")) {
      verbose = true;
    } else if (argc == 7) {
      visualise = false;
    }
  }

  if (!valid_arguments || (argc >= 6 && !visualise)) {
    std::cerr << "Usage: " << argv[0]
              << " <grid_size> <timesteps> <p> <f>"
                 " [--visualise [--v|-v]]"
              << std::endl;
    return 1;
  }
#else
  if (argc != 5) {
    std::cerr << "Usage: " << argv[0] << " <grid_size> <timesteps> <p> <f>"
              << std::endl;
    return 1;
  }
#endif

  int grid_size =
      std::stoi(argv[1]) + 2; // padding so that i don't have to check for
                              // boundry conditions in the hot loop
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);

  build_info::print_startup_banner(argv[0], grid_size, timesteps, p, f, VERSION,
                                   VERSION_NAME);
#ifndef NO_VISUALIZATION
  std::unique_ptr<SaveFile> save_file;
  if (visualise) {
    std::filesystem::create_directories("out");
    const std::string binary_path = make_save_file_path(VERSION);
    save_file = std::make_unique<SaveFile>(
        binary_path, static_cast<std::uint32_t>(grid_size),
        static_cast<std::uint64_t>(timesteps), verbose);
    std::cout << "Visualisation binary: " << binary_path << '\n';
  }
#endif

  // TODO : compute the hash of this data structure
  std::vector<std::vector<CellState>> grid(grid_size,
                                           std::vector<CellState>(grid_size));

  std::vector<std::vector<CellState>> next(grid_size,
                                           std::vector<CellState>(grid_size));
  pcg32 rng(80085);
  // TODO : change this to fix the cache access patterns
  for (int t = 0; t < timesteps; ++t) {
    for (int y = 1; y < grid_size - 1; ++y) {
      for (int x = 1; x < grid_size - 1; ++x) {
        auto r = rng.nextFloat();
        switch (grid[x][y]) {
        case CellState::Empty:
          if (r < p) {
            next[x][y] = CellState::Tree;
          } else {
            next[x][y] = CellState::Empty;
          }
          break;
        case CellState::Burning:
          next[x][y] = CellState::Empty;
          break;
        case CellState::Tree:
          const auto up = grid[x][y - 1];
          const auto down = grid[x][y + 1];
          const auto left = grid[x - 1][y];
          const auto right = grid[x + 1][y];

          if (up == CellState::Burning || down == CellState::Burning ||
              left == CellState::Burning || right == CellState::Burning) {
            next[x][y] = CellState::Burning;
          } else if (r < f) {
            next[x][y] = CellState::Burning;
          } else {
            next[x][y] = CellState::Tree;
          }
          break;
        }
      }
    }

    std::swap(grid, next);
#ifndef NO_VISUALIZATION
    if (visualise) {
      save_file->write_frame(grid);
    }
#endif
  }
}
