"""Source-level checks, not Ripes execution or --iret. Requires gcc/solver.exe."""
import ast
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = 0x10000
REGS = ['zero', 'ra', 'sp', 'gp', 'tp', 't0', 't1', 't2', 's0', 's1',
        'a0', 'a1', 'a2', 'a3', 'a4', 'a5', 'a6', 'a7', 's2', 's3',
        's4', 's5', 's6', 's7', 's8', 's9', 's10', 's11', 't3', 't4', 't5', 't6']
subprocess.run([sys.executable, str(ROOT / 'build_rv32i.py'), '--source-only'], check=True)
source = (ROOT / 'solver_rv32i_ripes.s').read_text(encoding='utf-8')
labels, code, patches, memory = {}, [], [], {}
address, section = BASE, 'data'
for raw in source.splitlines():
    line = raw.split('#', 1)[0].strip()
    if not line:
        continue
    if line.endswith(':'):
        assert line[:-1] not in labels
        labels[line[:-1]] = len(code) if section == 'text' else address
        continue
    if line in ('.data', '.text'):
        section = line[1:]
        continue
    if line.startswith('.globl'):
        continue
    if section == 'text':
        code.append(re.split(r'[\s,]+', line))
        continue
    op, value = line.split(None, 1)
    if op == '.align':
        n = int(value)
        address = (address + n - 1) // n * n
        continue
    if op == '.zero':
        data = bytes(int(value))
    elif op == '.asciz':
        data = ast.literal_eval(value).encode() + b'\0'
    else:
        size = {'.byte': 1, '.half': 2, '.word': 4}[op]
        data = b''
        for item in value.split(','):
            item = item.strip()
            try:
                number = int(item)
            except ValueError:
                patches.append((address + len(data), item))
                number = 0
            data += number.to_bytes(size, 'little')
    for byte in data:
        memory[address] = byte
        address += 1
for at, name in patches:
    for i, byte in enumerate(labels[name].to_bytes(4, 'little')):
        memory[at + i] = byte

