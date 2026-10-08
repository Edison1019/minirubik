#include <stdint.h>
#include <stdio.h>
#include "pdb_tables.h"

enum {
    CUBIES = 7,
    PERMUTATIONS = 5040,
    ORIENTATIONS = 729,
    MOVES = 9,
    MAX_DEPTH = 11
};

/* One suspended DFS level. All search storage has a fixed upper bound. */
typedef struct {
    uint16_t p, o;
    uint16_t current_p, current_o;
    uint8_t face, turn, last_face;
} search_frame_t;

static uint8_t heuristic(uint16_t p, uint16_t o)
{
    uint8_t hp = pdb_permutation[p], ho = pdb_orientation[o];
    return hp > ho ? hp : ho;
}

/* Returns the solution length, or -1 for invalid indices/no solution.
 * path must have room for MAX_DEPTH bytes. No output is produced here.
 * Moves retain the order R, R2, R', B, B2, B', D, D2, D'.
 */
int solve(uint16_t initial_p, uint16_t initial_o, uint8_t *path)
{
    search_frame_t frames[MAX_DEPTH + 1];
    if (initial_p >= PERMUTATIONS || initial_o >= ORIENTATIONS || path == NULL)
        return -1;
    if (initial_p == 0 && initial_o == 0)
        return 0;

    for (unsigned bound = heuristic(initial_p, initial_o);
         bound <= MAX_DEPTH; ++bound) {
        unsigned depth = 0;
        frames[0] = (search_frame_t){initial_p, initial_o,
                                    initial_p, initial_o, 0, 0, 3};
        for (;;) {
            search_frame_t *frame = &frames[depth];
            if (depth == bound || frame->face == 3) {
                if (depth == 0) break;
                --depth;
                continue;
            }
            if (frame->face == frame->last_face || frame->turn == 3) {
                ++frame->face;
                frame->turn = 0;
                frame->current_p = frame->p;
                frame->current_o = frame->o;
                continue;
            }

            unsigned face = frame->face;
            uint16_t p = perm_trans[frame->current_p][face];
            uint16_t o = ori_trans[frame->current_o][face];
            frame->current_p = p;
            frame->current_o = o;
            /* Advance the parent before descending, so backtracking resumes
             * at the next turn rather than repeating the same child. */
            unsigned move = face * 3 + frame->turn++;
            unsigned child_depth = depth + 1;
            if (child_depth + heuristic(p, o) > bound)
                continue;
            path[depth] = (uint8_t)move;
            if (p == 0 && o == 0)
                return (int)child_depth;
            depth = child_depth;
            frames[depth] = (search_frame_t){p, o, p, o, 0, 0, (uint8_t)face};
        }
    }
    return -1;
}

/* Define SOLVER_NO_MAIN when linking solve() into a host checker. */
#ifndef SOLVER_NO_MAIN
static const char *const move_names[MOVES] = {
    "R", "R2", "R'", "B", "B2", "B'", "D", "D2", "D'"
};

typedef struct { uint8_t p[CUBIES], o[CUBIES]; } state_t;

static uint32_t rank_state(const state_t *state)
{
    uint32_t p = 0, o = 0;
    for (unsigned i = 0; i < CUBIES; ++i) {
        unsigned smaller = 0;
        for (unsigned j = i + 1; j < CUBIES; ++j)
            smaller += state->p[j] < state->p[i];
        p = p * (CUBIES - i) + smaller;
    }
    for (unsigned i = 0; i < CUBIES - 1; ++i)
        o = o * 3 + state->o[i];
    return p * ORIENTATIONS + o;
}

static int parse_state(const char *input, state_t *state)
{
    unsigned seen = 0, sum = 0;
    for (unsigned i = 0; i < 2 * CUBIES; ++i) {
        unsigned char c = (unsigned char)input[i];
        if (c < '1' || c > (i < CUBIES ? '7' : '3')) return 0;
        if (i < CUBIES) {
            unsigned bit = 1U << (c - '1');
            if (seen & bit) return 0;
            seen |= bit;
            state->p[i] = (uint8_t)(c - '1');
        } else {
            state->o[i - CUBIES] = (uint8_t)(c - '1');
            sum += c - '1';
        }
    }
    return input[2 * CUBIES] == '\0' && sum % 3 == 0;
}

static int verify_solution(uint16_t p, uint16_t o,
                           const uint8_t *path, int length)
{
    if (length < 0 || length > MAX_DEPTH) return 0;
    for (int i = 0; i < length; ++i) {
        if (path[i] >= MOVES) return 0;
        unsigned face = path[i] / 3, turns = path[i] % 3 + 1;
        for (unsigned turn = 0; turn < turns; ++turn) {
            p = perm_trans[p][face];
            o = ori_trans[o][face];
        }
    }
    return p == 0 && o == 0;
}

int main(int argc, char **argv)
{
    const char *input = argc == 1 ? "24316572122213" : argv[1];
    state_t state;
    uint8_t path[MAX_DEPTH];
    if (argc > 2 || !parse_state(input, &state)) {
        fputs("Expected a valid 14-digit cube state.\n", stderr);
        return 2;
    }
    uint32_t rank = rank_state(&state);
    uint16_t p = (uint16_t)(rank / ORIENTATIONS);
    uint16_t o = (uint16_t)(rank % ORIENTATIONS);
    int length = solve(p, o, path);
    if (!verify_solution(p, o, path, length)) {
        fputs("No valid solution found within 11 steps.\n", stderr);
        return 1;
    }
    for (int i = 0; i < length; ++i)
        printf("%s%s", i ? " " : "", move_names[path[i]]);
    putchar('\n');
    return fflush(stdout) == EOF || ferror(stdout) ? 1 : 0;
}
#endif
