# Building a traceable CPU simulator in Python

For my CS104 computer architecture project, I built a small MIPS-style CPU simulator. It takes one file of instructions and another file of initial memory values. Each executed instruction prints the fetch, decode, execute, memory access, and write-back steps, making state changes visible.

The CPU has eight registers and a byte-addressed program counter. Its instruction set covers arithmetic (`ADD`, `ADDI`, `SUB`, `SLT`), control flow (`BNE`, `J`, `JAL`, `HALT`), and memory (`LW`, `SW`). The cache can be enabled, disabled, or flushed with `CACHE`. It holds four entries, evicts the oldest entry when full, and writes stores through to main memory.

The demonstration loads 4 and 5 from memory, adds them to 9, and stores the result. It then reads the result from cache, flushes the cache, and reads it again from main memory. A conditional branch skips an instruction that would otherwise add 99, and `JAL` records its return address in `R7`. This makes arithmetic, memory, cache, and control-flow behavior observable in one short run.

The biggest design choice was keeping parsing, memory storage, cache behavior, and CPU execution in separate components. This lets the same simulator run Codecademy's supplied inputs or a more complete demonstration without changing the code. I also added an instruction limit so a bad jump cannot trap the program forever.

The simulator is intentionally educational. It models instruction semantics rather than binary encoding or cycle-level pipelining. A future version could add fixed-width overflow, a branch-delay slot, and cycle timing to compare cache strategies.

