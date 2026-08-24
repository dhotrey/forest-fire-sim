#include "pcg32.h"
#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "build_info.hpp"
#include "save_file.hpp"
#ifdef DEBUG
#include "hash_grid.hpp"
#endif

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

  const int requested_grid_size = std::stoi(argv[1]);
  int grid_size =
      requested_grid_size + 2; // padding so that i don't have to check for
                               // boundry conditions in the hot loop
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);

  const uint32_t p_threshold = static_cast<uint32_t>(
      p * static_cast<double>(std::numeric_limits<uint32_t>::max()));

  const uint32_t f_threshold = static_cast<uint32_t>(
      f * static_cast<double>(std::numeric_limits<uint32_t>::max()));

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

  std::vector<CellState> grid(grid_size * grid_size);

  std::vector<CellState> next(grid_size * grid_size);
  pcg32 rng(80085);
  for (int t = 0; t < timesteps; ++t) {
    for (int x = 1; x < grid_size - 1; ++x) {
      const int row_start = x * grid_size;
      const int row_end = row_start + grid_size - 1;
      for (int index = row_start + 1; index < row_end; ++index) {
        auto r = rng.nextUInt();
        switch (grid[index]) {
        case CellState::Empty:
          if (r < p_threshold) {
            next[index] = CellState::Tree;
          } else {
            next[index] = CellState::Empty;
          }
          break;
        case CellState::Burning:
          next[index] = CellState::Empty;
          break;
        case CellState::Tree:
          const auto up = grid[index - 1];
          const auto down = grid[index + 1];
          const auto left = grid[index - grid_size];
          const auto right = grid[index + grid_size];

          if (up == CellState::Burning || down == CellState::Burning ||
              left == CellState::Burning || right == CellState::Burning) {
            next[index] = CellState::Burning;
          } else {
            if (r < f_threshold) {
              next[index] = CellState::Burning;
            } else {
              next[index] = CellState::Tree;
            }
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

#ifdef DEBUG
  const std::string final_hash = hash1d_grid(grid, grid_size);
  const bool is_reference_case =
      requested_grid_size == 1000 && timesteps == 500 && p == 0.02 && f == 0.01;

  if (is_reference_case) {
    if (final_hash == "15213144908148633160") {
      std::cout << "Correctness check passed: 1D grid hash matches expected "
                   "value.\n";
    } else {
      std::cout << "Correctness check failed: expected "
                << "15213144908148633160, got " << final_hash << ".\n";
    }
  } else {
    std::cout << "1D grid hash: " << final_hash << '\n';
  }
#endif
}
