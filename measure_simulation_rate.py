"""Measure Ripes model throughput; preserve raw telemetry and build identity."""
import argparse
import hashlib
import json
import platform
from pathlib import Path
import statistics
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--ripes', required=True, type=Path)
args = parser.parse_args()
root = Path(__file__).resolve().parent
exe = args.ripes.resolve()
source = root / 'tests/simulation_rate.s'
out = root / '.build/simulation_rate'
out.mkdir(parents=True, exist_ok=True)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
help_result = subprocess.run([str(exe), '--mode', 'cli', '--help'],
                             capture_output=True, text=True, check=True)
(out / 'ripes_help.txt').write_text(help_result.stdout, encoding='utf-8')
result = {'ripes': str(exe), 'ripes_sha256': digest(exe),
          'source_sha256': digest(source), 'platform': platform.platform(),
          'processor': platform.processor(), 'models': {}}
for model in ('RV32_ISS', 'RV32_5S'):
    runs = []
    for trial in range(1, 4):
        report = out / f'{model}_{trial}.json'
        command = [str(exe), '--mode', 'cli', '--src', str(source), '-t', 'asm',
                   '--proc', model, '--iret', '--exectime', '--cycles',
                   '--runinfo', '--json', '--timeout', '180000',
                   '--output', str(report)]
        print(f'{model}: trial {trial}/3', flush=True)
        process = subprocess.run(command, capture_output=True, text=True,
                                 timeout=200, check=True)
        (out / f'{model}_{trial}.log').write_text(
            process.stdout + process.stderr, encoding='utf-8')
        if 'Program exited with code: 0' not in process.stdout + process.stderr:
            raise RuntimeError('Benchmark did not exit successfully')
        data = json.loads(report.read_text())
        retired = data['# instructions retired']
        milliseconds = data['execution time (ms)']
        if retired != 8388868 or milliseconds <= 0:
            raise RuntimeError(f'Unexpected telemetry: {data}')
        rate = retired * 1000 / milliseconds
        runs.append({'iret': retired, 'milliseconds': milliseconds,
                     'instructions_per_second': rate, 'command': command})
        print(f'  {retired} instructions, {milliseconds} ms, {rate:,.0f} instr/s',
              flush=True)
    result['models'][model] = {'runs': runs, 'median_instructions_per_second':
                              statistics.median(r['instructions_per_second'] for r in runs)}
(out / 'summary.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({m: d['median_instructions_per_second']
                  for m, d in result['models'].items()}, indent=2))
