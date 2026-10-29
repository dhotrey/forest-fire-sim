# S1

hello, my name is Aryan Dhotre and this is my presentation for COSC3500 milestone 2

# s2 - forest fire celular autoama

The project I've decided to work on is a cellular automata based forest fire simulation. A cellular automaton is a grid of individual cells that changes step-by-step over time by following a simple set of rules based on the states of neighboring cells.
In a forest fire cellular automaton A tree grows on an empty cell with a probability p, A tree ignites with a probability f, A tree will burn if one of its neigbours is on fire,A burning cell turn into an empty cell.
A single timestep of this interaction is visualised in the Fig 1 and a visualisation on the right shows the simulation running on a 300x300 grid for 500 timesteps where the probability of tree growth is 0.01 and the probability of fire is 0.001

# s3 - benchmarking methodology

Quick note on methodology before the optimisations. Everything's tracked in git using tags, I try to contain one optimisation per version tag. I compile each version at -O3 with march=native, time it with time, and take the minimum of 5 runs to cut noise.
I run untimed warm up passes first so the first binary tested isn't unfairly penalised by cold caches, and every run uses the same RNG seed, so results are deterministic, but more on that later.
At the start of each job i also print the node configuration in maximum detail to help with debugging later if required , as shown in the image

# s4 - program startup

Each binary also prints its own build info version info, compiler version and build flags flags to stdout, which makes it much easier to tell log files apart later.

# s5 - v.1.0 - the serial baseline

v1 represents the serial baseline that i would compare all my optimisations to for the rest of the presentation. This is the fastest i could get my code to run using a serial implementation compiled with o3 and march=native.
for my problem size of 8320x8320 grid for 500 timesteps , my serial baseline ran the simulation in 117.77 seconds.

I would also like to point out that in this implementation i am double buffering the updates. Basically I keep two copies of grid, one for the grid during the current timestep and another for the state of the grid during the next timestep, and while this does 2x my memory usage it makes computing the next state very simple because cell updates within a timestep do not have any effects on their neighbours.

# s6 - v1.1 - avx

The first barrier to implementing AVX is the amount of branches my serial code has, and AVX isn't really fond of such branching code. So to implement AVX , I'm going to have to resort to branchless programming with [masking](https://en.algorithmica.org/hpc/simd/masking/). The flow chart on the right shows roughly the control flow diagram for the hotloop of my forest fire simulation.

# s7 avx

Now to start with , the `__m256i current = _mm256_loadu_si256(reinterpret_cast<const __m256i *>(grid.data() + idx));` instruction allows us to load in 256 bits of/from memory(?). {manim drawing of writing out this intrinsic on the screen and just 256 bits of memory}. This means with a 4 byte int we can fit 8 ints in here at a time. {manim drawing segments the 256 bits into 8 sections to show we can fit 8 ints at a time}. But since one cell of my sim is actually defined using 1 byte ints {draw`enum class CellState : std::uint8_t { Empty, Tree, Burning };` on screen } we can actually fit 32 cells at the same time {the 8 ints now segment into 32 sections instead each being 8 bits}

# s8 avx - con't

Now for the first check we actually need to see if any neighbours are on fire to see which states this will propogate to. To do this we need to check if any of the neighbors are on fire {animate just 5 grids in a + formation}. This still holds with 32 cells. {The + transitions to like a 20x20 grid with each cell labelled on the left of the screen. each cell should be labelled and should be populated randomly with 0,1,2 . Also keep like a legend on the top left showing 0 is empty 1 is tree and 2 is fire just as a reference} first we need to fetch the current row that's being processed {fetch one row from the middle towards the right of the screen} and the rows above and below {move the rows above and below to the right of the screen} we also need every element that's to the left and right of every elemt for the `current` row we're processing. To do that we can just fetch the row off by one on either side of the current row {fetch the left and right rows and move them towards the right of the screen} {all the up,down,left,right rows must be on top of each other}. Next to determine which of cells from current ignite due to a neighbour being on fire we need do an OR and this or will basically check which cells even have ANYTHING in them. {perform an OR on the all those 4 vectors and show the resultant vector at the bottom , have an OR between all 4 vectors and when you're doing the or animation write out the intrinsic _mm256_or_si256() on the left part and remove the grid that was there} {next transition bring the resultant vector to the center of the screen} this gives us the cells that aren't empty amongst our neighbours .

# s9

Now that we have which cells neighbours aren't empty we will check which ones are on fire. to do that we need to create a fire vector {const __m256i fireVector = _mm256_set1_epi8(2); appears and the corrosponding cells to go with it} and we will AND it with this vector { put these two vectors next to each other , perform an AND }. This leaves us with the cells that do have a neighbour on fire and then we create a mask using this vector by comparing it to { render _mm256_cmpeq_epi8 on screen and do the equality comparion beween the vector from the last step and render the resulting mask}

# s10
Now that we have computed which cells the fire spreads to, we need to move on to the rng part. the library im using for this project pcg32 offers an avx implementation , but it only gives me 8 random numbers at a time. to deal with this for each timestep i call the rng function 4 times to have 1 random number generated per cell being processed and compare it with BOTH p and f vectors. here p and f vectors are basically me casting the pobablity of a tree growing and the probablity of a fire starting to all cells of the vector {clear the screen and show the creation of p and f vector}. {next show one iteration of the loop of comparing with p and f vectors using the intrinsics there and writing it to growthchecks array growthChecks[i] = _mm256_castps_si256(_mm256_cmp_ps(randoms, pVector, _CMP_LT_OQ)); fireChecks[i] = _mm256_castps_si256(_mm256_cmp_ps(randoms, fVector, _CMP_LT_OQ));} {and then show the mask? we have for both growthChecks and fireChecks array when we do this with all random numbers}

# s11
Now that we have calculated both fire and growth checks for every cell we need to combine the 4 elements of growth checks array and of the fire checks array using the packing intrinsic {so basically illustrate how __m256i isGrowing = _mm256_packs_epi16(_mm256_packs_epi32(growthChecks[0], growthChecks[1]),_mm256_packs_epi32(growthChecks[2], growthChecks[3])); works for the growth, thing capture the nuance that it doesn't work across lanes and the result of packing all elements kind of jumbles them as it doesn't work across lanes} as you can see from the illustration packing the 4 elements into a single _m256 type jumbles them up but it's fine because we're dealing with random numbers here and it's not like those random numbers were generated for that particular cell {and now you can render the fire check packed mask as well next to the isGrowing vector}
