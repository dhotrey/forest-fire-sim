# Nodes on making various optimisations

# Lecture 2 - Architecture

- Review the lecture to see how to best structure your code to utilise cpu cache so that you don't hit RAM as often

# Lecture 3 - Optimisations and Profiling

- Tradeoff between CPU and Memory: Sometimes it won't be worth it to cache certain data because the memory bandwidth to fetch that data from the RAM will be too much and you might get better performance just recalculating the data every time.

  - generally , focus on memory bandwidth rather than optimising for one or two instructions as you'll be memory bound rather than compute bound. since all modern CPUs can process faster than the fastest RAM.

## Optimisations

### Compiler optimisations

- O0(no optimisatoin) : less compile time, less memory requirement
  - could be beneficial to use this to see if changes in the code are actually helping or not.

- O1(optimise) : Basic optimisation. optimises most obvious things not to fast

- O2 (optimise more) : Most optimisations that don't trade space/speed
- O3 (optimise yet more) : try to auto vectorise codde + O2
- Ofast : O3 + less accurate math. could be useful if dealing with a bunch of float point optimisations.

### Math

- mostly not relavent to what im working on
- ffast-math : to the compiler to use the fast math library to trade precision for speed, the result is not quite right but close enough. Could also use fastmath lib in code , eg fastsinf(x) instead of sinf(x)

- integrate calculations : do related calculations together.

### Remove loop invariant code

- basically remove operations from inside the loop that don't need to happen inside the loop.

### Exit loops early if possible

- pretty self explainatory

### Use lookup tables / precalculate

- make the lookup table as big as it needs to be but no bigger. will loose a lot of benifits of cache if the cache itself lives on the RAM and not in the cpu cache

### Copy propogation

```cpp
float y = x;
float z = 3 + y;

// rewrite this as
float z = 3 + x;
```

### Dead code removal

- if a calculation isn't being used anywhere , don't calculate it.

### variable resule vs extra variable

- could make the prf better or worse, need to benchmark and check for use case
  - can limit parallelsim and make code slow
  - could reduce memory bandwidth and make code fast

### common subexpression.

- don't recalculate intermediate values , just calculate it once and reuse it multiple times.

### induction variable simplification

- could be useful when i transition from a 2d grid to a 1d grid
  example the following example

```cpp
for (int i = 0; i < N; i++){

    k = i * 4 + m; // multiply + add called N times
    // do work.
}
```

can be written as follows

```cpp

k = m;
for(int i = 0;i<N;i++) {
    k += 4 // add constant called N times.
    // do work
}

```

in the above example now instead of a multiplicaiton and addition , we're just adding by a constnat in each loop iteration. Taking advantage of the fact that in the previous loop iterations the value of the next iteration is partially calculated for us.

### Strength reduction.

- replace expensive calculations with a cheaper one that does the same thing

eg:

```cpp

y = pow(x,2); // instead of this

y = x * x; // do this

// ------or------

y = 2 * x; // instead of this
y = x + x; // do this


```

- addition being faster than multiplication usually true for ints,
- but for floats it reallly depends on a lot of things.
- ref L3 : ~30 minute mark for explaination
- multiplication also usuallly faster than division like 10-20x faster.

### Inlining

- move function calls directly inline insead of calling function/methods.
- rather than call a small funciton, move it's contents directly onto the line because the overhead of calling a function can be more than the work that function is doing.
- can make code unreadable and unmaintainable
  - a workaround is using a macro instead of a function call to keep readability but also the speed improvement of having stuff inline

- Can also suggest the compiler to inline the funciton call!

```cpp

inline float madd(float a,float b, float c) {
    return a+b*c;
}

madd(a,b,c) // the compiler will auto inline this funciton for you during comptime. this is non deterministic. the compiler may or maynot do it based on how it's feeling that day.
```

### Loop unrolling

- the overhead of having a loop could be more than the work being done inside the loop

- unrolling the loop means to do more work per iteration and doing less iterations overall.

eg instead of

```cpp
for (int i = 0; i<N;i++){
    a[i] = a[i] + b[i] * c;
}

```

do this that does 4x the work in each iteration.

```cpp
for (int i = 0; i < N; i += 4)
{
    a[i]   = a[i]   + b[i]   * c;
    a[i+1] = a[i+1] + b[i+1] * c;
    a[i+2] = a[i+2] + b[i+2] * c;
    a[i+3] = a[i+3] + b[i+3] * c;
}
```

if N isn't divisible by 4 or whatever factor that's being chosen to the degree to which the loop is being unrolled , need to deal with the end case as a separate loop

```cpp
int rem = 4 * (N / 4);
for (int i = rem; i < N; i++)
{
    a[i] = a[i] + b[i] * c;
}
```

### Loop conditionals

