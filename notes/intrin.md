# SIMD intrinsic reference

For the planned AVX2 update: 32 byte-sized cells, two RNG calls interpreted as 32 total unsigned 16-bit random values, then byte masks and blends. The interior width is divisible by 32.

## Setup and how to read the names

```cpp
#include <immintrin.h>
#include <cstdint>
#include <limits>
```

Compile with AVX2 enabled (`-mavx2`) and run on an AVX2-capable CPU. The examples use your existing `grid`, `next`, and `rng`; `i` is the current flat index and `width` includes the two border columns.

`__m256i` is a 256-bit integer vector type: `m` is the SIMD vector naming convention, `256` is its total width, and `i` means integer. The operation decides whether those bits are treated as 32 bytes, 16 words, or eight 32-bit integers. No conversion is needed to use the RNG's returned bits with 16-bit operations.

| Name part | Meaning |
|---|---|
| `_mm256` | Intel's historical multimedia/SIMD intrinsic prefix, for 256-bit vectors. The leading underscore is part of the API name. |
| `epi8`, `epi16` | Extended packed integers, with 8-bit or 16-bit elements. Signedness depends on the operation. |
| `si256` | A 256-bit integer-vector operand/result, without specifying an element width. This suffix does not imply a signed comparison. |
| `set1` | Repeat one supplied value across every element; it does not mean fill with the number one. |
| `loadu`, `storeu` | Load/store with an unaligned address; `u` here means unaligned, not unsigned. |

Keep the constant vectors and adjusted thresholds outside the timestep loop. Examples below are fragments, not a complete update loop.

## 1. `_mm256_set1_epi8(value)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_set1_epi8)

**Name:** `_mm256` = 256-bit SIMD; `set1` = repeat one value; `epi8` = packed 8-bit integers.

Broadcast a cell value into all 32 bytes.

```cpp
const __m256i emptyVector = _mm256_set1_epi8(0);
const __m256i treeVector  = _mm256_set1_epi8(1);
const __m256i fireVector  = _mm256_set1_epi8(2);
```

## 2. `_mm256_set1_epi16(value)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_set1_epi16)

**Name:** `_mm256` = 256-bit SIMD; `set1` = repeat one value; `epi16` = packed 16-bit integers.

Broadcast a threshold or sign-bit pattern into all 16 words.

```cpp
// round(0.02 * 65536) and round(0.01 * 65536).
const __m256i pThreshold = _mm256_set1_epi16(1311);
const __m256i fThreshold = _mm256_set1_epi16(655);

// -32768 has the 16-bit pattern 0x8000 on this x86 target.
const __m256i signBit =
    _mm256_set1_epi16(std::numeric_limits<std::int16_t>::min());
```

These are new 16-bit thresholds; do not truncate the existing 32-bit thresholds. Probability 1 needs an explicit all-true case because threshold 65536 does not fit in 16 bits.

## 3. `_mm256_setzero_si256()` — optional

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_setzero_si256)

**Name:** `_mm256` = 256-bit SIMD; `setzero` = clear every bit; `si256` = integer vector spanning 256 bits.

Construct an all-zero vector. This can replace `set1_epi8(0)` for EMPTY.

```cpp
const __m256i zeroVector = _mm256_setzero_si256();
```

## 4. `_mm256_loadu_si256(pointer)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_loadu_si256)

**Name:** `_mm256` = 256-bit SIMD; `load` = read memory; `u` = unaligned; `si256` = 256-bit integer vector.

Read 32 consecutive bytes. No 32-byte address alignment is required.

```cpp
__m256i current = _mm256_loadu_si256(
    reinterpret_cast<const __m256i*>(grid.data() + i));
__m256i above = _mm256_loadu_si256(
    reinterpret_cast<const __m256i*>(grid.data() + i - width));
__m256i below = _mm256_loadu_si256(
    reinterpret_cast<const __m256i*>(grid.data() + i + width));
__m256i left = _mm256_loadu_si256(
    reinterpret_cast<const __m256i*>(grid.data() + i - 1));
__m256i right = _mm256_loadu_si256(
    reinterpret_cast<const __m256i*>(grid.data() + i + 1));
```

Pointer arithmetic happens on the byte-sized `CellState` pointer before the cast. All 32 bytes must still be valid memory; unaligned does not mean bounds-checked.

## 5. `_mm256_cmpeq_epi8(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_cmpeq_epi8)

**Name:** `_mm256` = 256-bit SIMD; `cmp` = compare; `eq` = equal; `epi8` = packed 8-bit integers.

Compare corresponding bytes: equal gives `0xFF`, unequal gives `0x00`.

```cpp
__m256i isEmpty = _mm256_cmpeq_epi8(current, emptyVector);
__m256i isTree = _mm256_cmpeq_epi8(current, treeVector);
__m256i isToBeEmpty = _mm256_cmpeq_epi8(current, fireVector);
```

Equality needs no signed/unsigned adjustment. These masks describe the original current cells.

## 6. `_mm256_or_si256(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_or_si256)

**Name:** `_mm256` = 256-bit SIMD; `or` = bitwise OR; `si256` = whole 256-bit integer vector.

Set each output bit if either input has it set.

```cpp
__m256i neighbours = _mm256_or_si256(
    _mm256_or_si256(above, below),
    _mm256_or_si256(left, right));
```

