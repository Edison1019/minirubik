"""Check known optimal lengths, independent move replay, and CLI failures."""
import argparse
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
MOVES = ['R', 'R2', "R'", 'B', 'B2', "B'", 'D', 'D2', "D'"]
INVALID = ['1234567111111', '123456711111111', '02345671111111',
           '82345671111111', '12345671111110', '12345671111114',
           '1234567111111a', '11345671111111', '12345671111112']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solver', default=str(ROOT/'solver'))
    parser.add_argument('--mini', default=str(ROOT/'mini'))
    parser.add_argument('--verifier', default=str(ROOT/'verify_host_path'))
    args = parser.parse_args()
    cases = []
    for line in (ROOT/'tests/solutions.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            state, reference = line.split('|')
            cases.append((state, len(reference.split())))
    cases.append(('25314672313211', 1))

    def check(binary, state, expected):
        p = subprocess.run([binary, state], capture_output=True, text=True, timeout=120)
        if p.returncode != 0:
            raise RuntimeError(f'{binary}: {state}: exit {p.returncode}: {p.stderr}')
        moves = p.stdout.split()
        if len(moves) != expected or any(m not in MOVES for m in moves):
            raise RuntimeError(f'{binary}: {state}: expected {expected} valid moves, got {moves}')
        encoded = ''.join(str(MOVES.index(m)) for m in moves)
        subprocess.run([args.verifier, state, encoded], check=True)

    for state, expected in cases:
        check(args.solver, state, expected)
    # mini rebuilds full BFS on every input; three representative cases suffice
    # here because the complete domain is covered by the separate H3 checker.
    for state, expected in [('12345671111111', 0), ('25314672313211', 1), ('21345671111111', 11)]:
        check(args.mini, state, expected)
    check(args.solver, '24316572122213', 8)
    default = subprocess.run([args.solver], capture_output=True, text=True, timeout=120)
    explicit = subprocess.run([args.solver, '24316572122213'], capture_output=True, text=True, timeout=120)
    if default.returncode != 0 or default.stdout != explicit.stdout:
        raise RuntimeError('solver default input does not match its documented sample')
    for binary in (args.solver, args.mini):
        rejected = [[state] for state in INVALID] + [['12345671111111', '12345671111111']]
        if binary == args.mini:
            rejected.append([])
        for arguments in rejected:
            p = subprocess.run([binary]+arguments, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if p.returncode != 2:
                raise RuntimeError(f'{binary}: {arguments}: expected invalid-input exit 2, got {p.returncode}')
        if os.name == 'posix':
            # A read-only stdout FD makes flushing fail without a SIGPIPE race.
            fd = os.open(os.devnull, os.O_RDONLY)
            try:
                p = subprocess.run([binary, '12345671111111'], stdout=fd, stderr=subprocess.DEVNULL)
            finally:
                os.close(fd)
            if p.returncode != 1:
                raise RuntimeError(f'{binary}: unwritable stdout: expected exit 1, got {p.returncode}')
    print('CLI PASS: optimal lengths, independent replay, default input, and rejection cases')


if __name__ == '__main__':
    main()
