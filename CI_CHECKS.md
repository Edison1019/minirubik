# Native checks and CI

On Linux:

```sh
make check
```

This builds the final solver, the preserved `mini` baseline, H1 and H2 checkers,
and an independent baseline-model path verifier. H1 exhaustively checks
heuristic admissibility, and H2 reconstructs and compares all four tables.
The CLI checker checks optimal lengths for the known vectors and independently
replays each returned path. Different shortest move sequences are accepted.
It also checks the final solver's default input, malformed inputs, extra
arguments, and (on POSIX) an unwritable stdout. `mini` still requires one input
argument; the final solver supports a default input.

On this Windows installation:

```powershell
& 'C:\mingw64\bin\mingw32-make.exe' check CC=gcc PYTHON=python 'SHELL=C:/Program Files/Git/bin/bash.exe'
```

Full-domain H3 is a separate, explicit command:

```sh
make check-h3
```

The GitHub workflow runs `make check` on pushes and pull requests. To run H3,
choose **Run workflow** and enable **full_h3**. H3 is not replaced by the sampled
CLI tests. Target Ripes checks, performance measurements, and LED rendering are
separate from this native CI.

`make prove-baseline` (also available as `make prove`) retains the existing
Frama-C checks for the annotated functions in `solver_baseline.c`. It is not a
formal proof of the new iterative search, and it is no longer run as though it
were one in CI. Frama-C and Alt-Ergo must be installed to use this optional
target; it was not executed in the local Windows validation.
