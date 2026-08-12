#include <iostream>

#include "build_info.hpp"

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
  
}
