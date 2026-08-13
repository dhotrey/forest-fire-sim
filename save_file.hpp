#ifndef SAVE_FILE_HPP
#define SAVE_FILE_HPP

#include <cstdint>
#include <fstream>
#include <string>
#include <vector>

enum class CellState : std::uint8_t { Empty, Tree, Burning };

std::string make_save_file_path(const std::string &version);

class SaveFile {
public:
  SaveFile(const std::string &binary_path, std::uint32_t grid_size,
           std::uint64_t frame_count,
           bool write_csv = false);

  void write_frame(const std::vector<std::vector<CellState>> &grid);

private:
  std::ofstream binary_;
  std::ofstream csv_;
  std::uint32_t grid_size_;
};

#endif // SAVE_FILE_HPP
