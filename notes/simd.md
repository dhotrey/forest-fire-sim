# simdeez nuts

worth learning and internalising the concept of aligned memory

# compiler at -o3

compiler can only do so much, even by unrolling the loop by a factor of 4/8 it usually struggles

# avx intrinsics

these are special functions that map ~directly onto specific assembly instructions but the details still left up to the compiler.

works something like thsi

```
A256:          [ A[i]  A[i+1] A[i+2] ... A[i+7] ]
                  +       +      +          +
sumTotal256:   [ s0      s1     s2    ...   s7    ]
                  ↓       ↓      ↓          ↓
sumTotal256:   [s0+A[i]  ...             s7+A[i+7]]
```

to use this include the `<immintrin.h>`

if you're going to work with 256-bit AVX vectors, it's preferable for their addresses in memory to line up nicely with 32-byte boundaries.

eg

```cpp
__m256* A = (__m256*) malloc(sizeof(__m256) * N); // this is unaligned
```

using aligned allocation instead we get

```cpp
__m256* A = aligned_alloc(ALIGN, sizeof(__m256) * N);
```

There's a few types of avx operations available to us

- arithmetic
- bitwise ops
- broadcast/gather/scatter - could be useful for bitwise ops for performing the masking ops and creating a new vector?
- memory load/store
- comparisons - can't really fix conditionals and branching here but this can be used to perform boundry checks for my grid instead of having a buffer making more efficient memory use
- permute/blend/insert/extract - data rearrangement
- broadcast/gather/scatter - could be useful for bitwise ops for performing the masking ops and creating a new vector?
- there's some type casting and initialisation avx funcitons too
- there's also intrinsics available for math and fastmath lib i.e. using approximations

### AVX Addition — `_mm256_add_ps`

```cpp
__m256 _mm256_add_ps(__m256 a, __m256 b);
```

| Vector `a` | a₇    | a₆    | a₅    | a₄    | a₃    | a₂    | a₁    | a₀    |
| ---------- | ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| Vector `b` | b₇    | b₆    | b₅    | b₄    | b₃    | b₂    | b₁    | b₀    |
| **Result** | a₇+b₇ | a₆+b₆ | a₅+b₅ | a₄+b₄ | a₃+b₃ | a₂+b₂ | a₁+b₁ | a₀+b₀ |

### AVX Fused Multiply-Add — `_mm256_fmadd_ps`

```cpp
__m256 _mm256_fmadd_ps(__m256 a, __m256 b, __m256 c);
```

Performs **element-wise multiplication followed by addition** on 8 packed 32-bit floats:

`result = (a × b) + c`

|            | Lane 7  | Lane 6  | Lane 5  | Lane 4  | Lane 3  | Lane 2  | Lane 1  | Lane 0  |
| ---------- | ------- | ------- | ------- | ------- | ------- | ------- | ------- | ------- |
| `a`        | a₇      | a₆      | a₅      | a₄      | a₃      | a₂      | a₁      | a₀      |
| `b`        | b₇      | b₆      | b₅      | b₄      | b₃      | b₂      | b₁      | b₀      |
| `c`        | c₇      | c₆      | c₅      | c₄      | c₃      | c₂      | c₁      | c₀      |
| **Result** | a₇b₇+c₇ | a₆b₆+c₆ | a₅b₅+c₅ | a₄b₄+c₄ | a₃b₃+c₃ | a₂b₂+c₂ | a₁b₁+c₁ | a₀b₀+c₀ |

- `__m256` = **256-bit vector containing 8 × 32-bit floats**
- `_ps` = **packed single-precision** floating point
- FMA performs the multiply and add as **one fused operation**
- Corresponding instruction shown: `vfmadd132ps`
- Useful for operations such as **dot products and matrix multiplication**

fmadd is quite expensive tho

# simd enables branchless programming (wtf?)

this is so weird i don't really understand it but if there's a need to revisit it refer SIMD lecture ~37min mark

# permute shuffle 
not really relevant to a1 or m2, if needed covered in the lecture at ~43min mark. 

# complex dot product.
implementation and explaination in lecture - not sure why but its there. 