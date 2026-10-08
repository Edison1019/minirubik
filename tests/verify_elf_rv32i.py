"""Execute linked RV32I machine code in a host checker; NOT Ripes --iret.
Requires gcc, solver.exe, and solver_rv32i.elf. No ISA extensions are modeled.
The checker rejects target writes outside .bss, including writes to tables.
"""
import struct
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
blob = (ROOT / 'solver_rv32i.elf').read_bytes()
h = struct.unpack_from('<16sHHIIIIIHHHHHH', blob)
assert h[0][:7] == b'\x7fELF\x01\x01\x01' and h[2] == 243
sections = [struct.unpack_from('<IIIIIIIIII', blob, h[6] + i * h[11]) for i in range(h[12])]
ns = sections[h[13]]
names = blob[ns[4]:ns[4] + ns[5]]
def string(data, at):
    return data[at:data.index(b'\0', at)].decode()
named = {string(names, s[0]): s for s in sections}
text, ro, bss = named['.text'], named['.rodata'], named['.bss']
assert text[2] == 6 and ro[2] == 2 and bss[1] == 8 and bss[2] == 3
image = bytearray(max(s[3] + s[5] for s in sections if s[2] & 2))
for s in sections:
    if s[2] & 2 and s[1] != 8:
        image[s[3]:s[3] + s[5]] = blob[s[4]:s[4] + s[5]]
sym = named['.symtab']
st = sections[sym[6]]
strings = blob[st[4]:st[4] + st[5]]
symbols = {}
for off in range(sym[4], sym[4] + sym[5], sym[9]):
    n, value, size, info, other, index = struct.unpack_from('<IIIBBH', blob, off)
    symbols[string(strings, n)] = value

