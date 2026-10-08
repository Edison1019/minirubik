"""Reproduce current assembly refinement experiments; no historical claims."""
import argparse
import datetime
import hashlib
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from compare_c_assembly import text_size
from measure_worst_case import input_offset, MOVES
from build_rv32i import verify_elf

ROOT = Path(__file__).resolve().parent
OLD = '''    add     t0, s10, t2
    lbu     t4, 0(t0)
    add     t0, s11, t3
    lbu     t5, 0(t0)
    bgeu    t4, t5, solve_child_h
    mv      t4, t5
solve_child_h:
    addi    t6, s4, 1          # child depth
    add     t0, t6, t4
    bgtu    t0, s3, solve_search
'''
BRANCHLESS = OLD.replace('    bgeu    t4, t5, solve_child_h\n    mv      t4, t5\n',
'''    sltu    t0, t4, t5
    sub     t0, zero, t0
    xor     t1, t4, t5
    and     t1, t1, t0
    xor     t4, t4, t1
''')
EARLY = '''    addi    t6, s4, 1          # child depth
    sub     t5, s3, t6         # remaining depth
    add     t0, s10, t2
    lbu     t4, 0(t0)
    bgtu    t4, t5, solve_search
    add     t0, s11, t3
    lbu     t4, 0(t0)
    bgtu    t4, t5, solve_search
solve_child_h:
'''

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ripes', required=True, type=Path)
    parser.add_argument('--offscreen', action='store_true', help='Optional Qt startup diagnostic')
    parser.add_argument('--jobs', type=int, default=1, choices=range(1, 4))
    parser.add_argument('--resume', action='store_true', help='Reuse completed runs with matching source/Ripes hashes')
    args = parser.parse_args()
    out = ROOT / 'measurements' / 'refinement'
    out.mkdir(parents=True, exist_ok=True)
    work = ROOT / '.build' / 'refinement'
    work.mkdir(parents=True, exist_ok=True)
    source = (ROOT / 'solver_rv32i.s').read_text(encoding='utf-8')
    if source.count(OLD) != 1:
        raise RuntimeError('Expected exactly one original heuristic block')
    gcc = next((ROOT / '.tools').glob('xpack*/bin/riscv-none-elf-gcc.exe')).resolve()
    verifier = work / 'verify.exe'
    subprocess.run(['gcc', '-O2', '-std=c99', '-Wno-sign-compare',
                    str(ROOT/'tests/verify_host_path.c'), '-o', str(verifier)], check=True)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    result = {'scope': 'New experiments, measured now; whole-program RV32_ISS, renderer disabled',
              'ripes_sha256': digest(args.ripes), 'original_source_sha256': digest(ROOT/'solver_rv32i.s'),
              'compiler': subprocess.check_output([str(gcc), '--version'], text=True).splitlines()[0],
              'variants': []}
    result['recorded_at_utc'] = datetime.datetime.utcnow().isoformat() + 'Z'
    result['measurement_script_sha256'] = digest(Path(__file__))
    result['linker_script_sha256'] = digest(ROOT/'solver_rv32i.ld')
    prior = {}
    if args.resume and (out/'results.json').exists():
        previous = json.loads((out/'results.json').read_text())
        if any(previous[k] != result[k] for k in ('ripes_sha256', 'original_source_sha256', 'compiler')):
            raise RuntimeError('Resume requires unchanged source, compiler, and Ripes')
        prior = {v['name']: v for v in previous['variants']}
    result['jobs'] = args.jobs
    result['qt_offscreen'] = args.offscreen
    pending = []
    cases = [('12345671111111', 0), ('25314672313211', 1),
             ('24316572122213', 8), ('21345671111111', 11), ('54721631111111', 11)]
    for name, block in [('baseline', OLD), ('branchless_max', BRANCHLESS), ('early_reject', EARLY)]:
        variant = out / (name + '.s')
        variant.write_text(source.replace(OLD, block), encoding='utf-8')
        elf = work / (name + '.elf')
        command = [str(gcc), '-march=rv32i', '-mabi=ilp32', '-mno-relax', '-nostdlib',
                   '-Wl,--no-relax', '-Wl,--build-id=none', '-Wl,-T,'+str(ROOT/'solver_rv32i.ld'),
                   str(variant), '-o', str(elf)]
        subprocess.run(command, cwd=ROOT, check=True)
        verify_elf(elf)
        blob = elf.read_bytes()
        offset = input_offset(blob)
        row = {'name': name, 'source_sha256': digest(variant), 'build_command': command,
               'text_bytes': text_size(blob), 'cases': []}
        result['variants'].append(row)
        for state, length in cases:
            old = prior.get(name, {})
            cached = next((c for c in old.get('cases', []) if c['input'] == state), None)
            if cached and old.get('source_sha256') == row['source_sha256']:
                encoded = ''.join(str(MOVES.index(t)) for t in cached['path'].split())
                subprocess.run([str(verifier), state, encoded], check=True)
                if cached['optimal_length'] != length or len(encoded) != length:
                    raise RuntimeError('Invalid cached length')
                if json.loads((out/f'{name}_{state}.json').read_text())['# instructions retired'] != cached['iret']:
                    raise RuntimeError('Cached telemetry differs')
                row['cases'].append(cached)
                continue
            patched = bytearray(blob)
            patched[offset:offset+14] = state.encode()
            current = work / f'{name}_{state}.elf'
            current.write_bytes(patched)
            report = out / f'{name}_{state}.json'
            if report.exists():
                report.unlink()
            command = [str(args.ripes.resolve()), '--mode', 'cli', '--src', str(current),
                       '-t', 'elf', '--proc', 'RV32_ISS', '--iret', '--exectime', '--runinfo',
                       '--json', '--timeout', '180000', '--output', str(report)]
            pending.append((row, state, length, report, command))
    environment = os.environ.copy()
    if args.offscreen:
        environment['QT_QPA_PLATFORM'] = 'offscreen'
    def measure(job):
        row, state, length, report, command = job
        p = subprocess.run(command, capture_output=True, text=True, timeout=600, env=environment)
        (out/f'{row["name"]}_{state}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
        if p.returncode:
            raise RuntimeError(f'Ripes exit={p.returncode}: {p.stdout+p.stderr}')
        tokens = p.stdout.replace('\x00', '').split('Program exited with code:')[0].split()
        if 'Program exited with code: 0' not in p.stdout+p.stderr or len(tokens) != length:
            raise RuntimeError(f'Failed run {row["name"]}: {state}')
        encoded = ''.join(str(MOVES.index(t)) for t in tokens)
        subprocess.run([str(verifier), state, encoded], check=True)
        return row, {'input': state, 'optimal_length': length, 'path': ' '.join(tokens),
                     'iret': json.loads(report.read_text())['# instructions retired'],
                     'independent_replay': True, 'command': command}
    (out/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = [executor.submit(measure, job) for job in pending]
        for future in as_completed(futures):
            row, item = future.result()
            row['cases'].append(item)
            (out/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            print(f'{row["name"]}: {item["input"]}: {item["iret"]:,}', flush=True)
    result['original_source_unchanged'] = digest(ROOT/'solver_rv32i.s') == result['original_source_sha256']
    for row in result['variants']:
        row['cases'].sort(key=lambda c: next(i for i, pair in enumerate(cases) if pair[0] == c['input']))
    result['complete'] = all(len(row['cases']) == len(cases) for row in result['variants'])
    (out/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')

if __name__ == '__main__':
    main()
