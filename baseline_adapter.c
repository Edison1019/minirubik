#include "baseline_adapter.h"

/* Including the original file keeps its static functions available here.
 * Rename only its CLI entry; the baseline file itself is not modified. */
#define main baseline_original_main
#include "solver_baseline.c"
#undef main

struct baseline_oracle {
    uint8_t *distance;
};

baseline_oracle *baseline_oracle_create(void)
{
    uint8_t diameter = 0;
    uint8_t *moves = build_table(&diameter);
    if (!moves || diameter != BASELINE_MAX_DEPTH) {
        fprintf(stderr, "Oracle BFS failed or diameter is not 11.\n");
        free(moves);
        return NULL;
    }
    baseline_oracle *oracle = malloc(sizeof *oracle);
    if (!oracle) {
        free(moves);
        return NULL;
    }
    oracle->distance = malloc(BASELINE_STATES);
    if (!oracle->distance) {
        free(moves);
        free(oracle);
        return NULL;
    }
    memset(oracle->distance, UINT8_MAX, BASELINE_STATES);
    oracle->distance[0] = 0;

    /* Resolve the baseline's toward-solved chains with memoization. No
     * candidate transition table is consulted, even for the oracle distance. */
    for (uint32_t rank = 0; rank < BASELINE_STATES; ++rank) {
        uint32_t chain[BASELINE_MAX_DEPTH];
        unsigned count = 0;
        uint32_t cursor = rank;
        while (oracle->distance[cursor] == UINT8_MAX) {
            if (count == BASELINE_MAX_DEPTH || moves[cursor] >= MOVES)
                goto invalid_oracle;
            chain[count++] = cursor;
            state_t state;
            unrank_state(cursor, &state);
            state = apply_move(state, moves[cursor]);
            if (!valid(&state)) goto invalid_oracle;
            cursor = rank_state(&state);
            if (cursor >= BASELINE_STATES) goto invalid_oracle;
        }
        unsigned distance = oracle->distance[cursor];
        while (count) {
            if (++distance > BASELINE_MAX_DEPTH) goto invalid_oracle;
            oracle->distance[chain[--count]] = (uint8_t)distance;
        }
    }
    unsigned max_distance = 0, hardest = 0;
    for (uint32_t rank = 0; rank < BASELINE_STATES; ++rank) {
        unsigned d = oracle->distance[rank];
        if (d > BASELINE_MAX_DEPTH) goto invalid_oracle;
        if (d > max_distance) max_distance = d;
        hardest += d == BASELINE_MAX_DEPTH;
    }
    if (max_distance != BASELINE_MAX_DEPTH || hardest != 2644)
        goto invalid_oracle;
    printf("Oracle ready: %u states; diameter %u; distance-11 states %u.\n",
           (unsigned)BASELINE_STATES, max_distance, hardest);
    free(moves);
    return oracle;

invalid_oracle:
    fputs("Invalid baseline path or distance distribution.\n", stderr);
    free(moves);
    baseline_oracle_destroy(oracle);
    return NULL;
}

void baseline_oracle_destroy(baseline_oracle *oracle)
{
    if (oracle) {
        free(oracle->distance);
        free(oracle);
    }
}

int baseline_oracle_distance(const baseline_oracle *oracle, uint32_t rank)
{
    if (!oracle || rank >= BASELINE_STATES) return -1;
    return oracle->distance[rank];
}

int baseline_oracle_verify(uint32_t rank, const uint8_t *path, int length)
{
    if (rank >= BASELINE_STATES || !path || length < 0 ||
        length > BASELINE_MAX_DEPTH) return 0;
    state_t state;
    unrank_state(rank, &state);
    for (int i = 0; i < length; ++i) {
        if (path[i] >= MOVES) return 0;
        state = apply_move(state, path[i]);
    }
    return valid(&state) && rank_state(&state) == 0;
}

int baseline_oracle_input(uint32_t rank, char input[15])
{
    if (rank >= BASELINE_STATES || !input) return 0;
    state_t state;
    unrank_state(rank, &state);
    for (unsigned i = 0; i < CUBIES; ++i) {
        input[i] = (char)('1' + state.p[i]);
        input[i + CUBIES] = (char)('1' + state.o[i]);
    }
    input[14] = '\0';
    return 1;
}
