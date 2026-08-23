# v0.0

This is the baseline. This is how the code came to me in my dream and I've just recreated it in main.cpp without any additonal thought. The idea is to just make the simulation work first and successive versions will work on making it faster.

## Observations:

Something very strange is happening. When this is compiled with GCC 15 , the o1 and o2 results are roughly similar but GCC 15 is only available on my laptop and on rangpur we have GCC 8.x and there o2 is ~80% slower than o1. The results are in data/v0.0/benchmarking/benchmarks-o1-o2.csv

Also asked about it on edstem - https://edstem.org/au/courses/38439/discussion/3524615

optimisations aside, i ran gprofng on the code with o1 [results](data/v0.0/gprofng/o1.txt) and found that the RNG eats 37% of the runtime

```txt

Excl. Total   Incl. Total    Name
CPU           CPU
 sec.      %   sec.      %
6.114 100.00  6.114 100.00   <Total>
3.823  62.52  6.114 100.00   main
2.292  37.48  2.292  37.48   std::mersenne_twister_engine<unsigned long, 32ul, 624ul, 397ul, 31ul, 2567483615ul, 11ul, 4294967295ul, 7ul, 2636928640ul, 15ul, 4022730752ul, 18ul, 1812433253ul>::operator()()
0.      0.    6.114 100.00   __libc_start_main
```

This is unacceptable. in the next version im going to fix the rng.

# v0.1

found this library to generate prng https://github.com/wjakob/pcg32, it has an optimised SIMD / AVX version as well that i can use for milesone 2.

After switching out the heavy rng library to the pcg32 one v0.1 at o1 optimisation runs in 3.28s for 1000x1000 grid. for comparison in v0.0 this was at 6.10s so this one change has almost slashed the runtime in half.

# v0.2
