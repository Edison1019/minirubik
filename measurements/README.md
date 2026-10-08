# Measurement evidence

These files preserve reported measurements rather than generated executables
or toolchain caches. Raw records retain the original local source paths and
commands for provenance. Reproduce the programs using paths appropriate to
your own installation.

| Directory | Evidence | Reproduction |
| --- | --- | --- |
| [gates](gates/) | H1/H2 logs, full H3 log and hashes, six ISS/pipeline target results, and all 2644 distance-11 counts | `collect_gate_evidence.py`, `run_h3.py`, `measure_worst_case.py` |
| [simulation_rate](simulation_rate/) | Three trials per model, raw telemetry and median-rate summary | `measure_simulation_rate.py` |
| [c_comparison](c_comparison/) | Ten paired tests, compiler identity, linked `.text` sizes, disassembly and linker map | `compare_c_assembly.py` |

Ripes is pinned by executable SHA-256 in the manifests. The measured build is
`v2.2.6-106-g5b8a616`, with RV32_ISS and RV32_5S where applicable. Measurements
include no renderer. Host H3 evidence belongs to the recorded solver/table
hashes; changing those files requires validating the new version separately.

The C comparison uses xPack `riscv-none-elf-gcc` 15.2.0 with
`-O2 -march=rv32i -mabi=ilp32`, not the literal compiler executable named in
the assignment. This distinction is recorded in its result manifest and must
be resolved before presenting it as the exact requested reference.

For the solved-input RV32_ISS gate run, the raw JSON was not retained; the
console log and `gates/gates_summary.json` retain its successful result and
756-instruction count. The other five gate runs have raw JSON and logs.

The host/guest memory-ratio measurements were manually collected in Task
Manager. Their reported values and method are in [MEMORY_RATIO.md](../MEMORY_RATIO.md);
this directory does not claim to contain original Task Manager screenshots.
