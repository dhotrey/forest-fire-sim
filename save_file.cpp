#include "save_file.hpp"

#include <iomanip>
#include <cstddef>
#include <ctime>
#include <filesystem>

namespace {

void write_little_endian(std::ofstream &file, std::uint64_t value,
                         std::size_t byte_count) {
  for (std::size_t byte = 0; byte < byte_count; ++byte) {
    const auto encoded = static_cast<std::uint8_t>(value >> (byte * 8));
    file.write(reinterpret_cast<const char *>(&encoded), sizeof(encoded));
  }
}

std::string output_timestamp() {
  const auto now = std::chrono::system_clock::now();
  const auto time = std::chrono::system_clock::to_time_t(now);
  const auto milliseconds =
      std::chrono::duration_cast<std::chrono::milliseconds>(
          now.time_since_epoch()) %
      1000;
  const std::tm *local_time = std::localtime(&time);

  std::ostringstream timestamp;
  timestamp << std::put_time(local_time, "%Y-%m-%d-%H-%M-%S") << '-'
            << std::setfill('0') << std::setw(3) << milliseconds.count();
  return timestamp.str();
}

} // namespace

std::string make_save_file_path(const std::string &version) {
  return "out/fire-" + version + "-" + output_timestamp() + ".bin";
}

SaveFile::SaveFile(const std::string &binary_path, std::uint32_t grid_size,
                   std::uint64_t frame_count, bool write_csv)
    : binary_(binary_path, std::ios::binary), grid_size_(grid_size) {
  if (write_csv) {
    std::filesystem::path csv_path(binary_path);
    csv_path.replace_extension(".csv");
    csv_.open(csv_path);
  }

  binary_.write("FFCA", 4);
  write_little_endian(binary_, 1, 2);         // format version
  write_little_endian(binary_, grid_size, 4); // square grid size
  write_little_endian(binary_, frame_count, 8);
  write_little_endian(binary_, 1, 4); // frame interval
  write_little_endian(binary_, 1, 1); // cell size
}

void SaveFile::write_frame(const std::vector<std::vector<CellState>> &grid) {
  for (std::uint32_t y = 0; y < grid_size_; ++y) {
    for (std::uint32_t x = 0; x < grid_size_; ++x) {
      const auto cell = static_cast<std::uint8_t>(grid[x][y]);
      binary_.write(reinterpret_cast<const char *>(&cell), sizeof(cell));

      if (csv_.is_open()) {
        csv_ << static_cast<int>(cell);
        if (x + 1 < grid_size_) {
          csv_ << ',';
        }
      }
    }

    if (csv_.is_open()) {
      csv_ << '\n';
    }
  }

  if (csv_.is_open()) {
    csv_ << '\n';
  }
}
