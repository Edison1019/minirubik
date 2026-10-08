"""Build/run the exhaustive native H3 gate without editing either solver.
Usage: python run_h3.py [--build-only] [--cc gcc]
The log and source hashes are saved in .build/h3/.
"""
import argparse
import hashlib
import json
import os
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BUILD = ROOT / '.build' / 'h3'
SOURCES = ['solver.c', 'solver_baseline.c', 'pdb_tables.h', 'baseline_adapter.c',
           'baseline_adapter.h', 'check_h3_full.c', 'run_h3.py']

def hashes():
    return {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in SOURCES}

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--build-only', action='store_true')
    parser.add_argument('--cc', default='gcc')
    args = parser.parse_args()
    BUILD.mkdir(parents=True, exist_ok=True)
    before = hashes()
    flags = ['-O2', '-std=c99', '-Wall', '-Wextra', '-Wpedantic']
    # Suppress the baseline's existing signedness warning for its adapter only.
    objects = []
    commands = []
    for name in ['solver.c', 'baseline_adapter.c', 'check_h3_full.c']:
        obj = BUILD / (Path(name).stem + '.o')
        extras = ['-DSOLVER_NO_MAIN', '-Werror'] if name == 'solver.c' else ['-Werror']
        if name == 'baseline_adapter.c':
            extras += ['-Wno-sign-compare']
        command = [args.cc] + flags + extras + ['-c', str(ROOT / name), '-o', str(obj)]
        commands.append(command)
        subprocess.run(command, cwd=str(ROOT), check=True)
        objects.append(str(obj))
    exe = BUILD / ('check_h3_full.exe' if os.name == 'nt' else 'check_h3_full')
    command = [args.cc] + objects + ['-o', str(exe)]
    commands.append(command)
    subprocess.run(command, cwd=str(ROOT), check=True)
    version = subprocess.check_output([args.cc, '--version'], text=True).splitlines()[0]
    manifest = {'compiler': version, 'commands': commands, 'sha256': before,
                'executable_sha256': hashlib.sha256(exe.read_bytes()).hexdigest()}
    if args.build_only:
        (BUILD / 'build.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print('Built:', exe)
        return
    started = time.perf_counter()
    pass_line = False
    with (BUILD / 'h3.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([str(exe)], cwd=str(ROOT), stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            print(line, end='', flush=True)
            log.write(line)
            log.flush()
            pass_line |= line.startswith('H3 PASS: all 3674160 states')
        status = process.wait()
    elapsed = time.perf_counter() - started
    unchanged = hashes() == before
    manifest.update({'wall_seconds': elapsed, 'exit_code': status,
                     'source_files_unchanged': unchanged,
                     'h3_pass': status == 0 and pass_line and unchanged})
    (BUILD / 'result.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print('Measured host wall time: %.3f seconds. Results: %s' % (elapsed, BUILD), flush=True)
    if not manifest['h3_pass']:
        raise SystemExit(status or 1)

if __name__ == '__main__':
    main()
