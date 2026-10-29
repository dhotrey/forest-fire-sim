# COSC3500 Milestone 2 — Presentation script (target: 9 min 25 s)

## S1 — Title (0:00 → 0:08)

Hello, my name is Aryan Dhotre, and this is my presentation for COSC3500 Milestone 2.

*(~8s, cumulative 0:08)*

---

## S2 — Forest fire cellular automaton (0:08 → 0:50)

The project I've chosen is a cellular-automaton-based forest fire simulation. It's a grid of cells that changes step by step using rules based on each cell and its neighbours.

An empty cell grows a tree with probability p. A tree ignites with probability f, or if a neighbour is burning. A burning cell becomes empty on the next timestep.

The figure shows one timestep, and the animation shows the simulation running for a 300 by 300 grid running simulated for 500 timesteps

*(~42s, cumulative 0:50)*

---

## S3 — Benchmarking methodology and startup information (0:50 → 1:35)

Before the optimisations, a quick note on benchmarking. I track versions with
git tags, compile at O3 for native arch, and measure elapsed wall-clock time
using `time`. Each configuration has five runs, and the charts show the minimum,
with shaded bands showing the range.

The slurm jobs log the node configuration at startup, as shown here.

>>>

Each binary also prints its version, compiler and build flags, so I can trace
results back to the build. Fixed seeds make runs repeatable within the same
version and thread configuration.

*(~45s, cumulative 1:35)*

---

## S4 — v1.0: serial baseline and double buffering (1:35 → 2:05)

My serial baseline takes 117.77 seconds for a square grid of side 8320 cells running for 500 timesteps.

While implementing the simulation I use two grids: one for the current state and one for the next state. Every update reads the current grid and writes to the next grid, so updates within a timestep don't affect their neighbours. Once the timestep is complete, I swap the buffers. That also makes parallel updates much easier later.

*(~30s, cumulative 2:05)*

---

## S5 — v1.1: replacing branches with masks (2:05 → 2:25)

The first optimisation is AVX2. My serial code has a lot of branches as you can see in the figure. To process multiple cells together, I replace those branches with masks that describe which cells satisfy each rule. Then I use those masks to select their next states.

*(~20s, cumulative 2:25)*

---

## S6 — Loading 32 one-byte cells (2:25 → 2:50)

This load reads 256 bits, or 32 bytes, from the grid. 
>>>

My cell type uses an eight-bit integer, so each cell occupies one byte. That means I can load 32 neighbouring cells into one vector and apply the update operations to
all 32 positions together.

*(~25s, cumulative 2:50)*

---

## S7 — Finding burning neighbours (2:50 → 3:40)

First I need to find which cells have a burning neighbour.
>>>

For this block of 32 cells, I load the cells above and below, plus the same row offset by one cell to the left and right. Each vector position now lines up with a neighbour
of the corresponding current cell.
>>>

I OR the four neighbour vectors together, preserving their state bits. 
>>>

Since fire is encoded as binary 10, ANDing with 2 isolates the fire bit. 
>>>

Comparing that result with 2 produces a byte mask showing where a burning neighbour exists, and zero otherwise.

*(~50s, cumulative 3:40)*

---

## S8 — Random checks and packing (3:40 → 4:40)

The AVX version of my RNG library produces eight random numbers at a time, but I need 32 for each block of cells. So I call it four times per block of 32 cells, compare each batch with the growth and fire probability vectors, and store the results in these two arrays of size four.
>>>

Next I pack these results into two 256-bit vectors: one for growth and one for fire, with one byte per cell.
>>>

Packing rearranges the results because the instructions work within 128-bit halves. I don't need to restore their original order because the random samples weren't assigned to particular cells beforehand. Both masks undergo the same rearrangement, so their growth and fire comparisons stay paired.

*(~60s, cumulative 4:40)*

---

## S9 — Turning the checks into rule masks (4:40 → 5:15)

next I apply some other simulation rules to the isGrowing and isBurning vector to get which indixes should have a tree growing and burning and empty in the next timestep


*(~35s, cumulative 5:15)*

---

## S10 — Blending and storing the next state (5:15 → 5:55)

