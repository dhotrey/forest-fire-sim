#include "hash_grid.hpp"

#include <cstdint>

std::string hash1d_grid(const std::vector<CellState> &grid, int grid_size) {
  std::uint64_t hash = 0;

  for (int x = 1; x < grid_size - 1; ++x) {
    const int row_start = x * grid_size;
    const int row_end = row_start + grid_size - 1;
    for (int index = row_start + 1; index < row_end; ++index) {
      hash = hash * 31 + static_cast<std::uint8_t>(grid[index]);
    }
  }

  return std::to_string(hash);
}

std::string hash2d_grid(const std::vector<std::vector<CellState>> &grid,
                        int grid_size) {
  std::uint64_t hash = 0;

  for (int x = 1; x < grid_size - 1; ++x) {
    for (int y = 1; y < grid_size - 1; ++y) {
      hash = hash * 31 + static_cast<std::uint8_t>(grid[x][y]);
    }
  }

  return std::to_string(hash);
}
