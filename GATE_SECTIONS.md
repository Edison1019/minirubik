<!-- Paste the first section at the end of stage 2, the second at the end of
stage 3, and the third in stage 4. Evidence links point to the repository;
commit and push the files before expecting the links to work online. -->

### Validation of the heuristic and tables

The heuristic and its tables were checked independently on the host before relying on them for target-side search. `check_h1.c` compares $h(s)=\max(h_{\mathrm{perm}}(s),h_{\mathrm{ori}}(s))$ with the exact baseline BFS distance for every one of the 3,674,160 states. It found **zero admissibility violations**, with maximum heuristic value 7 and maximum exact distance 11. The complete result is recorded in the [H1 log](https://github.com/Edison1019/minirubik/blob/main/measurements/gates/h1.log).

`check_h2.c` reconstructs transitions from an independent cubie model and computes abstract BFS distances using those reference transitions. It checks every entry, its range, the maximum value, and the solved entry or row:

| Table | Entries checked | Maximum value | Solved entry or R/B/D row | Result |
| --- | ---: | ---: | --- | --- |
| Orientation transitions | 2,187 | 728 | 426 / 16 / 0 | PASS |
| Permutation transitions | 15,120 | 5,039 | 1104 / 9 / 198 | PASS |
| Orientation PDB | 729 | 6 | 0 | PASS |
| Permutation PDB | 5,040 | 7 | 0 | PASS |

There were no mismatches with the reference. A solved transition row does not have to contain only zeros: a face turn generally moves a solved cube away from solved. The full results are in the [H2 log](https://github.com/Edison1019/minirubik/blob/main/measurements/gates/h2.log). H4 is not applicable because the implementation uses unpacked byte PDBs and halfword transition tables, with no packed accessor.

### Exhaustive validation of the C solver

The final C solver was checked against an independent exact BFS oracle over **all 3,674,160 states**. For each state, the checker compares the returned length with its exact distance and replays the returned moves using the baseline's cubie model. It also checks move codes and guards around the 11-byte output buffer.

All states returned valid solutions of optimal length, including all 2,644 states at distance 11. The complete H3 run took **1,098.67 seconds**, approximately **18 minutes and 19 seconds**, on the host. This is an exhaustive result, not a sample. Before reusing it, the recorded hashes of `solver.c`, `solver_baseline.c`, and `pdb_tables.h` were confirmed to match the current files.

Evidence: [full H3 log](https://github.com/Edison1019/minirubik/blob/main/measurements/gates/h3.log) and [run manifest](https://github.com/Edison1019/minirubik/blob/main/measurements/gates/h3_result.json).

### Validation on Ripes

The handwritten RV32I ELF was tested on Ripes `v2.2.6-106-g5b8a616` using both `RV32_ISS` and the five-stage `RV32_5S` model, without ISA extensions or a renderer. Three inputs cover a solved cube, a one-move scramble, and the specified distance-11 state. Each run exited successfully after the assembly's in-program solution verification. The emitted path was also independently replayed using the baseline model, and its length matched the known optimal distance.

| Input | Optimal HTM length | RV32_ISS | RV32_5S | Retired instructions in each model |
| --- | ---: | --- | --- | ---: |
| `12345671111111` | 0 | PASS | PASS | 756 |
| `25314672313211` | 1 | PASS | PASS | 1,067 |
| `21345671111111` | 11 | PASS | PASS | 10,782,338 |

Both models returned the same path for each input. The solved input returned an empty path, the short input returned `R'`, and the specified input returned:

```text
R B' D2 R' B R' B' R D2 R B
```

These records support T5 (returned paths solve the cube), T6 (the specified input has an optimal 11-move solution), and the three-case portion of T7 (reproduction in ISS and a pipeline model). Unseen grader inputs have not been tested as part of these six runs. Complete commands, counts, paths, independent replay results, and pinned executable hashes are in the [target-run summary](https://github.com/Edison1019/minirubik/blob/main/measurements/gates/gates_summary.json). The [evidence directory](https://github.com/Edison1019/minirubik/tree/main/measurements/gates) contains the console logs and available raw telemetry.
