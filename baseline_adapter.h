#ifndef BASELINE_ADAPTER_H
#define BASELINE_ADAPTER_H

#include <stdint.h>

enum { BASELINE_STATES = 3674160, BASELINE_ORIENTATIONS = 729,
       BASELINE_MAX_DEPTH = 11 };

typedef struct baseline_oracle baseline_oracle;

/* All oracle data comes from solver_baseline.c, not pdb_tables.h. */
baseline_oracle *baseline_oracle_create(void);
void baseline_oracle_destroy(baseline_oracle *oracle);
int baseline_oracle_distance(const baseline_oracle *oracle, uint32_t rank);
int baseline_oracle_verify(uint32_t rank, const uint8_t *path, int length);
int baseline_oracle_input(uint32_t rank, char input[15]);

#endif
