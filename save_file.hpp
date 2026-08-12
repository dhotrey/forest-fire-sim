#ifndef SAVE_FILE_HPP
#define SAVE_FILE_HPP

#include <cstdint>
#include <fstream>
#include <string>

class SaveFile {
public:
  SaveFile(const std::string &binary_path, const std::string &csv_path,
           std::uint32_t grid_size, std::uint64_t frame_count);

  template <typename Grid> void write_frame(const Grid &grid) {
    for (std::uint32_t y = 0; y < grid_size_; ++y) {
      for (std::uint32_t x = 0; x < grid_size_; ++x) {
        const auto cell = static_cast<std::uint8_t>(grid[x][y]);
        binary_.write(reinterpret_cast<const char *>(&cell), sizeof(cell));
        csv_ << static_cast<int>(cell);
        if (x + 1 < grid_size_) {
          csv_ << ',';
        }
      }
      csv_ << '\n';
    }
    csv_ << '\n';
  }

private:
  std::ofstream binary_;
  std::ofstream csv_;
  std::uint32_t grid_size_;
};

#endif // SAVE_FILE_HPP
