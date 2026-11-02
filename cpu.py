"""Small, traceable MIPS-style CPU simulator for the CS104 portfolio project."""

from __future__ import annotations

import argparse
import csv
import re
from dataclasses import dataclass
from pathlib import Path


REGISTER_COUNT = 8
ADDRESS_PATTERN = re.compile(r"^([+-]?\d+)\((R[0-7])\)$", re.IGNORECASE)


def register_number(token: str) -> int:
    match = re.fullmatch(r"R([0-7])", token.strip(), re.IGNORECASE)
    if not match:
        raise ValueError(f"invalid register: {token!r}; expected R0 through R7")
    return int(match.group(1))


def memory_address(token: str) -> int:
    """The supplied data file uses eight-bit binary addresses."""
    token = token.strip()
    if re.fullmatch(r"[01]{8}", token):
        return int(token, 2)
    return int(token, 0)


@dataclass(frozen=True)
class Instruction:
    opcode: str
    operands: tuple[str, ...]
    source_line: int

    def __str__(self) -> str:
        return ",".join((self.opcode, *self.operands))


def load_program(path: Path) -> list[Instruction]:
    instructions = []
    with path.open(newline="", encoding="utf-8-sig") as stream:
        for line_number, row in enumerate(csv.reader(stream), 1):
            fields = [field.strip() for field in row]
            if not fields or not fields[0] or fields[0].startswith("#"):
                continue
            instructions.append(
                Instruction(fields[0].upper(), tuple(fields[1:]), line_number)
            )
    if not instructions:
        raise ValueError(f"no instructions in {path}")
    return instructions


class MemoryBus:
    def __init__(self, values: dict[int, int] | None = None):
        self.values = dict(values or {})

    @classmethod
    def from_file(cls, path: Path) -> MemoryBus:
        values = {}
        with path.open(newline="", encoding="utf-8-sig") as stream:
            for line_number, row in enumerate(csv.reader(stream), 1):
                if not row or not row[0].strip() or row[0].lstrip().startswith("#"):
                    continue
                if len(row) != 2:
                    raise ValueError(f"{path}:{line_number}: expected ADDRESS,VALUE")
                address = memory_address(row[0])
                if address < 0:
                    raise ValueError(f"{path}:{line_number}: negative address")
                values[address] = int(row[1].strip(), 0)
        return cls(values)

    def read(self, address: int) -> int:
        if address < 0:
            raise ValueError("negative memory address")
        return self.values.get(address, 0)

    def write(self, address: int, value: int) -> None:
        if address < 0:
            raise ValueError("negative memory address")
        self.values[address] = value


class Cache:
    """Four-entry, fully associative FIFO cache with write-through stores."""

    def __init__(self, bus: MemoryBus, capacity: int = 4):
        if capacity < 1:
            raise ValueError("cache capacity must be positive")
        self.bus = bus
        self.capacity = capacity
        self.entries: dict[int, int] = {}
        self.enabled = False
        self.hits = 0
        self.misses = 0

    def flush(self) -> None:
        self.entries.clear()

    def _remember(self, address: int, value: int) -> None:
        if address not in self.entries and len(self.entries) >= self.capacity:
            del self.entries[next(iter(self.entries))]
        self.entries[address] = value

    def read(self, address: int) -> tuple[int, str]:
        if not self.enabled:
            return self.bus.read(address), "main memory (cache off)"
        if address in self.entries:
            self.hits += 1
            return self.entries[address], "cache hit"
        self.misses += 1
        value = self.bus.read(address)
        self._remember(address, value)
        return value, "cache miss; main memory"

    def write(self, address: int, value: int) -> str:
        self.bus.write(address, value)
        if not self.enabled:
            return "main memory (cache off)"
        if address in self.entries:
            self.hits += 1
            result = "cache hit; write-through"
        else:
            self.misses += 1
            result = "cache miss; write-through"
        self._remember(address, value)
        return result


