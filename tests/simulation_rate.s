# 64 passes over 128 KiB; 2097152 aligned word stores.
# No renderer, extensions, compiler, or console output inside the loop.
.text
.globl main
main:
    li t3, 64
pass:
    li t0, 0x100000
    li t1, 32768
loop:
    sw t1, 0(t0)
    addi t0, t0, 4
    addi t1, t1, -1
    bnez t1, loop
    addi t3, t3, -1
    bnez t3, pass
    li a0, 0
    li a7, 93
    ecall
