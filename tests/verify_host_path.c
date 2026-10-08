/* Independent move replay; never use the candidate transition tables. */
#include <stdio.h>
#include <string.h>
#define main baseline_original_main
#include "../solver_baseline.c"
#undef main

int main(int argc, char **argv)
{
    state_t state;
    if (argc != 3 || !parse_state(argv[1], &state)) return 2;
    size_t length = strlen(argv[2]);
    if (length > 11) return 1;
    for (size_t i = 0; i < length; ++i) {
        if (argv[2][i] < '0' || argv[2][i] > '8') return 1;
        state = apply_move(state, (uint8_t)(argv[2][i] - '0'));
    }
    return rank_state(&state) == 0 ? 0 : 1;
}
