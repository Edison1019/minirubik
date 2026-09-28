#include <stdio.h>
#include <stdint.h>
#include <string.h>

enum {
    CUBIES = 7,
    PERMUTATIONS = 5040,
    ORIENTATIONS = 729,
    STATES = PERMUTATIONS * ORIENTATIONS,
    MOVES = 9
};

typedef struct {
    uint8_t p[CUBIES], o[CUBIES];
} state_t;

static const uint8_t source[3][CUBIES] = {
    {1, 4, 2, 0, 3, 5, 6},
    {0, 1, 2, 4, 5, 6, 3},
    {0, 2, 5, 3, 1, 4, 6},
};
static const uint8_t twist[3][CUBIES] = {
    {1, 2, 0, 2, 1, 0, 0},
    {0, 0, 0, 1, 2, 1, 2},
    {0, 0, 0, 0, 0, 0, 0},
};

static state_t quarter_turn(state_t state, uint8_t face) {
    state_t result;
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t from = source[face][i];
        result.p[i] = state.p[from];
        result.o[i] = (uint8_t) ((state.o[from] + twist[face][i]) % 3U);
    }
    return result;
}

static uint32_t rank_state(const state_t *state) {
    uint32_t p = 0, o = 0;
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t smaller = 0;
        for (uint8_t j = (uint8_t) (i + 1U); j < CUBIES; ++j)
            if (state->p[j] < state->p[i])
                ++smaller;
        p = p * (CUBIES - i) + smaller;
    }
    for (uint8_t i = 0; i < 6; ++i)
        o = o * 3U + state->o[i];
    return p * ORIENTATIONS + o;
}

static void unrank_state(uint32_t rank, state_t *state) {
    uint8_t available[CUBIES] = {0, 1, 2, 3, 4, 5, 6};
    uint32_t p = rank / ORIENTATIONS, o = rank % ORIENTATIONS, f = 720;
    uint8_t sum = 0;
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t q = (uint8_t) (p / f);
        p %= f;
        state->p[i] = available[q];
        for (uint8_t j = q; j + 1U < CUBIES - i; ++j)
            available[j] = available[j + 1U];
        if (i < 5)
            f /= 6U - i;
    }
    for (uint8_t i = 6; i-- > 0;) {
        state->o[i] = (uint8_t) (o % 3U);
        sum = (uint8_t) (sum + state->o[i]);
        o /= 3U;
    }
    state->o[6] = (uint8_t) ((3U - sum % 3U) % 3U);
}

void generate_pdb(FILE *fp) {
    uint8_t pdb_ori[ORIENTATIONS];
    uint16_t queue_ori[ORIENTATIONS];
    memset(pdb_ori, 255, sizeof(pdb_ori));
    int head = 0, tail = 0;
    pdb_ori[0] = 0; queue_ori[tail++] = 0;
    state_t state, temp;
    
    while (head < tail) {
        uint16_t curr = queue_ori[head++];
        uint8_t depth = pdb_ori[curr];
        unrank_state((uint32_t) 0 * ORIENTATIONS + curr, &state);
        for (uint8_t face = 0; face < 3; ++face) {
            temp = state;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                temp = quarter_turn(temp, face);
                uint16_t next_o = (uint16_t)(rank_state(&temp) % ORIENTATIONS);
                if (pdb_ori[next_o] == 255) { 
                    pdb_ori[next_o] = depth + 1; queue_ori[tail++] = next_o;
                }
            }
        }
    }

    fprintf(fp, "const uint8_t pdb_orientation[%d] = {\n    ", ORIENTATIONS);
    for (int i = 0; i < ORIENTATIONS; ++i) {
        fprintf(fp, "%d, ", pdb_ori[i]);
        if ((i + 1) % 16 == 0 && i != ORIENTATIONS - 1) fprintf(fp, "\n    ");
    }
    fprintf(fp, "\n};\n\n");

    uint8_t pdb_perm[PERMUTATIONS];
    uint16_t queue_perm[PERMUTATIONS];
    memset(pdb_perm, 255, sizeof(pdb_perm)); 
    head = 0, tail = 0;
    pdb_perm[0] = 0; queue_perm[tail++] = 0;
    
    while (head < tail) {
        uint16_t curr = queue_perm[head++];
        uint8_t depth = pdb_perm[curr];
        unrank_state((uint32_t) curr * ORIENTATIONS + 0, &state);
        for (uint8_t face = 0; face < 3; ++face) {
            temp = state;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                temp = quarter_turn(temp, face);
                uint16_t next_p = (uint16_t)(rank_state(&temp) / ORIENTATIONS);
                if (pdb_perm[next_p] == 255) {
                    pdb_perm[next_p] = depth + 1; queue_perm[tail++] = next_p;
                }
            }
        }
    }

    fprintf(fp, "const uint8_t pdb_permutation[%d] = {\n    ", PERMUTATIONS);
    for (int i = 0; i < PERMUTATIONS; ++i) {
        fprintf(fp, "%d, ", pdb_perm[i]);
        if ((i + 1) % 16 == 0 && i != PERMUTATIONS - 1) fprintf(fp, "\n    ");
    }
    fprintf(fp, "\n};\n\n");
}

void generate_trans_tables(FILE *fp) {
    fprintf(fp, "const uint16_t ori_trans[%d][3] = {\n", ORIENTATIONS);
    for (int i = 0; i < ORIENTATIONS; i++) {
        fprintf(fp, "    {");
        state_t state;
        unrank_state(i, &state);
        for (int face = 0; face < 3; face++) {
            state_t next = quarter_turn(state, face);
            uint16_t next_o = rank_state(&next) % ORIENTATIONS;
            fprintf(fp, "%d%s", next_o, face == 2 ? "" : ", ");
        }
        fprintf(fp, "}%s\n", i == ORIENTATIONS - 1 ? "" : ",");
    }
    fprintf(fp, "};\n\n");

    fprintf(fp, "const uint16_t perm_trans[%d][3] = {\n", PERMUTATIONS);
    for (int i = 0; i < PERMUTATIONS; i++) {
        fprintf(fp, "    {");
        state_t state;
        unrank_state(i * ORIENTATIONS, &state);
        for (int face = 0; face < 3; face++) {
            state_t next = quarter_turn(state, face);
            uint16_t next_p = rank_state(&next) / ORIENTATIONS;
            fprintf(fp, "%d%s", next_p, face == 2 ? "" : ", ");
        }
        fprintf(fp, "}%s\n", i == PERMUTATIONS - 1 ? "" : ",");
    }
    fprintf(fp, "};\n\n");
}

int main() {
    FILE *fp = fopen("pdb_tables.h", "w");
    fprintf(fp, "#ifndef PDB_TABLES_H\n#define PDB_TABLES_H\n\n#include <stdint.h>\n\n");
    generate_pdb(fp);
    generate_trans_tables(fp);
    fprintf(fp, "#endif\n");
    fclose(fp);
    // printf("生成完畢！已將陣列寫入 pdb_tables.h\n");
    return 0;
}