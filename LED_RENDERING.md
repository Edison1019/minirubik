# LED cube rendering

The distributed `solver_rv32i_led.elf` is built for the LED peripheral base
**`0xf0000000`**, width 35, height 25, and the one-move input
**`25314672313211`**. `solver_rv32i.elf` uses the same input with rendering
disabled. Change `input_str` in `solver_rv32i.s` and rebuild to test another
input; an ELF contains the input chosen at build time.

The renderer displays the baseline's actual corner state as six 2-by-2 faces.
It draws the initial state after solving and verifying the path, then applies
each returned move to that state and redraws it. No stored animation is played.

## Ripes setup

1. In I/O, add an LED Matrix. Set **Width = 35**, **Height = 25**.
2. Note the displayed `LED_MATRIX_0_BASE` address.
3. Build a GUI ELF using that address, for example (only if the displayed
   address is actually `0xffff0000`):

```powershell
python build_rv32i.py --render --led-base 0xffff0000
```

4. Load **`solver_rv32i_led.elf`** with the LED peripheral still present.
5. Start with the one-move input `25314672313211`, then test solved and
   `21345671111111`. Change `input_str` in the canonical source and rebuild.
6. Observe the initial net, one redraw per returned move, and six uniform faces
   at the end. Capture screenshots or a recording as GUI evidence.

The GUI ELF preserves read-only `.rodata`. The base address is supplied from
the actual peripheral configuration as an assembly symbol, not embedded as a
literal MMIO address in renderer instructions. Width and height are set to the
required 35 and 25. Rebuild if the peripheral base changes.

`build_rv32i.py` also generates **`solver_rv32i_led_ripes.s`** for the built-in
editor. It uses the peripheral's own symbols and can help test the mapping,
but its tables are in `.data` because of the editor assembler's limitation.
Use the externally built LED ELF for the read-only section requirement.

## Measurement build

```powershell
python build_rv32i.py
```

This produces **`solver_rv32i.elf`** with `.equ RENDER, 0`. All renderer calls,
tables, delay loops, and MMIO accesses are assembled out. The GUI build uses
the same source with RENDER set to 1. The built-in-editor compatibility copies
are preprocessed by the build script because that assembler does not support
the canonical GNU conditional directives or read-only section directives.

With rendering disabled, `.text` remains 1356 bytes and static data remains
41515 bytes. The previous and new loaded `.text`, `.rodata`, and `.bss` were
compared and are identical, preserving the measured search code and counts.
The enabled test build uses 2044 `.text` bytes and 41680 static-data bytes.

## Mapping

The corner order is RUF, RDF, LDF, RUB, RDB, LDB, LUB, followed by the fixed
LUF corner. Each corner has an ordered set of three incident faces. At a
destination corner with orientation `o`, destination slot `s` takes the home
color at `(s + o) mod 3` of the cubie at that position. `led_mapping.py`
documents the geometry and derives the renderer's 24-entry mapping tables.

The net has U above F; its middle row is L, F, R, B; D is below F. Each sticker
is 4 pixels wide and 3 pixels high. Face origins are separated by one black
column/row. The net occupies 35 by 20 pixels and is offset downward by two
rows within the 35 by 25 display.

LED addresses use the row-major formula:

```text
LED_MATRIX_0_BASE + 4 * (y * LED_MATRIX_0_WIDTH + x)
```

The assembly advances row pointers using the symbolic width and clears using
both symbolic dimensions. There are no multiply/divide instructions. Colors
are U white, L orange, F green, R red, B blue, and D yellow. Display state is
updated with the same corner-source and twist rules as the baseline.

The delay is configurable in `led_renderer.inc` as `LED_DELAY_ITERATIONS`.
It is a busy loop, not calibrated wall-clock time: duration depends on the
processor model and GUI execution settings. Use a pipeline model or increase
the value if the animation is too fast. Every frame is redrawn even when the
GUI refresh rate does not show every intermediate write.

## Validation and limits

```powershell
python tests/verify_led.py
python tests/verify_elf_rv32i.py
```

The LED checker executes the actual linked RV32I instructions with a modeled
LED region. It rejects stores outside the stack and configured MMIO region,
checks all 875 pixels after the initial draw and every move, and independently
checks the corner orientation convention against physical 3D face turns.
Solved, one-move, eight-move, and eleven-move cases all passed (1, 2, 9, and 12
frames respectively). The CLI machine-code checker also passed all nine cases
with unchanged instruction counts. Maximum observed stack use is 304 bytes.

These host machine-code checks are not a GUI peripheral demonstration. Actual
Ripes GUI observation and screenshots are still required. The initial tests
used a synthetic base of `0xffff0000`; the distributed ELF was rebuilt and
retested with the actual I/O-panel base `0xf0000000`. Rebuild if your configured
peripheral base differs.
