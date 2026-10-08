## Choose a representation and an algorithm that fit the target

### State representation

The baseline's full BFS table is convenient on a hosted machine, but its peak guest memory is 18,405,414 bytes. The stage 1 measurements suggest approximately 48 host bytes per guest byte on this installation, and simulation is especially costly on the five-stage model. Instead of enumerating the full state space on the target, the solver performs a separate search for each input and retains only small read-only tables and a bounded search stack.

A search state is represented by two ranks: a permutation rank in the range 0 to 5039 and an orientation rank in the range 0 to 728. Both fit in `uint16_t`. The first rank encodes the arrangement of the seven movable corners; the second encodes their six independent twist values. The solved state has both ranks equal to zero. The input is still a 14-character cube string, which is converted into these ranks before searching.

Permutation and orientation evolve independently under each move. The solver therefore uses two factored transition tables instead of reconstructing and reranking all corners at every search node. Each table has three columns, one for each R, B, or D quarter-turn. Applying the same transition once, twice, or three times produces the corresponding quarter-turn, half-turn, or inverse quarter-turn. Each of these nine moves costs one in the half-turn metric (HTM).

### Transition tables and heuristic

Four tables are generated on the host in C. The two transition tables map abstract states to their successors, and the two pattern databases store exact distances to the solved abstract state. The abstract distances are computed using all nine unit-cost HTM moves, rather than treating a half-turn as two moves. These tables are linked into the target ELF's read-only `.rodata` section; the search itself still executes in Ripes.

| Table | Representation | Entries | Bytes |
| --- | --- | ---: | ---: |
| Permutation transitions | `uint16_t[5040][3]` | 15,120 | 30,240 |
| Orientation transitions | `uint16_t[729][3]` | 2,187 | 4,374 |
| Permutation PDB | `uint8_t[5040]` | 5,040 | 5,040 |
| Orientation PDB | `uint8_t[729]` | 729 | 729 |
| Total | | | **40,383** |

The heuristic is the maximum of the two abstract distances:

$$
h(s)=\max\bigl(h_{\mathrm{perm}}(s),h_{\mathrm{ori}}(s)\bigr).
$$

Any move sequence that solves the full cube also solves its permutation projection and its orientation projection. Each full move projects to an allowed abstract move with the same unit cost. Therefore, the shortest distance in either abstraction cannot exceed the full-state distance:

$$
h_{\mathrm{perm}}(s)\leq d(s),\qquad h_{\mathrm{ori}}(s)\leq d(s).
$$

Taking the maximum preserves this lower-bound property. Adding the two distances would not provide the same guarantee, because one move can contribute to solving both abstractions. H1 checks the chosen heuristic against the exact BFS distance over all 3,674,160 states. H2 independently checks the transition tables and abstract distances.

The PDB distances are stored as unpacked bytes. Their verified maxima are 7 for permutation and 6 for orientation. Packing would save memory but add extraction work to every heuristic lookup; the unpacked tables already fit comfortably within the budget. No full-state distance table is linked into the target.

### Non-recursive iterative-deepening search

The solver uses IDA* with an explicit stack rather than recursive function calls. The initial bound is the root heuristic. Each iteration performs a depth-first search and rejects a child when:

$$
\text{child depth}+h(\text{child})>\text{bound}.
$$

If no solution is found, the bound increases by one. The maximum bound is 11, using the diameter established by exhaustive host BFS. Search storage contains 12 frames, enough for depths 0 through 11, and an 11-byte move buffer.

Each frame records its initial ranks, the running ranks for the selected face, the next face and turn to try, and the face used to reach it. Before descending, the parent advances its turn counter so that backtracking resumes at the next candidate. When a frame is exhausted, the depth decreases and the previous frame resumes. This reproduces depth-first traversal without recursion or heap allocation.

Consecutive moves on the same face are excluded. Two such moves either cancel or combine into a single HTM move, so a shortest solution never needs adjacent moves on the same face. This reduces the available moves from nine at the root to six afterward without removing any shortest solution. It is search-tree pruning, not a global visited-state table; different paths can still reach the same state.

### Optimality and memory budget

For a shortest solution of length $d$, any prefix of length $g$ has a remaining solution of length $d-g$. Admissibility gives $h\leq d-g$ at that prefix, so $g+h\leq d$. Thus the heuristic cannot prune that shortest path when the bound reaches $d$. The same-face pruning also preserves shortest solutions. Since the root heuristic is no greater than $d$ and the bound increases one step at a time, no earlier bound can return a longer solution, and the first successful iteration returns a shortest solution. The goal test checks both ranks, rather than relying only on a zero heuristic.

The target avoids the baseline's 14,696,640-byte BFS queue and 3,674,160-byte full-state move table. Its four tables occupy 40,383 bytes, approximately 39.44 KiB. In the measured renderer-free assembly build, `.rodata` occupies 40,491 bytes including strings and alignment, `.data` is empty, and `.bss` reserves 1,024 bytes for the stack. Total static data is **41,515 bytes**, below the **131,072-byte** limit. The assembly allocates 192 bytes for its 12 explicit frames within the reserved stack; this frame storage is already covered by `.bss`, not an additional static allocation.

This design trades the baseline's constant-time table-guided answers for per-query heuristic search while keeping the target's memory bounded. H3 independently checks that the C search returns an optimal valid solution for every state. The target's separate exhaustive distance-11 performance measurements establish whether this memory choice also meets the Ripes instruction budget.
