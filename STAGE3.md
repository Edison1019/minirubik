## Improve efficiency in C

The C implementation makes the search operations explicit before translating them into RV32I. The main change from the baseline is architectural: the target no longer constructs a full BFS table. Within the chosen iterative-deepening search, the implementation avoids repeated cube reconstruction, generates successive turns incrementally, prunes unnecessary children, and uses bounded storage. The operation counts below describe the source algorithm; they are not retired-instruction measurements of individual optimizations.

### Remove target-side full enumeration

The baseline builds its complete table before answering an input. That build examines 3,674,160 states and 33,067,440 directed HTM edges. Each edge advances both a permutation and an orientation transition, giving 66,134,880 transition updates. It also allocates a 14,696,640-byte BFS queue and a 3,674,160-byte move-per-state table.

The final C solver instead reads precomputed abstraction tables and searches only as needed for the supplied input. This removes the queue and full-state move table, together accounting for 18,370,800 bytes. The four retained tables occupy 40,383 bytes. This is a reduction in target initialization work and storage, not a claim that search is cheaper than every baseline table lookup: once its complete table exists, the baseline can answer a query very cheaply. The target cannot afford that table-building strategy, as established in stage 1.

### Keep ranks throughout the search

Search frames store permutation and orientation ranks rather than 14-element cubie states. A candidate transition is obtained directly:

```c
uint16_t p = perm_trans[frame->current_p][face];
uint16_t o = ori_trans[frame->current_o][face];
```

This requires two halfword table reads. It avoids applying a turn to seven cubies, reducing their twist values modulo 3, and ranking the resulting state inside the search loop. Permutation ranking contains 21 pairwise comparisons for seven cubies, while orientation ranking processes six base-3 digits. These operations still occur where needed for input conversion or host table generation, but not for every candidate in the target search. The baseline already uses factored rank transitions during BFS; this implementation retains that useful idea rather than claiming it as a new optimization over the baseline.

The search uses separate ranks, so it also avoids repeatedly combining them as `p * 729 + o` and then splitting the combined rank with division and remainder. Its dynamic search operations contain no division or remainder. Input parsing, initial ranking, and final verification are outside this hot loop and still contain arithmetic that the RV32I compiler may implement using software helpers.

### Generate turns incrementally

Each frame preserves `current_p` and `current_o`. For one face, successive candidates apply one quarter-turn to the running state, producing the quarter-turn, half-turn, and inverse quarter-turn in order. Generating all three candidates therefore uses three paired transitions, or six halfword table reads.

If each candidate were independently generated from the parent using quarter-turn tables, it would require one, two, and three paired transitions respectively: six paired transitions and twelve halfword reads. The running-state method halves that transition work for a fully examined face. When moving to another face, the running ranks are reset to the frame's initial ranks. This also explains why the parent turn counter is advanced before descending: after backtracking, the next candidate must continue from the preserved running state.

### Prune before allocating a child frame

The search excludes the face used by the previous move. A shortest HTM solution cannot contain two adjacent moves on the same face, since they can be combined into one move or canceled. The root has nine candidates, while each subsequent level has at most six. This excludes one-third of the move choices at a non-root node before their table lookups are performed.

For a generated candidate, the heuristic reads two PDB bytes and selects their maximum. The bound check occurs before writing the path entry or initializing a child frame:

```c
if (child_depth + heuristic(p, o) > bound)
    continue;
```

Rejected candidates still update the parent's running state, which is needed to generate the next turn, but do not create a child frame. Accepted non-goal candidates initialize a frame containing four halfword ranks and three byte-sized control fields. This ordering avoids those child-frame writes for candidates that are immediately pruned. Bounds start at the root heuristic rather than zero, avoiding all lower-bound iterations that cannot possibly succeed.

The source retains explicit branches for bound checks, face selection, backtracking, and goal detection. It does not establish that a branchless replacement would be faster. Such a claim would require a separate comparison of instruction counts and pipeline behavior.

### Replace recursion with bounded frames

The implementation allocates `frames[MAX_DEPTH + 1]`, giving 12 frames for depths 0 through 11. Each frame stores four `uint16_t` ranks and three `uint8_t` fields; with the usual two-byte alignment, its size is 12 bytes and the frame array occupies 144 bytes. The output path needs 11 bytes. These are explicit search-data sizes, not the complete compiled stack requirement, which also includes local variables, saved registers, and runtime calls.

Descending and backtracking update a depth index rather than making recursive calls. This satisfies the target's recursion restriction and makes the search storage bound explicit. Exhausted frames resume their parent, whose next-turn state was already advanced. No heap allocation, floating-point arithmetic, or recursive search is used.

### Prepare for RV32I translation and preserve correctness

The transition-table row stride is six bytes. Its index is `(rank * 3 + face) * 2`, which can be implemented with shifts and additions on RV32I. Multiplying a face index by three for a move code is similarly inexpensive. The C frame layout has a 12-byte stride; the handwritten assembly later uses 16-byte frames, trading 48 additional frame bytes for simpler power-of-two address arithmetic. That layout change belongs to the assembly stage, rather than being a property of the C implementation.

The C source does not manually replace every arithmetic expression with shifts. GCC's RV32I output and its linked support routines must be examined to determine the actual machine cost. The compiler-reference comparison in stage 4 measures the full program separately; it does not attribute a measured speedup to each C change above.

Correctness is checked independently of these operation-count arguments. H1 checks admissibility over all 3,674,160 states, H2 checks the tables, and H3 checks the final C solver over the complete domain against the baseline oracle. The full H3 run returned optimal, valid solutions for all states and took approximately 18 minutes and 19 seconds on the host. The target measurements in stage 4 then determine whether the RV32I translation meets the instruction budget.
