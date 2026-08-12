#include <iostream>
#include <ostream>
#include <random>
#include <vector>

#include "build_info.hpp"

enum class CellState { Empty, Tree, Burning };
void print_grid(std::vector<std::vector<CellState>> grid) {
  for (int y = 0; y < static_cast<int>(grid.size()); y++) {
    for (int x = 0; x < static_cast<int>(grid.size()); x++) {
      std::cout << static_cast<int>(grid[x][y]) << " ";
    }
    std::cout << "\n";
  }
}

int main(int argc, char *argv[]) {

  if (argc != 5) {
    std::cerr << "Usage: " << argv[0] << " <grid_size> <timesteps> <p> <f>"
              << std::endl;
    return 1;
  }

  int grid_size = std::stoi(argv[1]);
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);

  build_info::print_startup_banner(grid_size, timesteps, p, f);

  std::vector<std::vector<CellState>> grid(grid_size,
                                           std::vector<CellState>(grid_size));

  // std::random_device randominator;
  // std::mt19937 gen(randominator());
  std::mt19937 gen(80085);
  std::uniform_real_distribution<double> dist(0.0, 1.0);

  for (int t = 0; t < timesteps; ++t) {
    std::cout << "Timestep " << t << std::endl;
    for (int y = 0; y < grid_size; y++) {
      for (int x = 0; x < grid_size; x++) {
        if (grid[x][y] == CellState::Empty || grid[x][y] == CellState::Tree) {
          if (dist(gen) < f) {
            grid[x][y] = CellState::Burning;
          } else if (dist(gen) < p) {
            grid[x][y] = CellState::Tree;
          }
        }
      }
    }
    print_grid(grid);
  }
}
