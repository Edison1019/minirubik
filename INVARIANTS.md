**Which invariants does the baseline rely on?**

The baseline fixes the front-upper-left corner and uses only moves on the R, B, and D faces. These moves preserve that corner's position and orientation, so the program only needs to represent the other seven corners.

The permutation array `p[7]` must contain each cubie ID from 0 to 6 exactly once. Each row of `source` is a permutation of these seven indices, so `quarter_turn()` rearranges the cubies without duplicating or losing any of them. The `valid()` function checks both the range and uniqueness of the IDs. There is no restriction to even permutations: a quarter-turn cycles four corners and is an odd permutation.

Each orientation value must be 0, 1, or 2, and the total corner twist must satisfy:

$$
\sum_{i=0}^{6} o[i] \equiv 0 \pmod{3}.
$$

In `quarter_turn()`, the orientation values are permuted and the face-specific twist values are added modulo 3. The twist rows for R and B each sum to 6, while the D row sums to 0, so every move preserves the total twist modulo 3. Consequently, only six orientation values are independent. `rank_state()` encodes the first six, and `unrank_state()` reconstructs the seventh as:

$$
o[6] = \left(3 - \left(\sum_{i=0}^{5}o[i] \bmod 3\right)\right) \bmod 3.
$$

These constraints give $7!$ permutations and $3^6$ orientations, for a total of $7!\times3^6=3{,}674{,}160$ states. The combined rank is `permutation_rank * 729 + orientation_rank`. On valid states, ranking and unranking must be inverse operations; the baseline's `self_test()` checks that unranking every rank produces a valid state that ranks back to the same value. The solved state has `p = {0,1,2,3,4,5,6}`, all-zero orientations, and rank zero.

The baseline also relies on permutation and orientation transitions being independent. The new permutation depends only on the old permutation and the chosen face, while the new orientation depends only on the old orientation and that face. This allows `build_table()` to precompute separate transition tables and combine their results during BFS.

Finally, all nine moves have unit cost in the half-turn metric. BFS discovers each state for the first time at its shortest distance from the solved state, and `toward_solved` stores the inverse of the discovery move. For every non-solved state, following that stored move decreases the exact distance by one, which is why repeatedly following the table returns an optimal solution.
