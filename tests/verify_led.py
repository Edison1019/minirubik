"""Check actual LED ELF stores and all displayed frames; not Ripes evidence."""
import struct
import subprocess
import tempfile
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import led_mapping as mapping

PALETTE = [0xffffff, 0xff8800, 0x00cc44, 0xee2222, 0x2255ff, 0xffff00]
SOURCE = [[1,4,2,0,3,5,6], [0,1,2,4,5,6,3], [0,2,5,3,1,4,6]]
TWIST = [[1,2,0,2,1,0,0], [0,0,0,1,2,1,2], [0]*7]
MOVES = ['R','R2',"R'",'B','B2',"B'",'D','D2',"D'"]


def turn(p, o, face):
    return ([p[i] for i in SOURCE[face]],
            [(o[i]+TWIST[face][j]) % 3 for j,i in enumerate(SOURCE[face])])


def pixels(p, o):
    stickers = [None]*24
    for corner in range(8):
        cubie, orientation = (p[corner], o[corner]) if corner < 7 else (7,0)
        for slot in range(3):
            color = mapping.HOME_COLORS[cubie*3+(slot+orientation)%3]
            stickers[mapping.DEST_FACELETS[corner*3+slot]] = color
    assert all(c is not None for c in stickers)
    screen = [0]*875
    for index,color in enumerate(stickers):
        x,y = mapping.PIXELS[index]
        for dy in range(3):
            for dx in range(4): screen[(y+dy)*35+x+dx] = PALETTE[color]
    return screen


# Independently check the sticker convention against physical 3D turns.
# A turn's sign is inferred from the baseline's corner-position cycle.
normal = {'R':(1,0,0),'L':(-1,0,0),'U':(0,1,0),'D':(0,-1,0),'F':(0,0,1),'B':(0,0,-1)}
def rotate(v, axis, sign):
    x,y,z = v
    return [(x,-sign*z,sign*y),(sign*z,y,-sign*x),(-sign*y,sign*x,z)][axis]
for face, axis, layer in [(0,0,1),(1,2,-1),(2,1,-1)]:
    destination = SOURCE[face].index(next(i for i,c in enumerate(mapping.COORDS[:7]) if c[axis]==layer))
    origin = SOURCE[face][destination]
    sign = next(s for s in (-1,1) if rotate(mapping.COORDS[origin],axis,s)==mapping.COORDS[destination])
    for dest,src in enumerate(SOURCE[face]):
        for slot,homeface in enumerate(mapping.CORNERS[src]):
            n = normal[homeface]
            if mapping.COORDS[src][axis]==layer: n=rotate(n,axis,sign)
            newslot=(slot-TWIST[face][dest])%3
            assert n==normal[mapping.CORNERS[dest][newslot]], (face,dest,slot)

namespace = {'__file__': str(ROOT/'tests/verify_elf_rv32i.py'), '__name__':'led_check'}
prefix = (ROOT/'tests/verify_elf_rv32i.py').read_text().split("program = program.replace('IMAGE'")[0]
prefix = prefix.replace("ROOT / 'solver_rv32i.elf'", "ROOT / 'solver_rv32i_led.elf'")
exec(prefix, namespace)
symbols = namespace['symbols']
base = symbols['LED_MATRIX_0_BASE']
assert symbols['LED_MATRIX_0_WIDTH']==35 and symbols['LED_MATRIX_0_HEIGHT']==25
program = namespace['program'].replace('static uint32_t r[32];',
    'static uint32_t r[32],pixels[875]; static FILE *frames;')
program = program.replace('if(argc!=2 ||', 'if(argc!=3 ||')
program = program.replace('memcpy(mem,image,sizeof(mem));',
    'frames=fopen(argv[2],"wb");if(!frames)fail("No frame file");memcpy(mem,image,sizeof(mem));')
program = program.replace('if(a%n || a<BSS_START',
    'if(a>=LED_BASE && a<LED_END){if(n!=4 || a%4)fail("Bad MMIO store");pixels[(a-LED_BASE)/4]=v;return;}\n if(a%n || a<BSS_START')
program = program.replace('uint32_t w=load(pc,4),next=pc+4;',
    'if(pc==LED_DELAY)fwrite(pixels,sizeof(pixels),1,frames);\n uint32_t w=load(pc,4),next=pc+4;')
replacements = [('IMAGE', ','.join(map(str,namespace['image']))),
                ('BSS_START',namespace['bss'][3]), ('BSS_END',namespace['bss'][3]+namespace['bss'][5]),
                ('TEXT_START',namespace['text'][3]), ('TEXT_END',namespace['text'][3]+namespace['text'][5]),
                ('INPUT',symbols['input_str']), ('ENTRY',namespace['h'][4]),
                ('STACK_TOP',symbols['stack_top']), ('LED_BASE',base), ('LED_END',base+3500),
                ('LED_DELAY',symbols['led_delay'])]
for key,value in replacements: program=program.replace(key,str(value))
cases=['12345671111111','25314672313211','21345671111111','24316572122213']
with tempfile.TemporaryDirectory(prefix='led_check_') as directory:
    folder=Path(directory)
    (folder/'emulator.c').write_text(program)
    exe=folder/'emulator.exe'
    subprocess.run(['gcc','-O2','-std=c99',str(folder/'emulator.c'),'-o',str(exe)],check=True)
    for state in cases:
        frames=folder/'frames.bin'
        result=subprocess.run([str(exe),state,str(frames)],capture_output=True,text=True,check=True)
        moves=result.stdout.split()
        reference=subprocess.check_output([str(ROOT/'solver.exe'),state],text=True).split()
        assert moves==reference
        raw=frames.read_bytes()
        assert len(raw)==(len(moves)+1)*3500
        p=[int(c)-1 for c in state[:7]];o=[int(c)-1 for c in state[7:]]
        for step in range(len(moves)+1):
            actual=list(struct.unpack_from('<875I',raw,step*3500))
            assert actual==pixels(p,o), (state,step)
            if step<len(moves):
                move=MOVES.index(moves[step])
                for _ in range(move%3+1): p,o=turn(p,o,move//3)
        assert p==list(range(7)) and o==[0]*7
        print('LED PASS:',state,'frames=',len(moves)+1,result.stderr.strip())
print('All actual machine-code LED frames match the independent reference.')
