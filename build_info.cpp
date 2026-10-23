#include "build_info.hpp"
#include <iostream>
#include <string>
#include <omp.h>
#ifndef BUILD_COMPILER_TARGET
#define BUILD_COMPILER_TARGET "unspecified"
#endif

#ifndef BUILD_FLAGS
#define BUILD_FLAGS "unspecified"
#endif

namespace {

const char *cpp_standard() {
#if __cplusplus >= 202302L
  return "C++23 or later";
#elif __cplusplus >= 202002L
  return "C++20";
#elif __cplusplus >= 201703L
  return "C++17";
#elif __cplusplus >= 201402L
  return "C++14";
#elif __cplusplus >= 201103L
  return "C++11";
#else
  return "pre-C++11";
#endif
}

const char *compiler_name() {
#if defined(__clang__)
  return "Clang " __VERSION__;
#elif defined(__GNUC__)
  return "GCC " __VERSION__;
#elif defined(_MSC_VER)
  return "MSVC";
#else
  return "unknown compiler";
#endif
}

const char *optimisation_status() {
#ifdef __OPTIMIZE__
  return "enabled";
#else
  return "disabled";
#endif
}

} // namespace

namespace build_info {

void print_startup_banner(const char *executable, int grid_size, int timesteps,
                          double p, double f, std::string version,
                          std::string version_name) {
  std::cout << "Cellular automata based forest fire model\n"
            << "--------------------------------------------------\n"
            << "Model configuration\n"
            << "  Grid size:       " << grid_size << '\n'
            << "  Time steps:      " << timesteps << '\n'
            << "  p (growth):      " << p << '\n'
            << "  f (lightning):   " << f << '\n'
            << "--------------------------------------------------\n"
            << "Runtime information\n";
#ifdef _OPENMP
  std::cout << "  OpenMP threads:  " << omp_get_max_threads() << '\n';
#else
  std::cout << "  OpenMP threads:  1 (OpenMP disabled)\n";
#endif
  std::cout << "--------------------------------------------------\n"
            << "Build information\n"
            << "  Version          " << version << " " << version_name << '\n'
            << "  Compiled:        " << __DATE__ << ' ' << __TIME__ << '\n'
            << "  Compiler:        " << compiler_name() << '\n'
            << "  C++ standard:    " << cpp_standard()
            << " (__cplusplus=" << __cplusplus << ")\n"
            << "  Compiler target: " << BUILD_COMPILER_TARGET << '\n'
            << "  Executable:      " << executable << '\n'
            << "  Build flags:     " << BUILD_FLAGS << '\n'
            << "  Optimisation:    " << optimisation_status() << '\n'
            << std::endl;
}

} // namespace build_info
