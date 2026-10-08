# GCC C reference versus handwritten RV32I assembly

The reference compiles the unchanged final `solver.c` with **riscv-none-elf-gcc.exe (xPack GNU RISC-V Embedded GCC x86_64) 15.2.0**.
Its target triple is `riscv-none-elf`. The core optimization and ISA options are
`-O2 -march=rv32i -mabi=ilp32`. Additional target integration options are
`-mno-relax -msmall-data-limit=0`; no LTO is enabled.

**Compiler qualification:** the available compiler is named `riscv-none-elf-gcc`,
rather than the assignment's literal `riscv64-unknown-elf-gcc`. This is a
GNU GCC RV32I/ILP32 reference comparison, but acceptance of this toolchain
as the specified reference has not been confirmed. To reproduce with the
specified executable, supply its path through `--gcc`.

The solver source is compiled in its own translation unit; only its main
symbol is renamed at compile time. A small Ripes runtime adapter supplies
the inline input and string-output/exit environment calls. Its minimal
stdio interface implements the operations used by this program; it is not
a general-purpose C library. GCC arithmetic support is linked from its
RV32I libgcc. These helpers occur only in the compiler reference, not in
the handwritten solver. The reference uses no heap or renderer.

Both programs execute on the pinned Ripes RV32_ISS model. Retired counts
cover the whole program, including ranking, search, path verification,
and output. Both returned paths are replayed independently using the
baseline model, their lengths are checked against known optimal values,
and the C and assembly paths match for every tested input. The wrappers
differ, so these counts are whole-program comparisons, not isolated search
instruction counts. C additionally retains its input validation.

| Input | Optimal moves | GCC C retired instructions | Assembly retired instructions | Assembly reduction |
| --- | ---: | ---: | ---: | ---: |
| `12345671111111` | 0 | 645 | 756 | -17.21% |
| `62345713133111` | 8 | 81,975 | 67,162 | 18.07% |
| `24316572122213` | 8 | 114,219 | 93,788 | 17.89% |
| `25713642221111` | 8 | 48,403 | 39,594 | 18.20% |
| `24513763133333` | 9 | 957,042 | 787,593 | 17.71% |
| `43752611332133` | 9 | 337,835 | 277,642 | 17.82% |
| `25416373331111` | 10 | 3,496,905 | 2,878,111 | 17.70% |
| `21345671111111` | 11 | 13,097,556 | 10,782,338 | 17.68% |
| `25314672313211` | 1 | 1,284 | 1,067 | 16.90% |
| `54721631111111` | 11 | 35,807,403 | 29,481,006 | 17.67% |

| Build | Linked `.text` bytes, renderer absent |
| --- | ---: |
| GCC C including startup, runtime adapter, and arithmetic helpers | 2164 |
| Handwritten assembly including startup and software arithmetic | 1356 |

The assembly does not win on the solved input: its fixed setup and
verification overhead exceeds the C reference's overhead for that case.
The assembly checks the root heuristic before reaching its goal test,
whereas C returns immediately for the solved root. Search-heavy inputs
benefit from the assembly's frame layout and register-held search state.
The measured results support the whole-program improvement; the cost
of individual optimizations is not separately established by this test.

Reproduce with:

```powershell
python compare_c_assembly.py --ripes 'PATH_TO_Ripes.exe' --gcc 'PATH_TO_RISC_V_GCC.exe'
```

Raw telemetry, console logs, commands, source hashes, linked disassembly,
and the GCC linker map are in `.build/c_comparison/`. `results.json`
records the compiler identity and whether the source files stayed unchanged.
