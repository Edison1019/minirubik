"""Collect reproducible H1-H4/T5-T7 artifacts without rerunning full H3."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from measure_worst_case import input_offset, MOVES

ROOT = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ripes', required=True, type=Path)
    args = parser.parse_args()
    out = ROOT/'measurements/gates'
    out.mkdir(parents=True, exist_ok=True)
    build = ROOT/'.build/gate_evidence'
    build.mkdir(parents=True, exist_ok=True)
    records = {}
    for gate in ('h1', 'h2'):
        exe = build/f'check_{gate}.exe'
        command = ['gcc', '-O2', '-std=c99', '-Wall', '-Wextra', '-Wpedantic']
        if gate == 'h1':
            command += ['-Wno-sign-compare']
        else:
            command += ['-Werror']
        command += [str(ROOT/f'check_{gate}.c'), '-o', str(exe)]
        subprocess.run(command, check=True)
        start = time.perf_counter()
        p = subprocess.run([str(exe)], capture_output=True, text=True, check=True)
        (out/f'{gate}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
        records[gate.upper()] = {'pass': True, 'wall_seconds': time.perf_counter()-start,
                                 'build_command': command}
        print(f'{gate.upper()} PASS', flush=True)
    h3 = json.loads((ROOT/'.build/h3/result.json').read_text())
    important = ['solver.c', 'solver_baseline.c', 'pdb_tables.h']
    for name in important:
        actual = hashlib.sha256((ROOT/name).read_bytes()).hexdigest()
        if actual != h3['sha256'][name]:
            raise RuntimeError('H3 source mismatch: '+name)
    if not h3['h3_pass']:
        raise RuntimeError('Full H3 did not pass')
    for name in ('h3.log', 'result.json'):
        shutil.copyfile(ROOT/'.build/h3'/name, out/('h3_'+name if name=='result.json' else name))
    records['H3'] = {'pass': True, 'states': 3674160, 'source_hashes_match': True,
                      'wall_seconds': h3['wall_seconds']}
    records['H4'] = {'applicable': False, 'reason': 'Unpacked byte PDBs and halfword transitions; no packed accessor.'}
    worst = ROOT/'.build/worst_case'
    for name in ('results.csv', 'summary.json', 'manifest.json', 'cases.csv'):
        shutil.copyfile(worst/name, out/('worst_case_'+name))
    subprocess.run([sys.executable, str(ROOT/'build_rv32i.py')], check=True)
    template = (ROOT/'solver_rv32i.elf').read_bytes()
    offset = input_offset(template)
    oracle = build/'baseline_verifier.exe'
    subprocess.run(['gcc', '-O2', '-std=c99', '-Wno-sign-compare',
                    str(ROOT/'baseline_adapter.c'), str(ROOT/'tests/export_distance11.c'),
                    '-o', str(oracle)], check=True)
    cases = [('12345671111111', 0), ('25314672313211', 1), ('21345671111111', 11)]
    runs = []
    for state, length in cases:
        blob = bytearray(template)
        blob[offset:offset+14] = state.encode()
        elf = build/'current.elf'
        elf.write_bytes(blob)
        for model in ('RV32_ISS', 'RV32_5S'):
            print(f'{model}: {state}', flush=True)
            report = out/f'{model}_{state}.json'
            if report.exists(): report.unlink()
            command = [str(args.ripes.resolve()), '--mode', 'cli', '--src', str(elf),
                       '-t', 'elf', '--proc', model, '--iret', '--exectime', '--runinfo',
                       '--json', '--timeout', '900000', '--output', str(report)]
            environment = os.environ.copy()
            environment['QT_QPA_PLATFORM'] = 'offscreen'
            p = subprocess.run(command, capture_output=True, text=True, timeout=920, check=True,
                               env=environment)
            (out/f'{model}_{state}.log').write_text(p.stdout+p.stderr, encoding='utf-8')
            if 'Program exited with code: 0' not in p.stdout+p.stderr:
                raise RuntimeError('Ripes solver failed')
            tokens = p.stdout.replace('\x00', '').split('Program exited with code:')[0].split()
            if len(tokens) != length or any(t not in MOVES for t in tokens):
                raise RuntimeError('Unexpected solution: '+str(tokens))
            permutation = [int(c)-1 for c in state[:7]]
            rank_p = 0
            for i, value in enumerate(permutation):
                rank_p = rank_p*(7-i)+sum(v<value for v in permutation[i+1:])
            rank_o = 0
            for c in state[7:13]: rank_o = rank_o*3+int(c)-1
            encoded = ''.join(str(MOVES.index(t)) for t in tokens)
            subprocess.run([str(oracle), '--verify', str(rank_p*729+rank_o), encoded], check=True)
            data = json.loads(report.read_text())
            runs.append({'model': model, 'input': state, 'length': length, 'path': ' '.join(tokens),
                         'iret': data['# instructions retired'], 'milliseconds': data['execution time (ms)'],
                         'independent_replay': True, 'command': command})
    records.update({'T5': {'pass': True, 'evidence': 'six runs plus full distance-11 independent replay'},
                    'T6': {'pass': True, 'input': '21345671111111', 'optimal_length': 11},
                    'T7': {'pass': True, 'scope': 'three required cases on ISS and RV32_5S; unknown grader inputs not tested'},
                    'target_runs': runs, 'ripes_build': 'v2.2.6-106-g5b8a616',
                    'ripes_sha256': hashlib.sha256(args.ripes.read_bytes()).hexdigest(),
                    'template_sha256': hashlib.sha256(template).hexdigest()})
    for state, _ in cases:
        paths = {r['path'] for r in runs if r['input']==state}
        if len(paths) != 1: raise RuntimeError('Models returned different paths')
    (out/'gates_summary.json').write_text(json.dumps(records, indent=2), encoding='utf-8')
    print('All collected gates passed; artifacts: measurements/gates/', flush=True)


if __name__ == '__main__':
    main()
