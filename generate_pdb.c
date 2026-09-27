#include <stdio.h>
#include <stdint.h>
#include <string.h>

// ---------------------------------------------------------
// 請在這裡貼上原版程式碼中的基礎結構與函式：
// 包含 state_t 定義, CUBIES, ORIENTATIONS, PERMUTATIONS
// 以及 quarter_turn, rank_state, unrank_state
// ---------------------------------------------------------

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


static state_t quarter_turn(state_t state, uint8_t face)
{
    state_t result;
    /*@ loop invariant 0 <= i <= CUBIES;
        loop invariant \forall integer j; 0 <= j < i ==>
          result.p[j] == state.p[source[face][j]];
        loop invariant \forall integer j; 0 <= j < i ==>
          result.o[j] == (state.o[source[face][j]] + twist[face][j]) % 3;
        loop assigns i, result.p[0..6], result.o[0..6];
        loop variant CUBIES - i;
    */
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t from = source[face][i];
        result.p[i] = state.p[from];
        result.o[i] = (uint8_t) ((state.o[from] + twist[face][i]) % 3U);
    }
    return result;
}

static uint32_t rank_state(const state_t *state)
{
    uint32_t p = 0, o = 0;
    /*@ loop invariant 0 <= i <= CUBIES;
        loop invariant (i == 0 ==> p == 0) && (i == 1 ==> p <= 6) &&
          (i == 2 ==> p <= 41) && (i == 3 ==> p <= 209) &&
          (i == 4 ==> p <= 839) && (i == 5 ==> p <= 2519) &&
          (i >= 6 ==> p <= 5039);
        loop assigns i, p;
        loop variant CUBIES - i;
     */
    for (uint8_t i = 0; i < CUBIES; ++i) {
        uint8_t smaller = 0;
        /*@ loop invariant i + 1 <= j <= CUBIES;
            loop invariant smaller <= j - i - 1;
            loop assigns j, smaller;
            loop variant CUBIES - j;
         */
        for (uint8_t j = (uint8_t) (i + 1U); j < CUBIES; ++j)
            if (state->p[j] < state->p[i])
                ++smaller;
        p = p * (CUBIES - i) + smaller;
    }
    /*@ loop invariant 0 <= i <= 6;
        loop invariant (i == 0 ==> o == 0) && (i == 1 ==> o < 3) &&
          (i == 2 ==> o < 9) && (i == 3 ==> o < 27) &&
          (i == 4 ==> o < 81) && (i == 5 ==> o < 243) &&
          (i == 6 ==> o < 729);
        loop assigns i, o;
        loop variant 6 - i;
     */
    for (uint8_t i = 0; i < 6; ++i)
        o = o * 3U + state->o[i];
    return p * ORIENTATIONS + o;
}

/*@ requires \valid(state); requires rank < STATES; assigns *state; */
static void unrank_state(uint32_t rank, state_t *state)
{
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

void generate_orientation_pdb() {
    uint8_t pdb[ORIENTATIONS];
    uint16_t queue[ORIENTATIONS];
    memset(pdb, 255, sizeof(pdb)); // 255 代表未探索
    
    int head = 0, tail = 0;
    pdb[0] = 0;          // 方向 ID 0 代表已還原，距離 0 步
    queue[tail++] = 0;

    state_t state, temp;
    while (head < tail) {
        uint16_t curr = queue[head++];
        uint8_t depth = pdb[curr];

        // 技巧：利用原本的 unrank_state。
        // 我們固定位置 ID 為 0，只還原方向 ID (curr)
        unrank_state((uint32_t) 0 * ORIENTATIONS + curr, &state);

        for (uint8_t face = 0; face < 3; ++face) {
            temp = state;
            // 連續轉 1次(90度), 2次(180度), 3次(270度)
            for (uint8_t turn = 0; turn < 3; ++turn) {
                temp = quarter_turn(temp, face);
                uint16_t next_o = (uint16_t)(rank_state(&temp) % ORIENTATIONS);
                
                if (pdb[next_o] == 255) { // 如果是第一次見到的新狀態
                    pdb[next_o] = depth + 1;
                    queue[tail++] = next_o;
                }
            }
        }
    }

    // 印出 C 語言陣列格式
    printf("const uint8_t pdb_orientation[%d] = {\n    ", ORIENTATIONS);
    for (int i = 0; i < ORIENTATIONS; ++i) {
        printf("%d, ", pdb[i]);
        if ((i + 1) % 16 == 0 && i != ORIENTATIONS - 1) printf("\n    ");
    }
    printf("\n};\n\n");
}

void generate_permutation_pdb() {
    uint8_t pdb[PERMUTATIONS];
    uint16_t queue[PERMUTATIONS];
    memset(pdb, 255, sizeof(pdb)); // 255 代表未探索
    
    int head = 0, tail = 0;
    pdb[0] = 0;          // 位置 ID 0 代表已還原，距離 0 步
    queue[tail++] = 0;

    state_t state, temp;
    while (head < tail) {
        uint16_t curr = queue[head++];
        uint8_t depth = pdb[curr];

        // 技巧：我們固定方向 ID 為 0，只還原位置 ID (curr)
        unrank_state((uint32_t) curr * ORIENTATIONS + 0, &state);

        for (uint8_t face = 0; face < 3; ++face) {
            temp = state;
            for (uint8_t turn = 0; turn < 3; ++turn) {
                temp = quarter_turn(temp, face);
                uint16_t next_p = (uint16_t)(rank_state(&temp) / ORIENTATIONS);
                
                if (pdb[next_p] == 255) {
                    pdb[next_p] = depth + 1;
                    queue[tail++] = next_p;
                }
            }
        }
    }

    // 印出 C 語言陣列格式
    printf("const uint8_t pdb_permutation[%d] = {\n    ", PERMUTATIONS);
    for (int i = 0; i < PERMUTATIONS; ++i) {
        printf("%d, ", pdb[i]);
        if ((i + 1) % 16 == 0 && i != PERMUTATIONS - 1) printf("\n    ");
    }
    printf("\n};\n");
}

int main() {
    // printf("// 這是由 PC 端離線運算產生的 Pattern Databases\n");
    // printf("// 請將這兩組陣列複製貼上到 Ripes 用的 solver.c 檔案最上方\n\n");
    
    generate_orientation_pdb();
    generate_permutation_pdb();
    
    return 0;
}