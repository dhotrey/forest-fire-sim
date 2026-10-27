# S1

hello, my name is Aryan Dhotre and this is my presentation for COSC3500 milestone 1	

# s2 - forest fire celular autoama
The project I've decided to work on is a cellular automata based forest fire simulation. A cellular automaton is a grid of individual cells that changes step-by-step over time by following a simple set of rules based on the states of neighboring cells. 
In a forest fire cellular automaton A tree grows on an empty cell with a probability p, A tree ignites with a probability f, A tree will burn if one of its neigbours is on fire,A burning cell turn into an empty cell.
A single timestep of this interaction is visualised in the Fig 1 and a visualisation on the right shows the simulation running on a 300x300 grid for 500 timesteps where the probability of tree growth is 0.01 and the probability of fire is 0.001

# s3 - benchmarking methodology
Before i get into explaining the code and the optimisations. I just want to explain the benchmarking methodology. I have been using git to keep track of changes in my code and I have tried to contain each optimisation to a git tag, so my tags go from v0.0 to v1.0. Apart from this I use the `time` command to benchmark the runtime of my program. each version is compiled using -o1 and o2 and each version is ran 5 times. I run both versions 15 times to account for server noise , and other factors that might cause a false measurement and consider the lowest score from the 5. I run each optimisation level with in 3 configurations , mainly changing the grid size parameter. I run it for 100x100, 500x500 and 10000x10000 . This is to measure the impact of cache hits and to have a larger training run in genera. In this presentation I will be discussing the results of the 10000x10000 grid ran for 500 timesteps. Since my program relies on random number generation. I also seed each run with the same number to have determinsistic results

All the benchmarks for a particular version are ran in the same slurm job so basically the slurm job runs my program 30 times on different optimisation levels with the same parameters and between versions I try to submit jobs to the same partition. This is done that all benchmarks from the same versions run under the exact same conditions and the only difference is the optimisaition level and not accidentally landing on a different cpu core etc. In the slurm scripts i also try to print out as much info about the node as possible so that it might help me debug/investigate any results after a script has been ran. In 

The warmup runs serve to **populate CPU caches and branch predictors** so that timed runs are comparable between different optimization configurations.

There are two levels:

1. **Size-1 warmup** (lines 141-147): Trivial run to load the binary itself into the instruction cache and set up the process.

2. **Grid-sized warmup** (lines 150-159): Full-scale untimed runs (`WARMUP_REPS=2`) for each grid size before the actual benchmark repetitions begin.

Without these, the first binary measured would run with cold caches while later binaries would benefit from residual data in cache, making the comparison unfair. 

# s4 - program startup
I also print a small splashscreen from my program that tries to capture the model configuration to the stdout. This is to make interpreting results from logfiles easier and reduce confusion. 
I am aware that since I use `time` to benchmark it also accounts for time to print the splashscreen to stdout but since this is a constant in all versions of my program and does not interfere with the %change in runtime measurements i take.


# s5 - v.0.0
Let's discuss the initial version of my code.
this image is the roughly the main meat and potatoes of my simulation. It is very simple but something very strange is happening when I benchmark this code with o1 and o2 optimisation flags. binary compiled with o2 is ~80% slower than o1. I have visualised the results in the bar chart below and we can se that o1 is consistently faster than o2 at all grid sizes. This appears to be a bug with GCC 8.5 which is available on the cluster as I did not observe the same performance hit on GCC 15 where the runtime of o1 and o2 was mostly comparable. 


# s6 - v0.0 - gprofng
I ran gprofng on o1 to find out that the mersene twister engine the thing im using for rng is eating 37% of the cpu time so of the 6 seconds my program is running for , it's only generating random numbers for 2 whole seconds.
There was no useful finding by running gprofng on o2 optimised code because i think the compiler just inlines all the code from the mersene twister engine into main so all the time just shows up into main. 

the takeaway was that there's no reason that rng generation in my program has to be so slow. This is not a simulation where rng is critical and the Mersenne Twister (mt19937) is considered slow compared to modern (PRNGs). 
My first optimisation will focus on getting rid of mt19937 and replacing it with something more lightweight

# s7 - v0.1
    
moving to pcg32 -> is a lightweight, high-performance pseudo-random number generator that achieves excellent statistical quality. We see drastic improvements in o1 and o2 runtime and finally o2 is faster than o1. It seems like the anomaly from v0.0 is gone now. 

# s8 - v0.2

Fixing cache access patterns. 
I changed the loop order so the inner loop traverses the contiguous y elements within each std::vector, improving spatial locality and reducing cache misses.
This means data loaded into a cache line is more likely to be reused by the next iterations instead of repeatedly jumping between separate memory allocations.

At this point we can see that the 100x100 grid with the `time` is a very small sample to run and time command does not give us enough resolution to determine any performance gain between the two optimisation levels so we'll be focusing on a 1000x1000 grid size from now on where o2 still shows a massive performance gain.

