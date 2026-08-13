#include <cstdint>
#include <filesystem>
#include <iostream>
#include <memory>
#include <random>
#include <string>
#include <vector>

#include "build_info.hpp"
#include "save_file.hpp"

const std::string VERSION = "0.0";

int main(int argc, char *argv[]) {
#ifndef NO_VISUALIZATION
  bool visualise = false;
  bool verbose = false;
  const bool valid_arguments = argc >= 5 && argc <= 7;

  if (valid_arguments && argc >= 6 && std::string(argv[5]) == "--visualise") {
    visualise = true;
    if (argc == 7 && (std::string(argv[6]) == "--v" ||
                      std::string(argv[6]) == "-v")) {
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
    std::cerr << "Usage: " << argv[0]
              << " <grid_size> <timesteps> <p> <f>" << std::endl;
    return 1;
  }
#endif

  int grid_size = std::stoi(argv[1]);
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);

  build_info::print_startup_banner(grid_size, timesteps, p, f);
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

  std::vector<std::vector<CellState>> grid(grid_size,
                                           std::vector<CellState>(grid_size));

  // std::random_device randominator;
  // std::mt19937 gen(randominator());
  std::mt19937 gen(80085);
  std::uniform_real_distribution<double> dist(0.0, 1.0);

  for (int t = 0; t < timesteps; ++t) {
    for (int y = 0; y < grid_size; ++y) {
      for (int x = 0; x < grid_size; ++x) {
        if (grid[x][y] == CellState::Empty || grid[x][y] == CellState::Tree) {
          if (dist(gen) < f) {
            grid[x][y] = CellState::Burning;
          } else if (dist(gen) < p) {
            grid[x][y] = CellState::Tree;
          }
        }
      }
    }

#ifndef NO_VISUALIZATION
    if (visualise) {
      save_file->write_frame(grid);
    }
#endif
  }
}
