/* Exhaustive host H3 gate. See run_h3.py for the reproducible build.
 * Tables are defined only by solver.c; this checker imports no candidate data.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include "baseline_adapter.h"

extern int solve(uint16_t p, uint16_t o, uint8_t *path);

int main(void)
{
    time_t started = time(NULL);
    clock_t cpu_started = clock();
    puts("H3 exhaustive check: building independent baseline oracle...");
    fflush(stdout);
    baseline_oracle *oracle = baseline_oracle_create();
    if (!oracle) return EXIT_FAILURE;
    unsigned histogram[BASELINE_MAX_DEPTH + 1] = {0};
    uint32_t checked = 0;
    for (uint32_t rank = 0; rank < BASELINE_STATES; ++rank) {
        /* Fill with invalid moves so unwritten path entries fail validation.
         * Canaries check the caller's exact 11-byte path capacity as well. */
        struct { uint8_t before, path[BASELINE_MAX_DEPTH], after; } result;
        result.before = 0xA5;
        result.after = 0x5A;
        memset(result.path, UINT8_MAX, sizeof result.path);
        int expected = baseline_oracle_distance(oracle, rank);
        int length = solve((uint16_t)(rank / BASELINE_ORIENTATIONS),
                           (uint16_t)(rank % BASELINE_ORIENTATIONS), result.path);
        int bounds_ok = result.before == 0xA5 && result.after == 0x5A;
        int path_ok = baseline_oracle_verify(rank, result.path, length);
        if (expected < 0 || length != expected || !bounds_ok || !path_ok) {
            char input[15];
            baseline_oracle_input(rank, input);
            fprintf(stderr, "H3 FAIL: rank=%u input=%s expected=%d length=%d "
                    "path_valid=%d canaries_valid=%d\nPath:",
                    rank, input, expected, length, path_ok, bounds_ok);
            int show = length < 0 ? 0 : length;
            if (show > BASELINE_MAX_DEPTH) show = BASELINE_MAX_DEPTH;
            for (int i = 0; i < show; ++i)
                fprintf(stderr, " %u", (unsigned)result.path[i]);
            fprintf(stderr, "\nChecked %u states before failure; wall %.0f seconds.\n",
                    checked, difftime(time(NULL), started));
            baseline_oracle_destroy(oracle);
            return EXIT_FAILURE;
        }
        ++histogram[expected];
        ++checked;
        if (checked % 10000 == 0) {
            printf("Progress: %u / %u; wall %.0f seconds\n", checked,
                   (unsigned)BASELINE_STATES, difftime(time(NULL), started));
            fflush(stdout);
        }
    }
    baseline_oracle_destroy(oracle);
    if (checked != BASELINE_STATES || histogram[11] != 2644)
        return EXIT_FAILURE;
    for (unsigned i = 0; i <= BASELINE_MAX_DEPTH; ++i)
        printf("Distance %u: %u states\n", i, histogram[i]);
    printf("H3 PASS: all %u states returned optimal, valid solutions.\n", checked);
    printf("Wall time: %.0f seconds; C clock elapsed: %.2f seconds.\n",
           difftime(time(NULL), started), (double)(clock() - cpu_started) / CLOCKS_PER_SEC);
    return fflush(stdout) == EOF || ferror(stdout) ? EXIT_FAILURE : EXIT_SUCCESS;
}
