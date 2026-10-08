# Building and loading the RV32I solver

The canonical source is `solver_rv32i.s`. It puts all four tables, strings,
and move-name pointers in `.rodata`, and its 1024-byte stack in `.bss`.
`solver_rv32i.ld` gives `.rodata` an R-only load segment, `.text` an RX
segment, and `.bss` an RW segment. The ELF entry is `_start`, which
initializes the stack before jumping to `main`. Compression and linker
relaxation are disabled so this remains RV32I and requires no `gp` setup.

## Build

```powershell
python build_rv32i.py
```

The script finds RISC-V GCC on PATH, or the portable Zig 0.13.0 toolchain
under `.tools/zig-windows-x86_64-0.13.0/`. To use another compiler:

```powershell
python build_rv32i.py --cc "C:/path/to/riscv64-unknown-elf-gcc.exe"
```

This produces `solver_rv32i.elf`, verifies its section and segment flags,
checks that all four table symbols belong to `.rodata`, verifies the entry
point, and checks the 128 KiB static-data budget. Modify `input_str` in the
canonical source and rebuild to test a different state.

The portable toolchain is downloaded from:
https://ziglang.org/download/0.13.0/zig-windows-x86_64-0.13.0.zip

Its published SHA-256 is:
`d859994725ef9402381e557c60bb57497215682e355204d754ee3df75ee3c158`.
No toolchain files or caches need to be committed; `.tools/` is ignored.
Zig here only assembles and links the handwritten assembly. It does not
replace the assignment's separate GCC reference comparison.

## Ripes

Load `solver_rv32i.elf` using Ripes' external ELF file option instead of
pasting the canonical assembly into the editor. Select RV32I, reset, and run.
Record the exact Ripes version and perform the required ISS/pipeline checks
and `--iret` measurements on that build. ELF flags describe read-only
placement; they do not demonstrate that Ripes traps writes to that region.

The build also generates `solver_rv32i_ripes.s` for the built-in assembler.
That compatibility copy uses `.data`, so it does **not** meet the read-only
section requirement. It is useful for source-level editor walkthroughs.
Do not edit it manually. Regenerate it without a toolchain using:

```powershell
python build_rv32i.py --source-only
```

Acceptance of external ELF files in the grading workflow still needs to be
confirmed with the instructor/TA.

## Local checks

```powershell
python tests/verify_rv32i.py
python tests/verify_elf_rv32i.py
```

The first script checks source instructions in the generated editor copy.
The second decodes and executes the linked ELF's RV32I machine instructions,
checks results against the native C solver, and rejects target stores outside
`.bss`. These checks are host tools; their instruction counters must not be
reported as Ripes `--iret` results.
