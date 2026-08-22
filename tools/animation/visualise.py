import struct
import sys

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.colors import ListedColormap

HEADER = struct.Struct("<4sHIQIB")


def read_save_file(filename):
    with open(filename, "rb") as save_file:
        magic, version, grid_size, frame_count, interval, cell_size = HEADER.unpack(
            save_file.read(HEADER.size)
        )
        data = np.fromfile(save_file, dtype=np.uint8)

    if magic != b"FFCA" or version != 1:
        raise ValueError("not a supported forest-fire save file")

    frames = data.reshape(frame_count, grid_size, grid_size)
    return frames, interval


filename = sys.argv[1]
skip = int(sys.argv[2]) if len(sys.argv) > 2 else 1
frames, interval = read_save_file(filename)

figure, axes = plt.subplots()
colours = ListedColormap(["black", "green", "red"])
image = axes.imshow(frames[0], cmap=colours, vmin=0, vmax=2, interpolation="nearest")


def update(frame_number):
    image.set_data(frames[frame_number])
    axes.set_title(f"Timestep {frame_number * interval}")
    return (image,)


animation = FuncAnimation(
    figure,
    update,
    frames=range(0, len(frames), skip),
    interval=100,
    repeat=False,
)
plt.show()
