CC ?= cc
CFLAGS ?= -O2 -std=c99 -Wall -Wextra -Wpedantic
PYTHON ?= python3
LED_BASE ?= 0xf0000000
RV32_CC ?=
FRAMA_C ?= frama-c
VECTORS := tests/solutions.txt
CLANG_FORMAT := $(shell command -v clang-format-20 2>/dev/null || command -v clang-format 2>/dev/null)
C_SOURCES := $(wildcard *.c *.h)

.PHONY: all elf elf-led check check-h3 prove prove-baseline clean indent

all: solver mini

# Rebuild through the script so ELF section and static-data checks always run.
elf:
	$(PYTHON) build_rv32i.py $(if $(RV32_CC),--cc "$(RV32_CC)")

elf-led:
	$(PYTHON) build_rv32i.py --render --led-base $(LED_BASE) $(if $(RV32_CC),--cc "$(RV32_CC)")

solver: solver.c pdb_tables.h
	$(CC) $(CFLAGS) solver.c -o $@

mini: mini.c
	$(CC) $(CFLAGS) $< -o $@

check_h1: check_h1.c solver_baseline.c pdb_tables.h
	$(CC) $(CFLAGS) -Wno-sign-compare check_h1.c -o $@

check_h2: check_h2.c pdb_tables.h
	$(CC) $(CFLAGS) check_h2.c -o $@

verify_host_path: tests/verify_host_path.c solver_baseline.c
	$(CC) $(CFLAGS) -Wno-sign-compare tests/verify_host_path.c -o $@

check: all check_h1 check_h2 verify_host_path $(VECTORS)
	./check_h1
	./check_h2
	$(PYTHON) tests/check_cli.py --solver ./solver --mini ./mini --verifier ./verify_host_path

# Explicit opt-in: full-domain search validation can take many minutes.
check-h3:
	$(PYTHON) run_h3.py --cc $(CC)

# Existing ACSL annotations describe the preserved baseline, not the new search.
prove: prove-baseline

prove-baseline: solver_baseline.c
	@log=$$(mktemp); trap 'rm -f "$$log"' 0 1 2 15; \
		$(FRAMA_C) -wp -wp-fct quarter_turn,rank_state,valid,parse_state \
		-wp-rte -rte-verbose 0 -wp-prover alt-ergo -wp-timeout 20 \
		-wp-cache none solver_baseline.c >"$$log" 2>&1; rc=$$?; \
		grep -Fvx -e '[wp] Warning: Skipped RTE guards: unaligned pointers (\aligned not supported)' \
		-e '[wp] Warning: Skipped RTE guards: invalid function pointer calls (\valid_function not supported)' "$$log"; \
		test $$rc -eq 0 && awk '$$1 == "[wp]" && $$2 == "Proved" && $$3 == "goals:" && $$4 > 0 && $$4 == $$6 { ok = 1 } END { exit !ok }' "$$log" && \
		! grep -Eq '(^|[[:space:]])(Timeout|Unknown|Failed):' "$$log"

indent:
ifeq ($(CLANG_FORMAT),)
	$(error clang-format 20 not found)
endif
	@$(CLANG_FORMAT) --version | grep -q 'version 20' || { echo "error: clang-format version 20 required"; exit 1; }
	$(CLANG_FORMAT) -i $(C_SOURCES)

clean:
	$(RM) solver mini check_h1 check_h2 verify_host_path
