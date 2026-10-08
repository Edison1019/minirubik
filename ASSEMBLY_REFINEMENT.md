# Measured assembly refinement experiments

These experiments were performed on October 8, 2026, after the original final
solver had been validated. They are new, reproducible experiments, not a
reconstruction of measurements taken during earlier development. The source
snapshots and raw Ripes reports are in `measurements/refinement/`.

## Measurement conventions

All variants use the same current solver, input wrapper, read-only tables,
move order, and solution verification. The renderer is compiled out
(`RENDER=0`). Code size means the bytes of linked `.text`, rather than the
file size of the ELF or assembly source. Instruction counts cover the entire
program and come from Ripes `--iret` on `RV32_ISS`, with no ISA extensions.
Each input is run in a fresh Ripes CLI process. Startup delays are not retired
instructions and are not used as an optimization metric.

The pinned Ripes build is `v2.2.6-106-g5b8a616`; its SHA-256 is
`bd2ddea8cd6fcf6902cda7366fe99ab6dd0c7fdbbc7efcfdb89ede20acc67f0f`.
The experiment manifest records the assembler/compiler version, commands,
source hashes, instruction counts, and returned paths.

Every run must exit successfully after the assembly's in-program replay.
The path is also replayed independently by `tests/verify_host_path.c`, using
the preserved baseline cubie model. Its length is checked against a known
optimal distance. These sampled checks do not replace full-domain H3 or the
complete distance-11 performance test.

## Step 0: pre-refinement assembly

The original child check reads both pattern databases, computes their maximum
with a branch, and prunes when `child_depth + max(h_p, h_o) > bound`.
This version provides the common reference for both experiments. Here, the internal artifact label `baseline` means the current non-recursive IDA* assembly before these experiments, not the original full-BFS `solver_baseline.c`. The full-BFS program was not run in Ripes for this comparison.

## Step 1: replace the maximum-selection branch

The first experiment replaces the conditional maximum with five instructions:

```asm
sltu t0, t4, t5
sub  t0, zero, t0
xor  t1, t4, t5
and  t1, t1, t0
xor  t4, t4, t1
```

The mask is all ones when `h_p < h_o`, otherwise zero. The XOR selection
therefore produces exactly the same maximum. Search order and pruning remain
unchanged. This removes a branch, but always executes five instructions;
the original selection executes one or two. Thus fewer branches alone do
not imply a smaller retired count. Pipeline cycle effects would require a
separate measurement and are not established by these ISS experiments.

## Step 2: reject on either table before computing a maximum

The second experiment starts again from the pre-refinement assembly. It computes
`remaining = bound - child_depth`, reads the permutation PDB, and rejects
immediately if its value exceeds `remaining`. Only surviving candidates read
the orientation PDB. It also rejects if that value exceeds `remaining`.

This is equivalent to the original check because
`max(h_p, h_o) > remaining` if and only if either component exceeds
`remaining`. The existing search entry rejects frames at the depth bound,
so `child_depth <= bound` and the unsigned subtraction cannot underflow.
The change removes maximum selection and can avoid the second address
calculation and byte load. Whether it pays depends on the observed rejection
distribution; the measurements below determine that.

## Reproduction

```powershell
python measure_refinement.py --ripes 'PATH_TO_Ripes.exe'
```

The script generates all three source snapshots from the pre-refinement heuristic
block, builds RV32I/ILP32 ELF files with the local xPack toolchain, checks their
read-only sections and static data budget, and measures five identical inputs
for every variant. The compiler is used as an assembler/linker, not to generate
the handwritten search. The script leaves the canonical `solver_rv32i.s` and
its published ELF files unchanged. `--offscreen` is an optional startup
diagnostic; the normal measurement uses the default Qt platform.

For independent concurrent runs, use `--jobs 3`. Each run then uses its own
patched ELF and report file. The experiment compares retired instructions, not
throughput; concurrent execution times must not be treated as isolated speed
measurements. Use `--resume` to retain verified completed results when the
source, compiler, and Ripes hashes still match.

## Measured results and decisions

| Input | Optimal moves | Step 0: pre-refinement assembly | Step 1: branchless maximum | Step 2: early rejection |
| --- | ---: | ---: | ---: | ---: |
| `12345671111111` | 0 | 756 | 756 | 756 |
| `25314672313211` | 1 | 1,067 | 1,079 | 1,061 |
| `24316572122213` | 8 | 93,788 | 101,439 | 89,063 |
| `21345671111111` | 11 | 10,782,338 | 11,660,401 | 10,241,263 |
| `54721631111111` | 11 | 29,481,006 | 31,884,261 | 28,002,408 |

All counts are whole-program retired instructions measured by Ripes. All 15
runs passed both in-program and independent path verification and returned
the known optimal lengths. The pre-refinement assembly reproduced the previously recorded
counts for all five inputs. The solved case does not enter the child check,
so neither change affects its retired count.

| Variant | Linked `.text` bytes | Static data bytes |
| --- | ---: | ---: |
| Pre-refinement assembly | 1,356 | 41,515 |
| Branchless maximum | 1,368 | 41,515 |
| Early rejection | 1,352 | 41,515 |

**Step 1 is rejected for the ISS objective.** On the specified distance-11
input, it increases retired instructions by approximately 8.14% and grows
the linked text by 12 bytes. The original maximum selection costs one or
two executed instructions; the branchless replacement always costs five.
Removing the branch therefore makes this instruction-count objective worse.

**Step 2 is the promising refinement.** It reduces retired instructions by
approximately 5.02% on the specified distance-11 input and 5.02% on the
previous pre-refinement worst-case input, while shrinking text by four bytes.
For an expanded child, the original heuristic block executes eight or nine
instructions. Early rejection executes five when the permutation bound alone
rejects it, otherwise eight. Both blocks make the same pruning decision, so
the gain comes from less work per candidate, rather than changing the search
order or weakening the optimality condition.

These records accompany the experiments as source snapshots. The published
canonical solver remains the measured pre-refinement version, whose complete 2,644-state
distance-11 batch has already passed. The early-rejection candidate has been
measured on the five inputs above; it has not been subjected to a new complete
distance-11 batch. Its count of 28,002,408 is for the *pre-refinement assembly's*
worst-case input, not a measured maximum over all states for the new variant.
This distinction keeps the original worst-case evidence and the new sampled
refinement evidence attributable to their actual versions.

Raw evidence: [experiment manifest](measurements/refinement/results.json),
[pre-refinement source](measurements/refinement/baseline.s),
[branchless source](measurements/refinement/branchless_max.s), and
[early-rejection source](measurements/refinement/early_reject.s).
