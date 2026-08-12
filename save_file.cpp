#include "save_file.hpp"

#include <cstddef>

namespace {

void write_little_endian(std::ofstream &file, std::uint64_t value,
                         std::size_t byte_count) {
  for (std::size_t byte = 0; byte < byte_count; ++byte) {
    const auto encoded = static_cast<std::uint8_t>(value >> (byte * 8));
    file.write(reinterpret_cast<const char *>(&encoded), sizeof(encoded));
  }
}

} // namespace

SaveFile::SaveFile(const std::string &binary_path, const std::string &csv_path,
                   std::uint32_t grid_size, std::uint64_t frame_count)
    : binary_(binary_path, std::ios::binary), csv_(csv_path),
      grid_size_(grid_size) {
  binary_.write("FFCA", 4);
  write_little_endian(binary_, 1, 2);          // format version
  write_little_endian(binary_, grid_size, 4);  // square grid size
  write_little_endian(binary_, frame_count, 8);
  write_little_endian(binary_, 1, 4);          // frame interval
  write_little_endian(binary_, 1, 1);          // cell size
}
