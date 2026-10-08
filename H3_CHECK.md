# Exhaustive H3 verification

Run the new checker with:

```powershell
python run_h3.py
```

Build without running the exhaustive search:

```powershell
python run_h3.py --build-only
```

Neither `solver.c` nor `solver_baseline.c` needs editing. The old
`check_h3.c` is not used by this build.

## Independence of the oracle

`baseline_adapter.c` includes the unchanged baseline with its CLI `main`
renamed. Its static ranking, unranking, move model, validation, and BFS
functions remain private to that translation unit. The adapter exports only
the small API in `baseline_adapter.h`.

The oracle builds the baseline BFS move-toward-solved table. It converts
the paths into exact distances, memoizing already resolved chains, and
checks that every rank has a distance in 0 through 11 and that 2644 ranks
have distance 11. Neither distances nor path verification consult the
candidate PDB or transition tables.

`solver.c` is compiled separately with `SOLVER_NO_MAIN`. It is the only
translation unit that includes `pdb_tables.h`, avoiding duplicate table
definitions. The new `check_h3_full.c` calls its existing `solve` interface.

## What is checked

For each of all 3674160 ranks, the checker:

1. Obtains the exact baseline BFS distance.
2. Calls the current nonrecursive solver.
3. Checks that its returned length equals that distance.
4. Applies every move with the baseline cubie model and requires solved.
5. Checks canaries surrounding the 11-byte output buffer. The buffer is
   initially filled with invalid moves, detecting unwritten path entries.

A mismatch exits nonzero and reports the rank, 14-character input,
expected/actual length, path, and validation status. The checker prints
`H3 PASS` only after checking the whole domain. There is no sampling mode.
The path canaries are a limited check, not a replacement for a memory
sanitizer.

## Results and reproducibility

The runner saves `.build/h3/h3.log` and `.build/h3/result.json`. The JSON
contains the compiler version, exact commands, executable and source
SHA-256 values, exit status, host wall time measured with `perf_counter`,
and a check that source files did not change during the run.

Compilation uses native GCC `-O2 -std=c99`. Only the adapter suppresses
the baseline's existing signedness warning; new code compiles with
warnings treated as errors. Host allocation by the oracle does not imply
allocation in the target solver.

This verifies H3 for the C search. It does not establish Ripes execution,
RV32I instruction budgets, T5-T7, H1, or H2. Those are separate gates.
