#include <cstdint>
#include <filesystem>
#include <iostream>
#include <limits>
#include <memory>
#include <string>
#include <utility>
#include <vector>

#include "pcg32_8.h"
#include <avx2intrin.h>

#include "build_info.hpp"
#include "save_file.hpp"
#ifdef DEBUG
#include "hash_grid.hpp"
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
  // padding so that i don't have to check for boundry conditions
  int grid_size = std::stoi(argv[1]) + 2;
  int timesteps = std::stoi(argv[2]);
  double p = std::stod(argv[3]);
  double f = std::stod(argv[4]);
  const __m256 pVector = _mm256_set1_ps(static_cast<float>(p));
  const __m256 fVector = _mm256_set1_ps(static_cast<float>(f));
  // clang-format off
  build_info::print_startup_banner(argv[0], grid_size, timesteps, p, f, VERSION, VERSION_NAME);
  // clang-format on

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
  pcg32_8 rng;

  const __m256i emptyVector = _mm256_setzero_si256(); // 32 cells set to 0
  const __m256i treeVector = _mm256_set1_epi8(1);     // 32 tree cells
  const __m256i fireVector = _mm256_set1_epi8(2);     // 32 fire cells

  for (int t = 0; t < timesteps; ++t) {
    for (int x = 1; x < grid_size - 1; x++) {
      for (int y = 1; y < grid_size - 1; y += 32) {
        const auto idx = x * grid_size + y;

        // read 256 bits of memory starting from idx
        __m256i current = _mm256_loadu_si256(
            reinterpret_cast<const __m256i *>(grid.data() + idx));
        __m256i left = _mm256_loadu_si256(
            reinterpret_cast<const __m256i *>(grid.data() + idx - 1));
        __m256i right = _mm256_loadu_si256(
            reinterpret_cast<const __m256i *>(grid.data() + idx + 1));
        __m256i up = _mm256_loadu_si256(
            reinterpret_cast<const __m256i *>(grid.data() + idx + grid_size));
        __m256i down = _mm256_loadu_si256(
            reinterpret_cast<const __m256i *>(grid.data() + idx - grid_size));

        // this bitwise or gives us all the cells from our neighbours that
        // either have a tree or fire neighbors contains the OR result rather
        // than a true or false so eg TREE OR fIRE would be (01 V 10) = 11
        __m256i neighbours = _mm256_or_si256(_mm256_or_si256(left, right),
                                           _mm256_or_si256(up, down));

        // here we single out only the burning cells from the neighbors
        // something like 11 AND 10 -> 10 or 10 AND 10 also -> 10 so we preserve
        // which cells have a burning neighbour
        // so fire bits will look something like [0,0,0b10,0,0b10 . . . ] or
        // [0,0,2,0,2,. . . ]
        __m256i fireBits = _mm256_and_si256(neighbours, fireVector);

        // isPropogating gives us a true/false mask for which indices does the
        // fire propogate to
        __m256i isPropogating = _mm256_cmpeq_epi8(fireBits, fireVector);

        // both these arrays basically array of size 4 where each element is a
        // 256 bit vector containing eight 32 bit comparisons eg
        // [ T T F F T F T F ]
        __m256i growthChecks[4];
        __m256i fireChecks[4];

        // this is the loop for calling the rng 4 times
        // #pragma GCC unroll 4
        // for (int i = 0; i < 4; i++) {
        //   __m256 randoms = rng.nextFloat(); // this gives us 8 randoms
        //   // clang-format off
        //   growthChecks[i] =_mm256_castps_si256(_mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ));
        //   fireChecks[i] = _mm256_castps_si256(_mm256_cmp_ps(randoms, fVector, _CMP_LT_OQ));
        //   // clang-format on
        // }

        // Explicit manual unrolling maximizes ILP and pipelines the pcg32_8 math
        {
            // Block 0
            __m256 r0 = rng.nextFloat();
            growthChecks[0] = _mm256_castps_si256(_mm256_cmp_ps(r0, pVector, _CMP_LT_OQ));
            fireChecks[0]   = _mm256_castps_si256(_mm256_cmp_ps(r0, fVector, _CMP_LT_OQ));
        
            // Block 1: CPU starts computing this RNG block while Block 0's _mm256_cmp_ps is in flight
            __m256 r1 = rng.nextFloat();
            growthChecks[1] = _mm256_castps_si256(_mm256_cmp_ps(r1, pVector, _CMP_LT_OQ));
            fireChecks[1]   = _mm256_castps_si256(_mm256_cmp_ps(r1, fVector, _CMP_LT_OQ));
        
            // Block 2
            __m256 r2 = rng.nextFloat();
            growthChecks[2] = _mm256_castps_si256(_mm256_cmp_ps(r2, pVector, _CMP_LT_OQ));
            fireChecks[2]   = _mm256_castps_si256(_mm256_cmp_ps(r2, fVector, _CMP_LT_OQ));
        
            // Block 3
            __m256 r3 = rng.nextFloat();
            growthChecks[3] = _mm256_castps_si256(_mm256_cmp_ps(r3, pVector, _CMP_LT_OQ));
            fireChecks[3]   = _mm256_castps_si256(_mm256_cmp_ps(r3, fVector, _CMP_LT_OQ));
        }
        // packing all comparison results a single 256 bit vectors

        __m256i isGrowing = _mm256_packs_epi16(
            _mm256_packs_epi32(growthChecks[0], growthChecks[1]),
            _mm256_packs_epi32(growthChecks[2], growthChecks[3]));

        __m256i isBurning = _mm256_packs_epi16(
            _mm256_packs_epi32(fireChecks[0], fireChecks[1]),
            _mm256_packs_epi32(fireChecks[2], fireChecks[3]));

        // the isGrowing and isBurning masks are not necessarily correct in
        // terms of which cells they map to but that's a TODO for v1.2

        __m256i isEmpty = _mm256_cmpeq_epi8(emptyVector, current);
        __m256i isTree = _mm256_cmpeq_epi8(treeVector, current);
        __m256i isToBeEmpty = _mm256_cmpeq_epi8(fireVector, current);

        __m256i treeGrowing = _mm256_and_si256(isEmpty, isGrowing);
        // clang-format off
        __m256i treeBurning =_mm256_and_si256(isTree, _mm256_or_si256(isBurning, isPropogating));
        __m256i nextVector = current;

        // Empty cells selected for growth become trees
        nextVector = _mm256_blendv_epi8(nextVector, treeVector, treeGrowing);
        // Trees selected for ignition become fire
        nextVector = _mm256_blendv_epi8(nextVector, fireVector, treeBurning);
        // Cells that were already burning become empty
        nextVector = _mm256_blendv_epi8(nextVector, emptyVector, isToBeEmpty);
        // Write these 32 updated cells into the next grid
        _mm256_storeu_si256(reinterpret_cast<__m256i *>(next.data() + idx),nextVector);
        //clang-format on
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
  std::cout << "1D grid hash: " << hash1d_grid(grid, grid_size)
            << '\n'; // expected: ...
#endif
}