class CPU:
    def __init__(self, program: list[Instruction], bus: MemoryBus, *, trace: bool = True):
        self.program = program
        self.bus = bus
        self.cache = Cache(bus)
        self.registers = [0] * REGISTER_COUNT
        self.pc = 0  # byte address; one instruction occupies four bytes
        self.steps = 0
        self.halted = False
        self.trace = trace
        self.events: list[str] = []

    def _log(self, message: str) -> None:
        self.events.append(message)
        if self.trace:
            print(message)

    def _write_register(self, index: int, value: int) -> None:
        if index != 0:  # MIPS R0 is hardwired to zero
            self.registers[index] = value
            self._log(f"  WRITE-BACK R{index} <- {value}")
        else:
            self._log("  WRITE-BACK R0 stays 0")

    def _address_operand(self, operand: str) -> int:
        match = ADDRESS_PATTERN.fullmatch(operand.strip())
        if not match:
            raise ValueError(f"invalid memory operand: {operand!r}")
        return self.registers[register_number(match.group(2))] + int(match.group(1))

    def step(self) -> None:
        if self.halted:
            return
        if self.pc % 4:
            raise ValueError(f"unaligned program counter: {self.pc}")
        index = self.pc // 4
        if not 0 <= index < len(self.program):
            self.halted = True
            self._log(f"STOP PC={self.pc}: outside loaded program")
            return

        instruction = self.program[index]
        opcode, args = instruction.opcode, instruction.operands
        self._log(f"FETCH PC={self.pc}: {instruction}")
        self._log(f"  DECODE {opcode} ({', '.join(args)})")
        next_pc = self.pc + 4

        def count(expected: int) -> None:
            if len(args) != expected:
                raise ValueError(
                    f"line {instruction.source_line}: {opcode} needs {expected} operand(s)"
                )

        if opcode in {"ADD", "SUB", "SLT"}:
            count(3)
            rd, rs, rt = map(register_number, args)
            left, right = self.registers[rs], self.registers[rt]
            result = {"ADD": lambda: left + right, "SUB": lambda: left - right,
                      "SLT": lambda: int(left < right)}[opcode]()
            self._log(f"  EXECUTE {left} {opcode} {right} = {result}")
            self._write_register(rd, result)
        elif opcode == "ADDI":
            count(3)
            rt, rs = map(register_number, args[:2])
            result = self.registers[rs] + int(args[2], 0)
            self._log(f"  EXECUTE {self.registers[rs]} + {args[2]} = {result}")
            self._write_register(rt, result)
        elif opcode == "BNE":
            count(3)
            rs, rt = map(register_number, args[:2])
            taken = self.registers[rs] != self.registers[rt]
            if taken:
                next_pc += int(args[2], 0) * 4
            self._log(f"  EXECUTE branch {'taken' if taken else 'not taken'} -> PC={next_pc}")
        elif opcode in {"J", "JAL"}:
            count(1)
            target = int(args[0], 0)
            if opcode == "JAL":
                self._write_register(7, next_pc)
            next_pc = target * 4
            self._log(f"  EXECUTE jump -> PC={next_pc}")
        elif opcode == "LW":
            count(2)
            rt = register_number(args[0])
            address = self._address_operand(args[1])
            value, source = self.cache.read(address)
            self._log(f"  MEMORY read [{address}] -> {value} ({source})")
            self._write_register(rt, value)
        elif opcode == "SW":
            count(2)
            rt = register_number(args[0])
            address = self._address_operand(args[1])
            source = self.cache.write(address, self.registers[rt])
            self._log(f"  MEMORY write [{address}] <- {self.registers[rt]} ({source})")
        elif opcode == "CACHE":
            count(1)
            code = int(args[0], 0)
            if code == 0:
                self.cache.enabled = False
            elif code == 1:
                self.cache.enabled = True
            elif code == 2:
                self.cache.flush()
            else:
                raise ValueError(f"invalid CACHE code: {code}")
            self._log(f"  EXECUTE CACHE {code}")
        elif opcode == "HALT":
            if args not in ((), (";",)):
                count(0)
            self.halted = True
            self._log("  EXECUTE HALT")
        else:
            raise ValueError(f"line {instruction.source_line}: unsupported opcode {opcode}")

        self.pc = next_pc
        self.steps += 1

    def run(self, max_steps: int = 1000) -> CPU:
        while not self.halted:
            if self.steps >= max_steps:
                raise RuntimeError(f"stopped after {max_steps} instructions (possible loop)")
            self.step()
        return self

    def report(self) -> str:
        registers = " ".join(f"R{i}={value}" for i, value in enumerate(self.registers))
        memory = " ".join(f"[{address}]={value}" for address, value in sorted(self.bus.values.items()))
        return (
            f"STEPS {self.steps}; PC {self.pc}; CACHE hits={self.cache.hits} "
            f"misses={self.cache.misses}\nREGISTERS {registers}\nMEMORY {memory}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("instructions", type=Path)
    parser.add_argument("data", type=Path)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--quiet", action="store_true", help="show only final state")
    args = parser.parse_args()
    cpu = CPU(load_program(args.instructions), MemoryBus.from_file(args.data), trace=not args.quiet)
    cpu.run(args.max_steps)
    print(cpu.report())


if __name__ == "__main__":
    main()
