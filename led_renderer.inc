# Included only when RENDER=1. All tables are read-only.
# Tables below map the baseline's corner-slot convention to a cube net.
.section .rodata, "a", @progbits
led_home_colors:
    .byte 0,3,2, 5,2,3, 5,1,2, 0,4,3, 5,3,4, 5,4,1, 0,1,4, 0,2,1
led_dest_facelets:
    .byte 3,12,9,21,11,14,20,7,10,1,16,13,23,15,18,22,19,6,0,4,17,2,8,5
led_pixel_origins:
    .byte 9,2,13,2,9,5,13,5,0,9,4,9,0,12,4,12,9,9,13,9,9,12,13,12,18,9,22,9,18,12,22,12,27,9,31,9,27,12,31,12,9,16,13,16,9,19,13,19
led_source:
    .byte 1,4,2,0,3,5,6, 0,1,2,4,5,6,3, 0,2,5,3,1,4,6
led_twist:
    .byte 1,2,0,2,1,0,0, 0,0,0,1,2,1,2, 0,0,0,0,0,0,0
.balign 4
led_palette:
    .word 0xffffff, 0xff8800, 0x00cc44, 0xee2222, 0x2255ff, 0xffff00
.equ LED_DELAY_ITERATIONS, 100000
.text

# a0 points to p[7],o[7]. Decode 24 stickers then draw the unfolded net.
# Stack: 24-byte facelet buffer, saved callee registers at 48..84.
led_draw:
    addi sp, sp, -96
    sw ra, 84(sp)
    sw s0, 48(sp)
    sw s1, 52(sp)
    sw s2, 56(sp)
    sw s3, 60(sp)
    sw s4, 64(sp)
    sw s5, 68(sp)
    sw s6, 72(sp)
    sw s7, 76(sp)
    mv s0, a0
    li s2, 0
led_corner:
    li t0, 7
    beq s2, t0, led_fixed_corner
    add t0, s0, s2
    lbu s4, 0(t0)
    lbu s5, 7(t0)
    j led_corner_slots
led_fixed_corner:
    li s4, 7
    li s5, 0
led_corner_slots:
    li s3, 0
led_slot:
    add t0, s3, s5
    li t1, 3
    bltu t0, t1, led_slot_index
    addi t0, t0, -3
led_slot_index:
    slli t1, s4, 1
    add t1, t1, s4
    add t1, t1, t0
    la t2, led_home_colors
    add t2, t2, t1
    lbu t3, 0(t2)
    slli t1, s2, 1
    add t1, t1, s2
    add t1, t1, s3
    la t2, led_dest_facelets
    add t2, t2, t1
    lbu t2, 0(t2)
    add t2, sp, t2
    sb t3, 0(t2)
    addi s3, s3, 1
    li t0, 3
    bltu s3, t0, led_slot
    addi s2, s2, 1
    li t0, 8
    bltu s2, t0, led_corner

    li s0, LED_MATRIX_0_BASE
    li s6, LED_MATRIX_0_WIDTH
    slli s6, s6, 2             # row stride in bytes
    li s7, LED_MATRIX_0_HEIGHT
    mv t0, s0
    li t1, 0
led_clear_row:
    li t2, LED_MATRIX_0_WIDTH
led_clear_pixel:
    sw zero, 0(t0)
    addi t0, t0, 4
    addi t2, t2, -1
    bnez t2, led_clear_pixel
    addi t1, t1, 1
    bltu t1, s7, led_clear_row

    li s2, 0
led_facelet:
    add t0, sp, s2
    lbu t0, 0(t0)
    slli t0, t0, 2
    la t1, led_palette
    add t1, t1, t0
    lw s4, 0(t1)
    slli t0, s2, 1
    la t1, led_pixel_origins
    add t1, t1, t0
    lbu t2, 0(t1)              # x
    lbu t3, 1(t1)              # y
    slli t2, t2, 2
    add s3, s0, t2
led_row_offset:
    beqz t3, led_rectangle
    add s3, s3, s6
    addi t3, t3, -1
    j led_row_offset
led_rectangle:
    li s5, 3
led_rectangle_row:
    mv t0, s3
    li t1, 4
led_rectangle_pixel:
    sw s4, 0(t0)
    addi t0, t0, 4
    addi t1, t1, -1
    bnez t1, led_rectangle_pixel
    add s3, s3, s6
    addi s5, s5, -1
    bnez s5, led_rectangle_row
    addi s2, s2, 1
    li t0, 24
    bltu s2, t0, led_facelet
    lw ra, 84(sp)
    lw s0, 48(sp)
    lw s1, 52(sp)
    lw s2, 56(sp)
    lw s3, 60(sp)
    lw s4, 64(sp)
    lw s5, 68(sp)
    lw s6, 72(sp)
    lw s7, 76(sp)
    addi sp, sp, 96
    ret

# Apply one output move to the display state; no target table reranking.
# a0=state, a1=move (0..8). Scratch state prevents in-place overwrite.
led_apply_move:
    addi sp, sp, -16
    li a2, 0
    li t0, 3
led_decode_move:
    bltu a1, t0, led_decoded_move
    addi a1, a1, -3
    addi a2, a2, 1
    j led_decode_move
led_decoded_move:
    addi a1, a1, 1
    slli t0, a2, 3
    sub t0, t0, a2            # face * 7
    la a3, led_source
    add a3, a3, t0
    la a4, led_twist
    add a4, a4, t0
led_apply_quarter:
    li a5, 0
led_apply_corner:
    add t0, a3, a5
    lbu t0, 0(t0)
    add t0, a0, t0
    lbu t1, 0(t0)
    add t2, sp, a5
    sb t1, 0(t2)
    lbu t1, 7(t0)
    add t0, a4, a5
    lbu t0, 0(t0)
    add t1, t1, t0
    addi t1, t1, -3
    bltz t1, led_twist_restore
    j led_twist_store
led_twist_restore:
    addi t1, t1, 3
led_twist_store:
    sb t1, 7(t2)
    addi a5, a5, 1
    li t0, 7
    bltu a5, t0, led_apply_corner
    li a5, 0
led_copy_corner:
    add t0, sp, a5
    lbu t1, 0(t0)
    add t0, a0, a5
    sb t1, 0(t0)
    addi a5, a5, 1
    li t0, 14
    bltu a5, t0, led_copy_corner
    addi a1, a1, -1
    bnez a1, led_apply_quarter
    addi sp, sp, 16
    ret

led_delay:
    li t0, LED_DELAY_ITERATIONS
led_delay_loop:
    addi t0, t0, -1
    bnez t0, led_delay_loop
    ret
