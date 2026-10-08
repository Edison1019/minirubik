/*
 * Host-side H2 checker for the four tables in pdb_tables.h.
 * Build: gcc -O2 -std=c99 -Wall -Wextra -Wpedantic check_h2.c -o check_h2
 * Run:   ./check_h2
 *
 * Reconstruct transitions from the baseline cubie model, independently of
 * the candidate transition tables. BFS on that reference graph reconstructs
 * the exact abstract distances. Compare every candidate entry, including
 * solved rows and maxima. Missing initializers that C fills with zero are
 * rejected whenever their resulting value differs from the reference.
 * A correct explicit zero and an identical implicit zero cannot be
 * distinguished at runtime; this verifies table contents, not provenance.
 * This is H2, not full-state admissibility (H1) or search optimality (H3).
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "pdb_tables.h"

enum { CUBIES = 7, ORI_STATES = 729, PERM_STATES = 5040, FACES = 3,
       MAX_DISTANCE = 11, UNVISITED = 255, MAX_DIAGNOSTICS = 10 };

/* C99 compile-time checks: reject unexpected table dimensions. */
#define COUNT(a) (sizeof(a) / sizeof((a)[0]))
typedef char ori_pdb_size[(COUNT(pdb_orientation) == ORI_STATES) ? 1 : -1];
typedef char perm_pdb_size[(COUNT(pdb_permutation) == PERM_STATES) ? 1 : -1];
typedef char ori_rows[(COUNT(ori_trans) == ORI_STATES) ? 1 : -1];
typedef char ori_cols[(COUNT(ori_trans[0]) == FACES) ? 1 : -1];
typedef char perm_rows[(COUNT(perm_trans) == PERM_STATES) ? 1 : -1];
typedef char perm_cols[(COUNT(perm_trans[0]) == FACES) ? 1 : -1];

/* Destination-to-source quarter-turn model, in R, B, D order.
 * These constants match solver_baseline.c, not the generated tables. */
static const uint8_t source[FACES][CUBIES] = {
    {1, 4, 2, 0, 3, 5, 6},
    {0, 1, 2, 4, 5, 6, 3},
    {0, 2, 5, 3, 1, 4, 6}
};
static const uint8_t twist[FACES][CUBIES] = {
    {1, 2, 0, 2, 1, 0, 0},
    {0, 0, 0, 1, 2, 1, 2},
    {0, 0, 0, 0, 0, 0, 0}
};
static const unsigned factorial[CUBIES] = {1, 1, 2, 6, 24, 120, 720};
static uint16_t reference_ori[ORI_STATES][FACES];
static uint16_t reference_perm[PERM_STATES][FACES];

static void decode_permutation(unsigned rank, uint8_t p[CUBIES])
{
    uint8_t available[CUBIES] = {0, 1, 2, 3, 4, 5, 6};
    for (unsigned i = 0; i < CUBIES; ++i) {
        unsigned weight = factorial[CUBIES - 1 - i];
        unsigned digit = rank / weight;
        rank %= weight;
        p[i] = available[digit];
        for (unsigned j = digit; j + 1 < CUBIES - i; ++j)
            available[j] = available[j + 1];
    }
}

static uint16_t encode_permutation(const uint8_t p[CUBIES])
{
    unsigned rank = 0;
    for (unsigned i = 0; i < CUBIES; ++i) {
        unsigned smaller = 0;
        for (unsigned j = i + 1; j < CUBIES; ++j)
            smaller += p[j] < p[i];
        rank += smaller * factorial[CUBIES - 1 - i];
    }
    return (uint16_t)rank;
}

static void decode_orientation(unsigned rank, uint8_t o[CUBIES])
{
    unsigned sum = 0;
    for (int i = CUBIES - 2; i >= 0; --i) {
        o[i] = (uint8_t)(rank % 3);
        sum += o[i];
        rank /= 3;
    }
    o[CUBIES - 1] = (uint8_t)((3 - sum % 3) % 3);
}

static uint16_t encode_orientation(const uint8_t o[CUBIES])
{
    unsigned rank = 0;
    for (unsigned i = 0; i < CUBIES - 1; ++i)
        rank = rank * 3 + o[i];
    return (uint16_t)rank;
}

static void build_reference_transitions(void)
{
    uint8_t before[CUBIES], after[CUBIES];
    for (unsigned i = 0; i < PERM_STATES; ++i) {
        decode_permutation(i, before);
        for (unsigned face = 0; face < FACES; ++face) {
            for (unsigned j = 0; j < CUBIES; ++j)
                after[j] = before[source[face][j]];
            reference_perm[i][face] = encode_permutation(after);
        }
    }
    for (unsigned i = 0; i < ORI_STATES; ++i) {
        decode_orientation(i, before);
        for (unsigned face = 0; face < FACES; ++face) {
            for (unsigned j = 0; j < CUBIES; ++j)
                after[j] = (uint8_t)((before[source[face][j]] +
                                      twist[face][j]) % 3);
            reference_ori[i][face] = encode_orientation(after);
        }
    }
}