Now I apply those masks using blending. For each byte, the blend selects the replacement value where the mask is true and keeps the existing value elsewhere.

The first blend turns selected empty cells into trees. The second turns selected trees into fire. The third turns cells that were already burning into empty cells.

All the masks came from the current state, so a newly grown tree can't ignite in the same timestep. Finally, I store the 32 updated cells in the next grid.

*(~40s, cumulative 5:55)*

---

## S11 — AVX results: processing width versus observed speedup (5:55 → 6:35)

On the same hardware, runtime falls from 117.77 seconds to 32.42 seconds. That's about 85 seconds saved, a 72.5 percent reduction in runtime.

Processing 32 cells together doesn't imply a 32-times speedup for the whole program. Updating that block takes multiple vector instructions, and the RNG
still needs four calls per block of 32 cells. Packing, memory access and work outside the vectorised loop also contribute to runtime.
The measured end-to-end speedup for this workload is about 3.6 times.

*(~40s, cumulative 6:35)*

---

## S12 — v1.3: OpenMP implementation (6:35 → 7:25)

Next I distribute the rows across threads with OpenMP. Both grids are shared, but during an update, threads only read the current grid and write separate
rows of the next grid. The probabilities are shared read-only values. Each thread has its own RNG and temporary vectors because those change while it works.

Generating a random number updates the RNG's internal state. If threads shared one generator, those updates would need synchronisation. Giving each thread its own generator avoids that shared mutable state.
>>

I create the thread team once and use static scheduling for the rows.
Keeping the team alive across timesteps avoids repeatedly entering a new parallel region. Static scheduling suits this workload because every row has the same number of cells and broadly similar work, so I can divide the rows evenly without dynamically assigning them as threads finish.
>> 

At each timestep, the loop's barrier waits for every row to finish. One thread then swaps the buffers inside the single block, whose closing barrier keeps everyone from starting the next timestep before the swap finishes. 

---

## S13 — OpenMP scaling and Amdahl's law (7:25 → 8:15)

For the same workload, runtime falls from 7.92 seconds with four threads to 4.02 seconds with eight threads.

With ideal scaling, doubling the threads would halve runtime to 3.96 seconds. The observed improvement is about 1.97 times, close to ideal over this range.

Double buffering helps because threads can update separate rows independently within each timestep. They still need to synchronise before and after the swap.
>> 

Amdahl's law says the serial fraction limits the overall speedup, even as we add more threads. Synchronisation and memory costs can also limit scaling. These results cover four to eight threads but they don't establish scaling beyond eight threads

*(~50s, cumulative 8:15)*

---

## S14 — Combined results (8:15 → 8:40)

Putting both changes together, runtime falls from 117 seconds for the serial baseline, to 32.42 seconds with AVX, to 4.02 seconds with AVX and eight threads.

That's about a 29.3-times overall speedup for this workload. A simulation that took nearly two minutes now finishes in about four seconds.

*(~25s, cumulative 8:40)*

---

## S15 — Reflection on correctness and conclusion (8:40 → 9:25)

Checking correctness is really hard here. AVX uses eight RNG streams, and OpenMP gives each thread its own RNG with a different seed. This changes which
random samples reach each cell, so matching final grids from these seeded runs isn't a suitable correctness test.

Instead, I manually checked the code against the cell-update rules and visually inspected the simulation running on a smaller grid to see whether those rules were being applied correctly.

The code inspection let me check how the masks implement growth, ignition and burning cells becoming empty. The visualised output let me check the resulting behaviour on the grid. These were manual checks, so they give me confidence in the implementation, but they don't establish correctness for every possible grid and random input.

>>

Overall, AVX processes 32 cells together, while OpenMP distributes the rows across threads. Together, these changes reduced this workload from nearly
118 seconds to four seconds which is incredible. 

*(~45s, cumulative 9:25)*

---

## S16 — AI disclosure (display only)

I did use AI to assist me with writing supporting code for this project such as scripts that visualise my simulation and code for animations in this presentation among other things. 

---

## S17 — Bibliography (display only)

And here's the references

Thank you for your time. 