With cell values 0, 1, and 2, bit `0b10` is present exactly when at least one neighbour is burning.

## 7. `_mm256_and_si256(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_and_si256)

**Name:** `_mm256` = 256-bit SIMD; `and` = bitwise AND; `si256` = whole 256-bit integer vector.

Keep only bits set in both inputs.

```cpp
__m256i fireBits = _mm256_and_si256(neighbours, fireVector);
__m256i isPropagating = _mm256_cmpeq_epi8(fireBits, fireVector);
```

`fireBits` contains cell-bit values 0 or 2. The comparison converts these to full byte masks 0x00 or 0xFF.

## 8. `_mm256_xor_si256(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_xor_si256)

**Name:** `_mm256` = 256-bit SIMD; `xor` = bitwise exclusive OR; `si256` = whole 256-bit integer vector.

Flip bits selected by the other operand. Here, flip each word's sign bit.

```cpp
// Constants: calculate outside the timestep loop.
const __m256i pAdjusted = _mm256_xor_si256(pThreshold, signBit);
const __m256i fAdjusted = _mm256_xor_si256(fThreshold, signBit);

// Per batch: two RNG calls, each supplying sixteen 16-bit values.
__m256i randomA = _mm256_xor_si256(rng.nextUInt(), signBit);
__m256i randomB = _mm256_xor_si256(rng.nextUInt(), signBit);
```

`rng.nextUInt()` is a library method, not an intrinsic. It returns eight 32-bit outputs; the 16-bit operations use both halves of every output. This is reinterpretation of the bits, not numerical conversion or truncation to only eight values.

## 9. `_mm256_cmpgt_epi16(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_cmpgt_epi16)

**Name:** `_mm256` = 256-bit SIMD; `cmp` = compare; `gt` = greater than; `epi16` = packed 16-bit integers.

Signed comparison of 16 corresponding words: true gives `0xFFFF`, false gives zero.

```cpp
__m256i growA = _mm256_cmpgt_epi16(pAdjusted, randomA);
__m256i growB = _mm256_cmpgt_epi16(pAdjusted, randomB);
__m256i burnA = _mm256_cmpgt_epi16(fAdjusted, randomA);
__m256i burnB = _mm256_cmpgt_epi16(fAdjusted, randomB);
```

The operand order is **threshold > random**, equivalent to random < threshold. XORing both operands with `0x8000` maps unsigned ordering onto signed ordering. For example, unsigned 0 becomes signed -32768, and unsigned 65535 becomes signed 32767. Reuse the same adjusted random vectors for both thresholds.

## 10. `_mm256_packs_epi16(a, b)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_packs_epi16)

**Name:** `_mm256` = 256-bit SIMD; `packs` = pack with signed saturation; `epi16` = source elements are packed 16-bit integers. The outputs here are 8-bit integers.

Narrow two vectors into one, clamping to the signed byte range.

```cpp
__m256i isGrowing = _mm256_packs_epi16(growA, growB);
__m256i isBurning = _mm256_packs_epi16(burnA, burnB);
```

Our inputs are only -1 (`0xFFFF`) or zero, so they become `0xFF` or `0x00` exactly. Pack the comparison masks, not the raw random values. Unsigned saturation would turn -1 into zero and lose the true masks.

Each 128-bit half is packed separately. With elements listed from low to high, the resulting byte order is:

```text
[ A0..A7 | B0..B7 | A8..A15 | B8..B15 ]
```

For this design, that order assigns random outcomes to cells. No shuffle is needed: pack both probability masks identically. A scalar correctness comparison must use that same assignment of random values to cells.

## 11. `_mm256_blendv_epi8(a, b, mask)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_blendv_epi8)

**Name:** `_mm256` = 256-bit SIMD; `blend` = select between inputs; `v` = selection comes from a variable vector mask; `epi8` = packed 8-bit integers.

For each byte, choose `b` when the mask byte's top bit is set; otherwise choose `a`.

```cpp
__m256i treeGrowth = _mm256_and_si256(isEmpty, isGrowing);
__m256i treeBurning = _mm256_and_si256(
    isTree, _mm256_or_si256(isPropagating, isBurning));

__m256i nextVector = _mm256_blendv_epi8(current, fireVector, treeBurning);
nextVector = _mm256_blendv_epi8(nextVector, treeVector, treeGrowth);
nextVector = _mm256_blendv_epi8(nextVector, emptyVector, isToBeEmpty);
```

Use comparison masks (`0xFF`/`0x00`), not cell values (`0`/`1`/`2`). A mask byte of 1 has its top bit clear and selects `a`. Store the selected cell values, not the masks.

## 12. `_mm256_storeu_si256(pointer, value)`

[Documentation](https://www.intel.com/content/www/us/en/docs/intrinsics-guide/index.html#text=_mm256_storeu_si256)

**Name:** `_mm256` = 256-bit SIMD; `store` = write memory; `u` = unaligned; `si256` = 256-bit integer vector.

Write all 32 bytes to memory without requiring 32-byte address alignment.

```cpp
_mm256_storeu_si256(
    reinterpret_cast<__m256i*>(next.data() + i), nextVector);
```

Keep the destination inside the interior row. Advance `y` by 32 and `x` by 1; swap grids once after all rows are complete.
