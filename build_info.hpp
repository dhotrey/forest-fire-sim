#ifndef BUILD_INFO_HPP
#define BUILD_INFO_HPP

#include <string>
namespace build_info {

void print_startup_banner(const char *executable, int grid_size, int timesteps,
                          double p, double f, std::string version,
                          std::string version_name);

} // namespace build_info

#endif // BUILD_INFO_HPP