prefix = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const unsigned char image[] = {IMAGE};
static unsigned char mem[sizeof(image)];
static uint32_t r[32];
static unsigned minsp=STACK_TOP, call_depth;
static unsigned long long steps;
static const unsigned saved_regs[]={8,9,18,19,20,21,22,23,24,25,26,27};
static struct {uint32_t saved[12],sp,ra;} calls[32];
static void fail(const char *s) {fprintf(stderr,"%s\n",s); exit(1);}
static uint32_t load(uint32_t a,unsigned n) {
 if(a%n || a<BASE || a+n>BASE+sizeof(mem)) fail("Bad load/alignment");
 uint32_t v=0; for(unsigned i=0;i<n;++i) v|=(uint32_t)mem[a-BASE+i]<<(8*i);
 return v;
}
static void store(uint32_t a,unsigned n,uint32_t v) {
 if(a%n || a<STACK_LOW || a+n>STACK_TOP) fail("Bad store or table write");
 for(unsigned i=0;i<n;++i) mem[a-BASE+i]=(unsigned char)(v>>(8*i));
}
static void enter(unsigned pc) {
 if(call_depth==32 || r[2]%16) fail("Call depth/alignment");
 for(unsigned k=0;k<12;++k) calls[call_depth].saved[k]=r[saved_regs[k]];
 calls[call_depth].sp=r[2]; calls[call_depth].ra=pc; ++call_depth; r[1]=pc;
}
static void leave(void) {
 if(!call_depth) fail("Unmatched ret"); --call_depth;
 for(unsigned k=0;k<12;++k) if(calls[call_depth].saved[k]!=r[saved_regs[k]]) fail("Callee-saved register corrupted");
 if(calls[call_depth].sp!=r[2] || calls[call_depth].ra!=r[1]) fail("Stack/return address corrupted");
}
int main(int argc,char **argv) {
 if(argc!=2 || strlen(argv[1])!=14) fail("Expected 14-digit state");
 memcpy(mem,image,sizeof(mem)); memcpy(mem+INPUT-BASE,argv[1],14);
 unsigned pc=0;
 for(;;) {
  if(++steps>100000000) fail("Source instruction limit");
  switch(pc++) {CASES default: fail("Bad PC");}
  r[0]=0; if(r[2] && r[2]<minsp) minsp=r[2];
 }
}
'''
def reg(name):
    return 'r[%d]' % REGS.index(name)

cases = []
for pc, inst in enumerate(code):
    op, a = inst[0], inst[1:]
    if op == 'li':
        body = '%s=(uint32_t)(%s);' % (reg(a[0]), a[1])
    elif op == 'la':
        body = '%s=%d;' % (reg(a[0]), labels[a[1]])
    elif op == 'mv':
        body = '%s=%s;' % (reg(a[0]), reg(a[1]))
    elif op in ('add', 'sub', 'or', 'addi', 'andi', 'slli', 'srli'):
        symbol = {'add': '+', 'sub': '-', 'or': '|', 'addi': '+',
                  'andi': '&', 'slli': '<<', 'srli': '>>'}[op]
        rhs = '(uint32_t)(%s)' % a[2] if op in ('addi', 'andi', 'slli', 'srli') else reg(a[2])
        body = '%s=%s%s%s;' % (reg(a[0]), reg(a[1]), symbol, rhs)
    elif op in ('lbu', 'lhu', 'lw', 'sb', 'sh', 'sw'):
        match = re.fullmatch(r'(-?\d+)\((\w+)\)', a[1])
        addr = '%s+(uint32_t)(%s)' % (reg(match[2]), match[1])
        n = {'lbu': 1, 'lhu': 2, 'lw': 4, 'sb': 1, 'sh': 2, 'sw': 4}[op]
        if op.startswith('l'):
            body = '%s=load(%s,%d);' % (reg(a[0]), addr, n)
        else:
            body = 'store(%s,%d,%s);' % (addr, n, reg(a[0]))
    elif op in ('j', 'call'):
        body = ('enter(pc);' if op == 'call' else '') + 'pc=%d;' % labels[a[0]]
    elif op == 'ret':
        body = 'leave(); pc=r[1];'
    elif op in ('beqz', 'bnez', 'bltz'):
        expr = {'beqz': '%s==0', 'bnez': '%s!=0', 'bltz': '(int32_t)%s<0'}[op] % reg(a[0])
        body = 'if(%s) pc=%d;' % (expr, labels[a[1]])
    elif op in ('beq', 'bge', 'bgeu', 'bltu', 'bgt', 'bgtu'):
        symbol = {'beq': '==', 'bge': '>=', 'bgeu': '>=', 'bltu': '<', 'bgt': '>', 'bgtu': '>'}[op]
        x, y = reg(a[0]), reg(a[1])
        if op in ('bge', 'bgt'):
            x, y = '(int32_t)' + x, '(int32_t)' + y
        body = 'if(%s%s%s) pc=%d;' % (x, symbol, y, labels[a[2]])
    elif op == 'ecall':
        body = r'''if(r[17]==4) {
 uint32_t addr=r[10]; unsigned c; while((c=load(addr++,1))!=0) putchar(c);
 } else if(r[17]==93 || r[17]==10) {
 if(call_depth || r[2]!=STACK_TOP) fail("Unbalanced stack at exit");
 fprintf(stderr,"source_steps=%llu stack_bytes=%u\n",steps,STACK_TOP-minsp);
 return r[17]==93 ? (int)r[10] : 0;
 } else fail("Unsupported ecall");'''
    else:
        raise ValueError(inst)
    cases.append('case %d: {%s} break;' % (pc, body))

program = prefix.replace('IMAGE', ','.join(str(memory.get(i, 0)) for i in range(BASE, address)))
program = program.replace('CASES', '\n'.join(cases))
for name, value in [('BASE', BASE), ('STACK_LOW', labels['stack_storage']),
                    ('STACK_TOP', labels['stack_top']), ('INPUT', labels['input_str'])]:
    program = program.replace(name, str(value))

tests = []
for row in (ROOT / 'tests/solutions.txt').read_text().splitlines():
    if row and not row.startswith('#'):
        state, solution = row.split('|')
        tests.append((state, len(solution.split())))
tests.append(('25314672313211', 1))
with tempfile.TemporaryDirectory(prefix='rv32i_source_check_') as tmp:
    tmp = Path(tmp)
    (tmp / 'interpreter.c').write_text(program)
    exe = tmp / 'interpreter.exe'
    subprocess.run(['gcc', '-O2', '-std=c99', str(tmp / 'interpreter.c'), '-o', str(exe)], check=True)
    for state, length in tests:
        actual = subprocess.run([str(exe), state], capture_output=True, text=True)
        expected = subprocess.run([str(ROOT / 'solver.exe'), state], capture_output=True, text=True)
        assert actual.returncode == 0, (state, actual.stderr, actual.stdout)
        assert expected.returncode == 0, (state, expected.stderr)
        assert actual.stdout == expected.stdout, (state, actual.stdout, expected.stdout)
        assert len(actual.stdout.split()) == length, (state, actual.stdout)
        print('PASS:', state, repr(actual.stdout.strip()), actual.stderr.strip(), flush=True)
print('Source checks passed. Ripes T5-T7 and --iret remain separate checks.')
