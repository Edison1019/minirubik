### Correctness validation: H1-H4 and T5-T7

Host checks use the baseline's cubie move model and exact BFS oracle. The oracle
is separate from the candidate solver and its heuristic tables. Host validation
and target execution are reported separately: native C correctness checks do
not replace execution in Ripes.

| Gate | Check | Result and evidence |
| --- | --- | --- |
| H1 | Check $h(s)\le d(s)$ for all 3,674,160 states | PASS: zero violations; maximum heuristic 7, exact diameter 11. [Log](measurements/gates/h1.log). |
| H2 | Check every transition and PDB entry against an independent reference | PASS: 2,187 orientation-transition entries, 15,120 permutation-transition entries, 729 orientation-PDB entries, and 5,040 permutation-PDB entries; no mismatches. [Log](measurements/gates/h2.log). |
| H3 | Compare returned solution lengths with exact BFS distances and independently replay paths over the full domain | PASS: all 3,674,160 states returned optimal valid solutions; elapsed wall time 1,098.67 seconds, approximately 18 min 19 s. [Log](measurements/gates/h3.log), [manifest](measurements/gates/h3_result.json). |
| H4 | Compare packed accessors with unpacked references at even and odd indices | Not applicable: PDBs use unpacked bytes and transitions use unpacked halfwords; there is no packed accessor. |
| T5 | Apply returned paths and check that the cube is solved | The assembly calls `verify_solution` before printing a path. In the exhaustive RV32_ISS distance-11 run, all 2,644 returned paths also passed independent baseline replay. [Per-state records](measurements/gates/worst_case_results.csv). |
| T6 | Solve `21345671111111` optimally in 11 HTM moves | PASS on RV32_ISS: `R B' D2 R' B R' B' R D2 R B`, 11 moves, 10,782,338 retired instructions. [Summary](measurements/gates/worst_case_summary.json). |
| T7 | Run solved, short, and distance-11 cases in RV32_ISS and a visual pipeline model | PASS for all six runs on RV32_ISS and RV32_5S. Both models returned identical valid optimal paths. [Run summary](measurements/gates/gates_summary.json). Unknown grader inputs are not part of these recorded tests. |

For H2, the solved PDB entry is zero in both abstractions. The maximum distances
are 6 for orientation and 7 for permutation. The maximum transition values are
728 and 5039 respectively. The solved transition rows are R/B/D = 426/16/0 for
orientation and 1104/9/198 for permutation. A solved transition entry need not
be zero: turning a solved cube generally produces an unsolved state.

The H3 result is from the completed full-domain run, not a new sample. Its
recorded hashes for `solver.c`, `solver_baseline.c`, and `pdb_tables.h` were
checked against the current files before reusing the evidence.

#### Target test cases

| Case | Input | Optimal HTM length | Expected path in the current build |
| --- | --- | ---: | --- |
| Solved | `12345671111111` | 0 | Empty path |
| Short | `25314672313211` | 1 | `R'` |
| Distance 11 | `21345671111111` | 11 | `R B' D2 R' B R' B' R D2 R B` |

Use Ripes `v2.2.6-106-g5b8a616`, with no ISA extensions, and record each case
on `RV32_ISS` and `RV32_5S`. The renderer is absent in this measured version.
For each run, successful exit and in-program verification were accompanied
by the expected optimal length. The available raw reports and console
logs are stored in `measurements/gates/`, with run commands and independent
replay results in `gates_summary.json`.

The complete distance-11 run passed the performance gate with a maximum of
29,481,006 retired instructions. Its pinned environment and template hashes
are recorded in [the manifest](measurements/gates/worst_case_manifest.json).
This target performance result complements H3; it does not substitute for
full-domain C optimality or the pipeline-model tests.

<!-- For HackMD, replace these repository-relative links with full GitHub URLs
after committing and pushing the evidence. Do not leave links pointing to
HackMD-relative paths. -->
