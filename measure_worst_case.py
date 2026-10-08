"""Measure all distance-11 inputs in Ripes ISS, with one reusable temporary ELF."""
import argparse
import csv
import hashlib
import json
import platform
import re
import struct
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
MOVES = ['R', 'R2', "R'", 'B', 'B2', "B'", 'D', 'D2', "D'"]
LIMIT = 50_000_000


def input_offset(blob):
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', blob)
    sections = [struct.unpack_from('<IIIIIIIIII', blob, h[6] + i*h[11])
                for i in range(h[12])]
    for s in sections:
        if s[1] != 2:
            continue
        strings = sections[s[6]]
        names = blob[strings[4]:strings[4]+strings[5]]
        for off in range(s[4], s[4]+s[5], s[9]):
            n, value, _, _, _, index = struct.unpack_from('<IIIBBH', blob, off)
            name = names[n:names.index(b'\0', n)]
            if name == b'input_str':
                target = sections[index]
                if target[2] != 2:
                    raise RuntimeError('input_str is not read-only allocated data')
                offset = target[4] + value - target[3]
                data = blob[offset:offset+15]
                if len(data) != 15 or data[14] != 0 or not data[:14].isdigit():
                    raise RuntimeError('Unexpected input string layout')
                return offset
    raise RuntimeError('input_str symbol not found')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ripes', required=True, type=Path)
    parser.add_argument('--cc', default='gcc', help='Native C compiler')
    parser.add_argument('--limit', type=int, help='Smoke test only; cannot establish full PASS')
    parser.add_argument('--resume', action='store_true')
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error('--limit must be positive')
    out = ROOT / '.build' / ('worst_case_smoke' if args.limit else 'worst_case')
    out.mkdir(parents=True, exist_ok=True)
    ripes = args.ripes.resolve()
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    source = ROOT / 'solver_rv32i.s'
    source_text = source.read_text(encoding='utf-8')
    if 'LED_MATRIX' in source_text:
        raise RuntimeError('Renderer added: explicitly verify it is compiled out before measuring')
    subprocess.run([sys.executable, str(ROOT/'build_rv32i.py')], cwd=ROOT, check=True)
    template = (ROOT/'solver_rv32i.elf').read_bytes()
    offset = input_offset(template)
    oracle = out/'export_distance11.exe'
    # Reuse the identical verifier on resume; PE timestamps can change its hash
    # even when rebuilding identical C sources.
    if not args.resume:
        subprocess.run([args.cc, '-O2', '-std=c99', '-Wall', '-Wextra', '-Wpedantic',
                        '-Werror', '-Wno-sign-compare', str(ROOT/'baseline_adapter.c'),
                        str(ROOT/'tests/export_distance11.c'), '-o', str(oracle)], check=True)
    exported = subprocess.check_output([str(oracle)], text=True)
    exported = '\n'.join(line for line in exported.splitlines()
                         if re.fullmatch(r'[0-9]+,[1-7]{7}[1-3]{7}', line)) + '\n'
    cases = [(int(line.split(',')[0]), line.split(',')[1])
             for line in exported.splitlines()]
    if len(cases) != 2644 or len({rank for rank, _ in cases}) != 2644:
        raise RuntimeError('Expected exactly 2644 unique distance-11 cases')
    (out/'cases.csv').write_text('rank,input\n'+exported, encoding='utf-8')
    manifest = {'ripes': str(ripes), 'ripes_sha256': digest(ripes),
                'template_sha256': hashlib.sha256(template).hexdigest(),
                'source_sha256': digest(source),
                'baseline_sha256': digest(ROOT/'solver_baseline.c'),
                'oracle_sha256': digest(oracle), 'platform': platform.platform(),
                'processor': 'RV32_ISS', 'renderer': 'absent', 'threshold': LIMIT,
                'measurement_scope': 'whole program, including verify and output'}
    manifest_file = out/'manifest.json'
    if args.resume:
        if not manifest_file.exists() or json.loads(manifest_file.read_text()) != manifest:
            raise RuntimeError('Cannot resume: build/environment differs')
    manifest_file.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    results_file = out/'results.csv'
    rows = list(csv.DictReader(results_file.open(newline=''))) if args.resume and results_file.exists() else []
    done = {int(r['rank']) for r in rows}
    if len(done) != len(rows) or not done.issubset({r for r, _ in cases}):
        raise RuntimeError('Invalid existing results')
    fields = ['rank', 'input', 'iret', 'milliseconds', 'path', 'status']
    selected = cases[:args.limit] if args.limit else cases
    started = time.time()
    with results_file.open('a' if args.resume else 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        if not args.resume or not rows:
            writer.writeheader()
        for rank, input_string in selected:
            if rank in done:
                continue
            blob = bytearray(template)
            blob[offset:offset+14] = input_string.encode('ascii')
            temporary = out/'current.elf'
            temporary.write_bytes(blob)
            telemetry = out/'current.json'
            if telemetry.exists():
                telemetry.unlink()
            command = [str(ripes), '--mode', 'cli', '--src', str(temporary),
                       '-t', 'elf', '--proc', 'RV32_ISS', '--iret', '--exectime',
                       '--runinfo', '--json', '--timeout', '120000', '--output', str(telemetry)]
            status, retired, milliseconds, path = 'execution_failure', '', '', ''
            try:
                process = subprocess.run(command, capture_output=True, text=True, timeout=140)
                log = process.stdout + process.stderr
                (out/'current.log').write_text(log, encoding='utf-8')
                if process.returncode == 0 and 'Program exited with code: 0' in log and telemetry.exists():
                    data = json.loads(telemetry.read_text())
                    retired = data['# instructions retired']
                    milliseconds = data['execution time (ms)']
                    tokens = process.stdout.replace('\x00', '').split('Program exited with code:')[0].split()
                    if len(tokens) == 11 and all(t in MOVES for t in tokens):
                        path = ' '.join(tokens)
                        encoded = ''.join(str(MOVES.index(t)) for t in tokens)
                        valid = subprocess.run([str(oracle), '--verify', str(rank), encoded]).returncode == 0
                        status = ('pass' if retired <= LIMIT else 'over_budget') if valid else 'invalid_path'
                    else:
                        status = 'invalid_length_or_output'
            except subprocess.TimeoutExpired:
                status = 'timeout'
            row = dict(zip(fields, [rank, input_string, retired, milliseconds, path, status]))
            writer.writerow(row)
            f.flush()
            rows.append(row)
            if status != 'pass' or len(rows) % 25 == 0 or args.limit:
                print(f'{len(rows)}/{len(selected)}: {input_string} iret={retired} {status}', flush=True)
            if status not in ('pass', 'over_budget'):
                print('Stopped on failed measurement; fix the cause before resuming.', flush=True)
                break
    counts = [int(r['iret']) for r in rows if str(r['iret']).isdigit()]
    worst = max((r for r in rows if str(r['iret']).isdigit()),
                key=lambda r: int(r['iret']), default=None)
    unchanged = digest(source) == manifest['source_sha256']
    summary = {'completed': len(rows), 'expected': 2644,
               'pass': not args.limit and len(rows) == 2644 and unchanged and all(r['status']=='pass' for r in rows),
               'failures': [r for r in rows if r['status'] != 'pass'],
               'worst_case': worst, 'maximum_iret': max(counts, default=None),
               'specified_vector': next((r for r in rows if r['input']=='21345671111111'), None),
               'source_unchanged': unchanged, 'this_run_wall_seconds': time.time()-started}
    (out/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    if summary['failures'] or (not args.limit and not summary['pass']):
        raise SystemExit(1)


if __name__ == '__main__':
    main()
