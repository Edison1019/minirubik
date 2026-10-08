# Exhaustive distance-11 Ripes measurement

```powershell
python measure_worst_case.py --ripes 'C:\Users\user\Desktop\Ripes-v2.2.6-106-g5b8a616-win-x86_64\Ripes.exe'
```

The native baseline adapter constructs its independent exact BFS oracle and
exports all 2644 distance-11 states. Neither solver source is edited. The script
builds the canonical assembly ELF once and locates the read-only `input_str`
symbol. For each case it copies the template, changes only the 14 input bytes,
and overwrites `.build/worst_case/current.elf`. This is equivalent to changing
the assembly string and rebuilding, but avoids repeating identical compilation.
There is one temporary ELF, rather than 2644 retained ELF files.

Each case runs in a fresh Ripes RV32_ISS CLI process with no ISA extensions or
cache options. The current assembly has no renderer. The script refuses sources
containing LED_MATRIX references; if a renderer is added, update the tool to
check the explicit assembly-time renderer switch before measuring.

The measurement includes the entire program: ranking, search, solution
verification, and console output. Successful exit, an 11-move output, and an
independent baseline-model replay of that output are required. Every measured
instruction count must be at most 50000000. Timeouts and malformed outputs are
failures, never omitted successes. The Ripes instruction count is used directly;
source-level and local emulator counts do not substitute for it.

Artifacts in `.build/worst_case/`:

- `cases.csv`: exact ranks and all 2644 input strings.
- `results.csv`: each input, retired instructions, execution milliseconds,
  returned path, and pass/failure status; flushed after every case.
- `manifest.json`: build hashes, pinned Ripes executable, and measurement scope.
- `summary.json`: completion count, worst case, failures, specified sample, and
  full-domain pass status. A full PASS requires every case, not a sample.
- `current.elf`, `current.json`, `current.log`: most recent run only.

Resume an interrupted run with the same command and `--resume`. Build hashes
must match. A recorded failure remains a failure; inspect it before deciding to
restart a complete run. A separate short validation run is available using
`--limit 2`, which writes to `.build/worst_case_smoke/` and cannot yield a full PASS.

Generated measurement files are ignored by Git. Preserve or copy the CSV,
manifest, and summary for the assignment report and reproducibility evidence.
