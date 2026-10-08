.option norvc
.option norelax
.text
.globl _start
_start:
    la sp, stack_top
    call reference_entry
    li a7, 93
    ecall
.section .bss,"aw",@nobits
.balign 16
stack_storage:
    .zero 4096
stack_top:
