#include "../baseline_adapter.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char **argv)
{
    if (argc == 4 && strcmp(argv[1], "--verify") == 0) {
        uint8_t path[11];
        size_t length = strlen(argv[3]);
        if (length > 11) return 1;
        for (size_t i = 0; i < length; ++i) {
            if (argv[3][i] < '0' || argv[3][i] > '8') return 1;
            path[i] = (uint8_t)(argv[3][i] - '0');
        }
        unsigned long rank = strtoul(argv[2], NULL, 10);
        if (rank >= BASELINE_STATES) return 1;
        return baseline_oracle_verify((uint32_t)rank, path, (int)length) ? 0 : 1;
    }
    if (argc != 1) return 2;
    baseline_oracle *oracle = baseline_oracle_create();
    if (!oracle) return 1;
    unsigned count = 0;
    for (uint32_t rank = 0; rank < BASELINE_STATES; ++rank) {
        if (baseline_oracle_distance(oracle, rank) == 11) {
            char input[15];
            if (!baseline_oracle_input(rank, input)) return 1;
            printf("%u,%s\n", (unsigned)rank, input);
            ++count;
        }
    }
    baseline_oracle_destroy(oracle);
    return count == 2644 && fflush(stdout) == 0 ? 0 : 1;
}
