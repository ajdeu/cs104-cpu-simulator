"""Integration checks for arithmetic, control flow, memory, and cache behavior."""

import unittest
from pathlib import Path

from cpu import CPU, MemoryBus, load_program


ROOT = Path(__file__).parent


class SimulatorIntegrationTests(unittest.TestCase):
    def test_demo_program(self):
        cpu = CPU(
            load_program(ROOT / "examples/demo_instructions.txt"),
            MemoryBus.from_file(ROOT / "examples/demo_data.txt"),
            trace=False,
        ).run()
        self.assertEqual(cpu.registers[0], 0)
        self.assertEqual(cpu.registers[3], 9)
        self.assertEqual(cpu.registers[6], 9)
        self.assertEqual(cpu.registers[7], 68)
        self.assertEqual(cpu.bus.values[3], 9)
        self.assertEqual((cpu.cache.hits, cpu.cache.misses), (1, 4))
        self.assertEqual(cpu.steps, 17)

    def test_bad_program_is_stopped_by_instruction_limit(self):
        from cpu import Instruction

        cpu = CPU([Instruction("J", ("0",), 1)], MemoryBus(), trace=False)
        with self.assertRaisesRegex(RuntimeError, "possible loop"):
            cpu.run(max_steps=4)

    def test_subtraction_jump_and_disabled_cache(self):
        from cpu import Instruction

        rows = [
            ("ADDI", "R1", "R0", "10"),
            ("ADDI", "R2", "R0", "3"),
            ("SUB", "R3", "R1", "R2"),
            ("J", "5"),
            ("ADDI", "R3", "R3", "99"),
            ("SW", "R3", "0(R0)"),
            ("LW", "R4", "0(R0)"),
            ("HALT", ";"),
        ]
        program = [Instruction(row[0], tuple(row[1:]), i + 1) for i, row in enumerate(rows)]
        cpu = CPU(program, MemoryBus(), trace=False).run()
        self.assertEqual(cpu.registers[3:5], [7, 7])
        self.assertEqual(cpu.bus.values[0], 7)
        self.assertEqual((cpu.cache.hits, cpu.cache.misses), (0, 0))


if __name__ == "__main__":
    unittest.main()