We can see that the runtime of the simulation continues to fall quite a bit by such a small change. o2 has gotten 32% faster than the previous version. 


# s8 & s9 v0.2 - cachegrind

Further more we can inspect the cache access patterns to see what difference this has made to the cache access with valgrind. 
In v0.1, the D1 cache, which is the L1 data cache, had approximately 1.38 billion misses, giving a D1 miss rate of 32.7%. The high miss rate validates the hypothesis that the original implementation was making poor use of the L1 cache.In v0.2, I reversed the loop order so that the inner loop changes y. This means I now traverse the contiguous elements within each inner vector, giving much better spatial locality.The effect is very significant. D1 cache misses dropped from approximately 1.38 billion in v0.1 to just 16.45 million in v0.2, which is a reduction of approximately 98.8%. The D1 miss rate also dropped from 32.7% to just 0.4%. This shows that the new traversal order is making much better use of the L1 data cache.LLd misses were approximately 43,547 in v0.1 and 43,549 in v0.2. So the optimisation isn't a silver bullet

# s10 v0.3 - easy wins
In v0.2 I'm calling rng at the top of the switch case, but this is not the most optimal stratergy as we don't require rng when a tree is burning or has a burning neighbour . We only need rng calls for an empty grid cell or a grid cell that already has a tree. 

# s11,s12 v0.3 - the numbers
So now in v0.3 on the right I'm only calling the rng when it's actually gets used. [1] “Forest-fire Model.” Accessed: Aug. 27, 2026. [Online]. Available: https://itp.uni-frankfurt.de/~gros/StudentProjects/Projects_2020/projekt_lars_dingeldein/
[2] B. Drossel and F. Schwabl, “Self-organized critical forest-fire model,” Phys. Rev. Lett., vol. 69, no. 11, pp. 1629–1632, Sep. 1992, doi: 10.1103/PhysRevLett.69.1629.
[3] “The ‘Gru With a Gun’ Meme and the ‘Gru No’ Meme Come From a Doki Doki Literature Club Meme. : r/TheMatpatEffect.” Accessed: Aug. 27, 2026. [Online]. Available: https://www.reddit.com/r/TheMatpatEffect/comments/1rpku7c/the_gru_with_a_gun_meme_and_the_gru_no_meme_come/
[4] W. Jakob, wjakob/pcg32. (Jul. 23, 2026). C++. Accessed: Aug. 27, 2026. [Online]. Available: https://github.com/wjakob/pcg32

Interestingly, that was not what happened. At -O1, the change actually worked: performance improved by about 5–6%. But at -O2, performance got around 17% worse.

With -O2, the compiler was inlining the RNG into multiple conditional paths, which changed the structure of the hot loop. 
I decided to benchmark the branch prediction statistics with valgrind
The results were pretty interesting: v0.3 executed about 6% more instructions and 26% more branches than v0.2. So even though I was doing fewer RNG calculations, I was actually generating more work overall in the hot loop.
So I decided not to pursue this change further and instead focus on optimisations that give a more consistent benefit on the target GCC 8.5 -O2 environment

# s13-14 v0.4
Since the previous change resulted in a perf deg. 0.4 will roll this back. Along with that. Also i'll do an integer threshold compare instead of float. since pcg32 internally calls next_uint, i can directly call that function instead of having to go through the float comparsion. 
basically precompute `p_threshold`/`f_threshold`, compare against `nextUInt32()` directly. I believe this will save me time because nextfloat function internally calls nextint32 anyways. So I can just save on that.
This has improved performance slightly. Excluding the results of v0.3 we can see that this change has led to a 8.4% speedup in o2 optimisation level

# s15 v0.5 
Moving from a 2d grid to a 1d grid also feels like a fairly obvious optimisation. This also changes the grid indexing pattern. Since this change affects the correctness of the simulation. To make sure i ended up with the same simulation, I computed a hash of the 2d grid implementation at the end of 500 timesteps and then basically compared it with the hash of the 1d grid implementation. This helped prove with confidence that the refactor did not break functionality. 

I also ran cachegrind on the this new implementation to see how it affected cpu cache utilisation patterns, I found that the 1D implementation performed substantially fewer data-memory accesses. the total number of data references dropped from around 3.7 billion to 1.7 billion — roughly a 54% reduction., and writes dropped from about 1 billion to around 500 million.This suggests that the optimisation significantly reduced overall memory traffic without introducing a substantial deterioration in cache locality.

On the runtime, for o2 this has only resulted in a minor 2% improvement while for o1 this is once again a big reduction of 10% from the previous version



# s16 v06-v0.7 - things that didn't work 
For v0.6 I just thought that inducitonv variable slimplifaction would reduce my runtime, it did not do that i guess the compiler does it better. similarly for v0.7 i tried to pack my 1d grid so that each cell instead of being 1 byte would only be 2 bits since it only cycles between empty,burning and tree and this reduced the cache size drastically but runtime still went up

















