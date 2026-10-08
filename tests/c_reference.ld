OUTPUT_ARCH(riscv)
ENTRY(_start)
PHDRS
{
    text PT_LOAD FLAGS(5);
    rodata PT_LOAD FLAGS(4);
    ram PT_LOAD FLAGS(6);
}
SECTIONS
{
    .text 0 : ALIGN(4) { *(.text .text.*) } :text
    .rodata 0x10000 : ALIGN(4) { *(.rodata .rodata.*) } :rodata
    .data : ALIGN(16) { *(.data .data.* .sdata .sdata.*) } :ram
    .bss (NOLOAD) : ALIGN(16) { *(.bss .bss.* .sbss .sbss.*) *(COMMON) } :ram
    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }
    ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x10000, ".text overlaps .rodata")
}
