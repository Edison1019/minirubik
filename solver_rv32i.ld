OUTPUT_ARCH(riscv)
ENTRY(_start)

PHDRS
{
    text   PT_LOAD FLAGS(5); /* R + X */
    rodata PT_LOAD FLAGS(4); /* R, no W */
    ram    PT_LOAD FLAGS(6); /* R + W */
}

SECTIONS
{
    .text 0 : ALIGN(4)
    {
        *(.text .text.*)
    } :text

    .rodata 0x10000 : ALIGN(4)
    {
        *(.rodata .rodata.*)
    } :rodata

    .data : ALIGN(16)
    {
        *(.data .data.* .sdata .sdata.*)
    } :ram

    .bss (NOLOAD) : ALIGN(16)
    {
        *(.bss .bss.* .sbss .sbss.*)
        *(COMMON)
    } :ram

    /DISCARD/ : { *(.comment) *(.note*) *(.eh_frame*) }

    ASSERT(ADDR(.text) + SIZEOF(.text) <= 0x10000,
           ".text overlaps the read-only tables")
    ASSERT(SIZEOF(.data) == 0, "Unexpected writable initialized data")
    ASSERT(SIZEOF(.rodata) + SIZEOF(.data) + SIZEOF(.bss) <= 131072,
           "Static data exceeds the assignment's 128 KiB budget")
}
