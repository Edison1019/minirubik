"""Build final solver.c with RV32I GCC and compare whole-program Ripes counts."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
import sys
from pathlib import Path
from measure_worst_case import input_offset, MOVES

ROOT = Path(__file__).resolve().parent


def text_size(blob):
    h = struct.unpack_from('<16sHHIIIIIHHHHHH', blob)
    sections = [struct.unpack_from('<IIIIIIIIII', blob, h[6]+i*h[11]) for i in range(h[12])]
    strings = sections[h[13]]
    names = blob[strings[4]:strings[4]+strings[5]]
    for s in sections:
        if names[s[0]:names.index(b'\0', s[0])] == b'.text':
            return s[5]
    raise RuntimeError('Missing .text')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ripes', required=True, type=Path)
    parser.add_argument('--gcc', type=Path)
    args = parser.parse_args()
    candidates = list((ROOT/'.tools').glob('xpack*/bin/riscv-none-elf-gcc.exe'))
    gcc = (args.gcc or (candidates[0] if candidates else None))
    if gcc is None:
        parser.error('Supply --gcc with a RISC-V GCC executable')
    gcc = gcc.resolve()
    ripes = args.ripes.resolve()
    out = ROOT/'.build/c_comparison'
    out.mkdir(parents=True, exist_ok=True)
    digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    sources = ['solver.c', 'pdb_tables.h', 'solver_rv32i.s', 'tests/c_reference_runtime.c',
               'tests/c_reference_start.s', 'tests/c_reference.ld', 'tests/ripes_stdio/stdio.h']
    before = {s: digest(ROOT/s) for s in sources}
    version = subprocess.check_output([str(gcc), '--version'], text=True).splitlines()[0]
    target = subprocess.check_output([str(gcc), '-dumpmachine'], text=True).strip()
    flags = ['-O2', '-march=rv32i', '-mabi=ilp32', '-mno-relax', '-msmall-data-limit=0']
    commands = []

    def run(command):
        commands.append(command)
        subprocess.run(command, cwd=ROOT, check=True)

    run([str(gcc)] + flags + ['-I', str(ROOT/'tests/ripes_stdio'),
        '-Dmain=solver_reference_main', '-c', str(ROOT/'solver.c'), '-o', str(out/'solver.o')])
    run([str(gcc)] + flags + ['-ffreestanding', '-fno-builtin', '-c',
        str(ROOT/'tests/c_reference_runtime.c'), '-o', str(out/'runtime.o')])
    c_elf = out/'solver_c.elf'
    run([str(gcc)] + flags + ['-nostdlib', '-Wl,--no-relax', '-Wl,--build-id=none',
        '-Wl,-T,'+str(ROOT/'tests/c_reference.ld'), '-Wl,-Map,'+str(out/'solver_c.map'),
        str(ROOT/'tests/c_reference_start.s'), str(out/'solver.o'), str(out/'runtime.o'),
        '-lgcc', '-o', str(c_elf)])
    objdump = gcc.with_name(gcc.name.replace('gcc', 'objdump'))
    disassembly = subprocess.check_output([str(objdump), '-d', str(c_elf)], text=True)
    (out/'solver_c.disassembly.txt').write_text(disassembly, encoding='utf-8')
    run([sys.executable, str(ROOT/'build_rv32i.py')])
    blobs = {'C': c_elf.read_bytes(), 'assembly': (ROOT/'solver_rv32i.elf').read_bytes()}
    offsets = {k: input_offset(v) for k, v in blobs.items()}
    # Host checker uses the exact baseline move model to independently replay paths.
    verifier = out/'baseline_verifier.exe'
    run(['gcc', '-O2', '-std=c99', '-Wno-sign-compare', str(ROOT/'baseline_adapter.c'),
         str(ROOT/'tests/export_distance11.c'), '-o', str(verifier)])
    cases = []
    for line in (ROOT/'tests/solutions.txt').read_text().splitlines():
        if line and not line.startswith('#'):
            state, path = line.split('|')
            cases.append((state, len(path.split())))
    cases += [('25314672313211', 1), ('54721631111111', 11)]
    rows = []
    for state, expected in cases:
        results = {}
        for model, blob in blobs.items():
            patched = bytearray(blob)
            patched[offsets[model]:offsets[model]+14] = state.encode('ascii')
            temporary = out/f'current_{model}.elf'
            temporary.write_bytes(patched)
            report = out/f'{state}_{model}.json'
            if report.exists(): report.unlink()
            command = [str(ripes), '--mode', 'cli', '--src', str(temporary), '-t', 'elf',
                       '--proc', 'RV32_ISS', '--iret', '--exectime', '--json', '--runinfo',
                       '--timeout', '180000', '--output', str(report)]
            commands.append(command)
            p = subprocess.run(command, capture_output=True, text=True, timeout=200, check=True)
            log = p.stdout+p.stderr
            (out/f'{state}_{model}.log').write_text(log, encoding='utf-8')
            if 'Program exited with code: 0' not in log:
                raise RuntimeError(f'{model} failed: {state}: {log}')
            tokens = p.stdout.replace('\x00', '').split('Program exited with code:')[0].split()
            if len(tokens) != expected or any(t not in MOVES for t in tokens):
                raise RuntimeError(f'{model} returned incorrect length: {state}: {tokens}')
            # Ranking is calculated independently in Python for the verifier input.
            permutation = [int(c)-1 for c in state[:7]]
            rank_p = 0
            for i, value in enumerate(permutation):
                rank_p = rank_p*(7-i)+sum(v<value for v in permutation[i+1:])
            rank_o = 0
            for c in state[7:13]: rank_o = rank_o*3+int(c)-1
            encoded = ''.join(str(MOVES.index(t)) for t in tokens)
            subprocess.run([str(verifier), '--verify', str(rank_p*729+rank_o), encoded], check=True)
            results[model] = {'iret': json.loads(report.read_text())['# instructions retired'],
                              'path': ' '.join(tokens)}
        if results['C']['path'] != results['assembly']['path']:
            raise RuntimeError(f'C and assembly paths differ: {state}')
        row = {'input': state, 'optimal_length': expected, **results,
               'assembly_reduction_percent': 100*(1-results['assembly']['iret']/results['C']['iret'])}
        rows.append(row)
        print(f"{state}: C={results['C']['iret']:,}; asm={results['assembly']['iret']:,}", flush=True)
    result = {'gcc': version, 'gcc_target': target, 'flags': flags,
              'exact_requested_executable_name': gcc.name in ('riscv64-unknown-elf-gcc', 'riscv64-unknown-elf-gcc.exe'),
              'ripes': str(ripes), 'ripes_sha256': digest(ripes), 'commands': commands,
              'source_sha256': before, 'sources_unchanged': before=={s:digest(ROOT/s) for s in sources},
              'text_bytes': {k:text_size(v) for k,v in blobs.items()}, 'cases': rows,
              'scope': 'whole-program; C includes Ripes adapter and RV32I libgcc helpers',
              'libgcc_helpers': sorted(set(re.findall(r'<(__\w+)>:', disassembly)))}
    (out/'results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    lines = ['# GCC C reference versus handwritten RV32I assembly', '',
             'The reference compiles the unchanged final `solver.c` with **'+version+'**.',
             'Its target triple is `'+target+'`. The core optimization and ISA options are',
             '`-O2 -march=rv32i -mabi=ilp32`. Additional target integration options are',
             '`-mno-relax -msmall-data-limit=0`; no LTO is enabled.', '',
             '**Compiler qualification:** the available compiler is named `riscv-none-elf-gcc`,',
             'rather than the assignment\'s literal `riscv64-unknown-elf-gcc`. This is a',
             'GNU GCC RV32I/ILP32 reference comparison, but acceptance of this toolchain',
             'as the specified reference has not been confirmed. To reproduce with the',
             'specified executable, supply its path through `--gcc`.', '',
             'The solver source is compiled in its own translation unit; only its main',
             'symbol is renamed at compile time. A small Ripes runtime adapter supplies',
             'the inline input and string-output/exit environment calls. Its minimal',
             'stdio interface implements the operations used by this program; it is not',
             'a general-purpose C library. GCC arithmetic support is linked from its',
             'RV32I libgcc. These helpers occur only in the compiler reference, not in',
             'the handwritten solver. The reference uses no heap or renderer.', '',
             'Both programs execute on the pinned Ripes RV32_ISS model. Retired counts',
             'cover the whole program, including ranking, search, path verification,',
             'and output. Both returned paths are replayed independently using the',
             'baseline model, their lengths are checked against known optimal values,',
             'and the C and assembly paths match for every tested input. The wrappers',
             'differ, so these counts are whole-program comparisons, not isolated search',
             'instruction counts. C additionally retains its input validation.', '',
             '| Input | Optimal moves | GCC C retired instructions | Assembly retired instructions | Assembly reduction |',
             '| --- | ---: | ---: | ---: | ---: |']
    for row in rows:
        lines.append('| `'+row['input']+'` | '+str(row['optimal_length'])+' | '+
                     format(row['C']['iret'], ',')+' | '+format(row['assembly']['iret'], ',')+
                     ' | '+format(row['assembly_reduction_percent'], '.2f')+'% |')
    lines += ['', '| Build | Linked `.text` bytes, renderer absent |', '| --- | ---: |',
              '| GCC C including startup, runtime adapter, and arithmetic helpers | '+str(result['text_bytes']['C'])+' |',
              '| Handwritten assembly including startup and software arithmetic | '+str(result['text_bytes']['assembly'])+' |', '',
              'The assembly does not win on the solved input: its fixed setup and',
              'verification overhead exceeds the C reference\'s overhead for that case.',
              'The assembly checks the root heuristic before reaching its goal test,',
              'whereas C returns immediately for the solved root. Search-heavy inputs',
              'benefit from the assembly\'s frame layout and register-held search state.',
              'The measured results support the whole-program improvement; the cost',
              'of individual optimizations is not separately established by this test.', '',
              'Reproduce with:', '', '```powershell',
              "python compare_c_assembly.py --ripes 'PATH_TO_Ripes.exe' --gcc 'PATH_TO_RISC_V_GCC.exe'",
              '```', '',
              'Raw telemetry, console logs, commands, source hashes, linked disassembly,',
              'and the GCC linker map are in `.build/c_comparison/`. `results.json`',
              'records the compiler identity and whether the source files stayed unchanged.']
    (ROOT/'C_ASSEMBLY_COMPARISON.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    print(json.dumps({k:result[k] for k in ['gcc','gcc_target','text_bytes','libgcc_helpers']}, indent=2))


if __name__ == '__main__':
    main()
