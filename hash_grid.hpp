#ifndef HASH_GRID_HPP
#define HASH_GRID_HPP

#include "save_file.hpp"

#include <cstddef>
#include <string>
#include <vector>

std::string hash1d_grid(const std::vector<CellState> &grid, int grid_size);
std::string hash2d_grid(const std::vector<std::vector<CellState>> &grid,
                        int grid_size);

#endif // HASH_GRID_HPP
