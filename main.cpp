#include <cstdint>
#include <fstream>
#include <iostream>
#include <random>
#include <string>
#include <vector>

#include "build_info.hpp"

enum class CellState : std::uint8_t { Empty, Tree, Burning };

#ifndef NO_VISUALISE
#pragma pack(push, 1)
struct SaveHeader {
  char magic[4];
  std::uint16_t version;
  std::uint32_t grid_size;
  std::uint64_t frame_count;
  std::uint32_t frame_interval;
  std::uint8_t cell_size;
};
#pragma pack(pop)

void print_grid(const std::vector<std::vector<CellState>> &grid) {
  for (int y = 0; y < static_cast<int>(grid.size()); ++y) {
    for (int x = 0; x < static_cast<int>(grid.size()); ++x) {
      std::cout << static_cast<int>(grid[x][y]) << ' ';
    }
    std::cout << '\n';
  }
}
#endif

int main(int argc, char *argv[]) {
#ifndef NO_VISUALISE
  const bool visualise = argc == 6 && std::string(argv[5]) == "-v";
  if (argc < 5 || argc > 6 || (argc == 6 && !visualise)) {
    std::cerr << "Usage: " << argv[0] << " <grid_size> <timesteps> <p> <f> [-v]"
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

  int grid_size = std::stoi(argv[1]);
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);

  build_info::print_startup_banner(grid_size, timesteps, p, f);
#ifndef NO_VISUALISE
  std::ofstream binary;
  std::ofstream csv;
  if (visualise) {
    binary.open("out/fire.bin", std::ios::binary);
    csv.open("out/fire.csv");

    SaveHeader header{{'F', 'F', 'C', 'A'},
                      1,
                      static_cast<std::uint32_t>(grid_size),
                      static_cast<std::uint64_t>(timesteps),
                      1,
                      1};
    binary.write(reinterpret_cast<const char *>(&header), sizeof(header));
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

#ifndef NO_VISUALISE
    if (visualise) {
      for (int y = 0; y < grid_size; ++y) {
        for (int x = 0; x < grid_size; ++x) {
          const auto cell = static_cast<std::uint8_t>(grid[x][y]);
          binary.write(reinterpret_cast<const char *>(&cell), sizeof(cell));
          csv << static_cast<int>(cell);
          if (x + 1 < grid_size) {
            csv << ',';
          }
        }
        csv << '\n';
      }
      csv << '\n';

      // std::cout << "Timestep " << t << '\n';
      // print_grid(grid);
    }
#endif
  }
}