program = r'''
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static const unsigned char image[]={IMAGE};
static unsigned char mem[sizeof(image)];
static uint32_t r[32];
static void fail(const char *s) {fprintf(stderr,"%s\n",s);exit(1);}
static int32_t sx(uint32_t v,unsigned bits) {return (int32_t)(v<<(32-bits))>>(32-bits);}
static uint32_t load(uint32_t a,unsigned n) {
 if(a%n || a>sizeof(mem)-n) fail("Bad load/alignment");
 uint32_t v=0;for(unsigned i=0;i<n;++i) v|=(uint32_t)mem[a+i]<<(8*i);
 return v;
}
static void store(uint32_t a,unsigned n,uint32_t v) {
 if(a%n || a<BSS_START || a+n>BSS_END) fail("Bad store, including write to read-only data");
 for(unsigned i=0;i<n;++i) mem[a+i]=(unsigned char)(v>>(8*i));
}
int main(int argc,char **argv) {
 if(argc!=2 || strlen(argv[1])!=14) fail("Expected 14-character state");
 memcpy(mem,image,sizeof(mem));memcpy(mem+INPUT,argv[1],14);
 uint32_t pc=ENTRY,minsp=STACK_TOP;int stack_ready=0;
 unsigned long long steps=0;
 for(;;) {
  if(++steps>100000000) fail("Instruction limit");
  if(pc%4 || pc<TEXT_START || pc+4>TEXT_END) fail("PC outside text");
  uint32_t w=load(pc,4),next=pc+4;
  unsigned op=w&127,rd=(w>>7)&31,f3=(w>>12)&7,rs1=(w>>15)&31,rs2=(w>>20)&31,f7=w>>25;
  uint32_t a=r[rs1],b=r[rs2],v=0;int write=1;
  int32_t imm=sx(w>>20,12);
  switch(op) {
  case 0x37: v=w&0xfffff000;break;
  case 0x17: v=pc+(w&0xfffff000);break;
  case 0x6f: {
   uint32_t j=((w>>31)<<20)|(((w>>12)&255)<<12)|(((w>>20)&1)<<11)|(((w>>21)&1023)<<1);
   v=next;next=pc+(uint32_t)sx(j,21);break;
  }
  case 0x67: if(f3) fail("Non-RV32I jalr");v=next;next=(a+(uint32_t)imm)&~1U;break;
  case 0x63: {
   uint32_t j=((w>>31)<<12)|(((w>>7)&1)<<11)|(((w>>25)&63)<<5)|(((w>>8)&15)<<1);
   int take=0;write=0;
   switch(f3) {
   case 0:take=a==b;break;case 1:take=a!=b;break;
   case 4:take=(int32_t)a<(int32_t)b;break;case 5:take=(int32_t)a>=(int32_t)b;break;
   case 6:take=a<b;break;case 7:take=a>=b;break;default:fail("Invalid branch");
   }
   if(take) next=pc+(uint32_t)sx(j,13);break;
  }
  case 0x03:
   switch(f3) {
   case 0:v=(uint32_t)sx(load(a+imm,1),8);break;case 1:v=(uint32_t)sx(load(a+imm,2),16);break;
   case 2:v=load(a+imm,4);break;case 4:v=load(a+imm,1);break;case 5:v=load(a+imm,2);break;
   default:fail("Invalid load");
   }break;
  case 0x23: {
   int32_t si=sx(((w>>25)<<5)|((w>>7)&31),12);write=0;
   if(f3>2) fail("Invalid store");store(a+si,1U<<f3,b);break;
  }
  case 0x13:
   switch(f3) {
   case 0:v=a+imm;break;case 2:v=(int32_t)a<imm;break;case 3:v=a<(uint32_t)imm;break;
   case 4:v=a^(uint32_t)imm;break;case 6:v=a|(uint32_t)imm;break;case 7:v=a&(uint32_t)imm;break;
   case 1:if(f7) fail("Invalid slli");v=a<<rs2;break;
   case 5:if(f7==0) v=a>>rs2;else if(f7==32) v=(uint32_t)((int32_t)a>>rs2);else fail("Invalid shift");break;
   }break;
  case 0x33:
   if(f7!=0 && !(f7==32 && (f3==0 || f3==5))) fail("Non-RV32I arithmetic");
   switch(f3) {
   case 0:v=f7?a-b:a+b;break;case 1:v=a<<(b&31);break;case 2:v=(int32_t)a<(int32_t)b;break;
   case 3:v=a<b;break;case 4:v=a^b;break;
   case 5:v=f7?(uint32_t)((int32_t)a>>(b&31)):a>>(b&31);break;
   case 6:v=a|b;break;case 7:v=a&b;break;
   }break;
  case 0x73:
   write=0;if(w!=0x73) fail("Unsupported system instruction");
   if(r[17]==4) {uint32_t addr=r[10];unsigned c;while((c=load(addr++,1))) putchar(c);}
   else if(r[17]==93 || r[17]==10) {
    if(r[2]!=STACK_TOP) fail("Unbalanced stack");
    fprintf(stderr,"machine_steps=%llu stack_bytes=%u\n",steps,STACK_TOP-minsp);
    return r[17]==93?(int)r[10]:0;
   }else fail("Unsupported ecall");break;
  default:fail("Not a supported RV32I instruction");
  }
  if(write && rd) r[rd]=v;r[0]=0;pc=next;
  /* la sp uses AUIPC+ADDI; the intermediate address is not stack use. */
  if(r[2]==STACK_TOP) stack_ready=1;
  if(stack_ready && r[2]<minsp) minsp=r[2];
 }
}
'''
program = program.replace('IMAGE', ','.join(map(str, image)))
for name, value in [('BSS_START', bss[3]), ('BSS_END', bss[3] + bss[5]),
                    ('TEXT_START', text[3]), ('TEXT_END', text[3] + text[5]),
                    ('INPUT', symbols['input_str']), ('ENTRY', h[4]), ('STACK_TOP', symbols['stack_top'])]:
    program = program.replace(name, str(value))
tests = []
for row in (ROOT / 'tests/solutions.txt').read_text().splitlines():
    if row and not row.startswith('#'):
        state, solution = row.split('|')
        tests.append((state, len(solution.split())))
tests.append(('25314672313211', 1))
with tempfile.TemporaryDirectory(prefix='rv32i_machine_check_') as tmp:
    tmp = Path(tmp)
    (tmp / 'emulator.c').write_text(program)
    exe = tmp / 'emulator.exe'
    subprocess.run(['gcc', '-O2', '-std=c99', str(tmp / 'emulator.c'), '-o', str(exe)], check=True)
    for state, length in tests:
        actual = subprocess.run([str(exe), state], capture_output=True, text=True)
        expected = subprocess.run([str(ROOT / 'solver.exe'), state], capture_output=True, text=True)
        assert actual.returncode == 0, (state, actual.stderr, actual.stdout)
        assert expected.returncode == 0 and actual.stdout == expected.stdout, (state, actual.stdout, expected.stdout)
        assert len(actual.stdout.split()) == length, (state, actual.stdout)
        print('PASS:', state, repr(actual.stdout.strip()), actual.stderr.strip(), flush=True)
print('Linked machine-code checks passed; Ripes T5-T7/--iret remain to be measured.')
