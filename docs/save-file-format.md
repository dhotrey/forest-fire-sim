# Binary save-file format

`fire-{version}-{date}-{time}.bin` is self-describing and does not require the
Python script to be told the grid size or number of timesteps. All integer
fields are fixed-width and little-endian. The complete file is laid out like
this:

```text
┌─────────────────────────────────────────────────────────────────────┐
│ Header (23 bytes)                                                   │
├────────┬───────────┬───────────┬────────────┬───────────┬───────────┤
│ "FFCA" │ version   │ grid size │ frame count│ interval  │ cell size │
│ 4 B    │ 2 B       │ 4 B       │ 8 B        │ 4 B       │ 1 B       │
└────────┴───────────┴───────────┴────────────┴───────────┴───────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Frame 0: grid_size × grid_size one-byte cell states                 │
├─────────────────────────────────────────────────────────────────────┤
│ Frame 1: grid_size × grid_size one-byte cell states                 │
├─────────────────────────────────────────────────────────────────────┤
│ ...                                                                 │
├─────────────────────────────────────────────────────────────────────┤
│ Frame frame_count - 1: grid_size × grid_size one-byte cell states   │
└─────────────────────────────────────────────────────────────────────┘
```

The header fields are, in order: the magic bytes `FFCA`; format version
`uint16` (currently `1`); square grid size `uint32`; saved-frame count
`uint64`; frame interval `uint32` (currently `1`); and cell size `uint8`
(currently `1`). Each frame contains `grid_size * grid_size` cells in display
order: all x values for y = 0, then all x values for y = 1, and so on. Cell
states are `0 = Empty`, `1 = Tree`, and `2 = Burning`. Frame 0 is the grid after
the first completed update, so a run with `timesteps = N` contains exactly N
frames.

The stored grid size includes the one-cell border on every side: an input size
of 256 produces a 258 × 258 stored grid. The startup banner also reports this
padded size.
