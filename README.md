# CPU simulator (CS104 portfolio project)

This local Python project simulates a small MIPS-style CPU. It loads a comma-separated instruction file and a separate memory-initialization file, then traces fetch, decode, execute, memory access, and register write-back. No external packages are needed.

Run the complete demonstration:

```sh
python3 cpu.py examples/demo_instructions.txt examples/demo_data.txt
```

Run Codecademy's supplied starter inputs:

```sh
python3 cpu.py examples/codecademy_instruction_input.txt examples/codecademy_data_input.txt
```

The supplied program jumps to instruction index 8 although it contains only five instructions. The simulator reports that the program counter has left the loaded program. The separate demonstration reaches `HALT` and exercises arithmetic, branching, a jump with link, memory reads and writes, cache hits, cache misses, and a cache flush.

Test the simulator:

```sh
python3 -m unittest -v
```

## Input format

Each instruction is one CSV row: `OPCODE,OPERAND,...`. Empty lines and lines beginning with `#` are ignored. Register names are `R0` through `R7`; `R0` always reads zero and ignores writes. The program counter is byte-addressed, with one instruction per four bytes. `J` and `JAL` targets are zero-based instruction indices; `BNE` uses an offset relative to the following instruction.

The memory file has `ADDRESS,VALUE` rows. Eight-character binary addresses, as used by Codecademy's supplied data, are decoded as binary. Other addresses and values are decimal or `0x`-prefixed hexadecimal integers. Uninitialized memory reads as zero; negative addresses are rejected.

Supported instructions: `ADD`, `ADDI`, `SUB`, `SLT`, `BNE`, `J`, `JAL`, `LW`, `SW`, `CACHE`, and `HALT`. Memory operands use `offset(Rs)`. `CACHE,0` disables the cache, `CACHE,1` enables it, and `CACHE,2` flushes it. The four-entry cache is fully associative, uses FIFO replacement, and writes through to main memory. This is an educational model: it does not implement real MIPS binary encoding, 32-bit overflow, a pipeline, or cycle timing.

## Design notes

`CPU` owns the register file and program counter. `MemoryBus` stores word values at integer addresses. `Cache` mediates loads and stores, tracks hits and misses, and uses Python dictionary insertion order to evict the oldest entry. CSV parsing is kept separate from execution so the same CPU can run any loaded program. The instruction limit prevents an accidental infinite loop.

Read the [project write-up](blog.md) for a walkthrough of the simulator and its design decisions.