static int check_transitions(const char *name, unsigned count,
                             const uint16_t actual[][FACES],
                             uint16_t expected[][FACES])
{
    unsigned invalid = 0, mismatches = 0, max_actual = 0, max_expected = 0;
    int solved_ok = 1;
    printf("\n%s\n", name);
    for (unsigned i = 0; i < count; ++i) {
        for (unsigned face = 0; face < FACES; ++face) {
            unsigned value = actual[i][face], ref = expected[i][face];
            invalid += value >= count;
            if (value > max_actual) max_actual = value;
            if (ref > max_expected) max_expected = ref;
            if (value != ref) {
                if (++mismatches <= MAX_DIAGNOSTICS)
                    printf("  Mismatch [%u][%u]: actual=%u expected=%u\n",
                           i, face, value, ref);
                if (i == 0) solved_ok = 0;
            }
        }
    }
    printf("  Entries checked: %u; invalid: %u; mismatches: %u\n",
           count * FACES, invalid, mismatches);
    printf("  Maximum: %u (expected %u)\n", max_actual, max_expected);
    printf("  Solved row R/B/D: %u/%u/%u (expected %u/%u/%u): %s\n",
           (unsigned)actual[0][0], (unsigned)actual[0][1],
           (unsigned)actual[0][2], (unsigned)expected[0][0],
           (unsigned)expected[0][1], (unsigned)expected[0][2],
           solved_ok ? "PASS" : "FAIL");
    int pass = invalid == 0 && mismatches == 0 && solved_ok &&
               max_actual == max_expected;
    printf("  RESULT: %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

static int check_pdb(const char *name, unsigned count, const uint8_t actual[],
                     uint16_t transitions[][FACES])
{
    uint8_t distance[PERM_STATES];
    uint16_t queue[PERM_STATES];
    unsigned head = 0, tail = 0;
    memset(distance, UNVISITED, sizeof(distance));
    distance[0] = 0;
    queue[tail++] = 0;
    /* HTM: each of 1, 2, or 3 quarter-turns is one BFS edge. */
    while (head < tail) {
        unsigned current = queue[head++];
        for (unsigned face = 0; face < FACES; ++face) {
            unsigned next = current;
            for (unsigned turn = 0; turn < 3; ++turn) {
                next = transitions[next][face];
                if (distance[next] == UNVISITED) {
                    distance[next] = (uint8_t)(distance[current] + 1);
                    queue[tail++] = (uint16_t)next;
                }
            }
        }
    }
    unsigned unpopulated = 0, invalid = 0, mismatches = 0;
    unsigned max_actual = 0, max_expected = 0;
    printf("\n%s\n", name);
    for (unsigned i = 0; i < count; ++i) {
        unsigned value = actual[i];
        unpopulated += value == UNVISITED;
        invalid += value > MAX_DISTANCE;
        if (value > max_actual) max_actual = value;
        if (distance[i] > max_expected) max_expected = distance[i];
        if (value != distance[i] && ++mismatches <= MAX_DIAGNOSTICS)
            printf("  Mismatch [%u]: actual=%u expected=%u\n",
                   i, value, (unsigned)distance[i]);
    }
    printf("  Entries checked: %u; reference reached: %u\n", count, tail);
    printf("  Unpopulated: %u; invalid: %u; mismatches: %u\n",
           unpopulated, invalid, mismatches);
    printf("  Maximum: %u (expected %u)\n", max_actual, max_expected);
    printf("  Solved entry: %u (expected 0): %s\n",
           (unsigned)actual[0], actual[0] == 0 ? "PASS" : "FAIL");
    int pass = tail == count && unpopulated == 0 && invalid == 0 &&
               mismatches == 0 && actual[0] == 0 &&
               max_actual == max_expected && max_expected <= MAX_DISTANCE;
    printf("  RESULT: %s\n", pass ? "PASS" : "FAIL");
    return pass;
}

int main(void)
{
    int pass = 1;
    build_reference_transitions();
    puts("H2 TABLE CHECK (independent cubie-model reference)");
    pass &= check_transitions("ori_trans", ORI_STATES,
                              ori_trans, reference_ori);
    pass &= check_transitions("perm_trans", PERM_STATES,
                              perm_trans, reference_perm);
    /* Use reference transitions even when candidate transitions fail. */
    pass &= check_pdb("pdb_orientation", ORI_STATES,
                      pdb_orientation, reference_ori);
    pass &= check_pdb("pdb_permutation", PERM_STATES,
                      pdb_permutation, reference_perm);
    puts(pass ? "\nH2 PASS" : "\nH2 FAIL");
    return pass ? EXIT_SUCCESS : EXIT_FAILURE;
}