move conditionals outside the loop , instead of inside the loop if possible , so we only have to evaluate the conditionals once before the loop and that work doesn't get done N times inside the loop.

example instead of doing this ↓

```cpp
for (int i = 0; i < N; i++)
{
    if (k == 0)
    {
        a[i] = a[i] + b[i] * c;
    }
    else
    {
        a[i] = 0;
    }
}
```

do this instead ↓ that uses the k branch outside the loop and not inside the loop

```cpp
if (k == 0)
{
    for (int i = 0; i < N; i++)
    {
        a[i] = a[i] + b[i] * c;
    }
}
else
{
    for (int i = 0; i < N; i++)
    {
        a[i] = 0;
    }
}
```

also for loops that just initialise the whole array to 0 , a common operation that could be done after initialising the value of the loop. That can instead be done using `memset`

-> `memset(a,0,sizeof(float)*N);`
note: memset is on a per byte basis not a per element basis. could be finiky on setting non zero values.

Also try to branch outside the loop rather than inside the loop, so indead of doing something like

```cpp
for (int i = 0; i < N; i++)
{
    for (int j = 0; j < N; j++)
    {
        if (j < i)
        {
            a[i][j] = a[i][j] + b[i][j] * c;
        }
        else
        {
            a[i][j] = 0;
        }
    }
}
```

write it as two separate loops

```cpp
for (int i = 0; i < N; i++)
{
    for (int j = 0; j < i; j++)
    {
        a[i][j] = a[i][j] + b[i][j] * c;
    }

    for (int j = i; j < N; j++)
    {
        a[i][j] = 0;
    }
}
```

Now these two separate loops can be parallelised since both loops are independent of each other.

### Reduction operations.

Also not particularly relavent for my project i don't think.

- eg min,max,sum, etc on an array. for these operations, the following optimisations can be considered.
  - unroll loop by factor of 2,4,8 etc
  - split the array into chunks
  - keep track of min/max/sumValue in each chunk.
  - might perform worse serially but code is now more prone to parallelism. SIMD,MIMD(threads)

### Type conversions

- don't convert between types unless it's absolutely necessary.

### Let the compiler do what it can

- Avoid doing anything that might prevent the compiler from optimising your code. like conditionals inside the loop might prevent the compiler from auto vectorising the code
- Also try to limit interdependence.
- Try not to have ambigous use of pointers.

### Memory access patterns that efficiently exploit cache.

Extremely relavent to what my code does ref L3: ~46 minute mark

We want to access memory with spatial and temporal locality. We want to address nearby memory addresses at nearby points in time
example :

Basically we want to access the memory how it's laid out in the cpu cache lines. c uses row major format and basically fetches rows of arrays from the ram into the cache so an operation that works on the following items such that [1,2,3,4,5] we access them from left to right i.e. from 1 -> 5 is better than having something that tries to access 1,6,11 then 2,7,12 etc from the matrix below in succession because when the cpu pulls 1 from the ram, it also has the ENTIRE row sitting in the cache that just gets wasted and has to be pulled back into ram later.

```
[[1,2,3,4,5],
[6,7,8,9,10],
[11,12,13,14,15]]
```

Accessing memory that's spacially adjacent also makes the code prone to SIMD optimisations.

sequential v non sequential access can lead to ~8x speed improvement - at least on the instructors hardware. -> just with autovectorise

on hand vectorising the code , that lends an additonal 2x speedup on the example being talked in the slide.

## Profiling

Optimise sections of code that take the longest, don't devote time to optimise the code that is a very small fraction of the runtime.

### Code instrumentation

Amdahl's Law : max possible theoritical speedup is limited by the portion of your code you can't optimise/throw more resources at.

#### Logging cde added to function calls - manually

Be careful here, the resolution of the timer could be OS, hardware and/or compiler dependent. Important when measuring tight loops of short duration. (some timers only ~10ms resolution)

```cpp
std::chrono::steady_clock::time_point startTime = std::chrono::steady_clock::now();

doWork();

std::chrono::steady_clock::time_point stopTime = std::chrono::steady_clock::now();
std::chrono::duration<double> time_span =
    (std::chrono::duration_cast<std::chrono::duration<double>>(stopTime - startTime));

double dt = time_span.count();
```

Note : profiling and logging time adds overhead to the code that could make the overall runtime slower.

#### Sampling - statistical profilers

the downside is that it isn't deterministic

- regularly interrupts the code to see what's running/mem usage

#### gprof

uses both instrumentation and sampling

- compile with `-pg` flag and turn off optimisations `-O0`
  - instead of `O0` can do `-no-pie-fno`

- run the executable after compiling with -pg
- run `gprof PROG gmon.out > analysis.txt`

- call graph profile output shows the call graph of the program
