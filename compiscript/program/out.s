# auto-generated MIPS from tac
.data
newline: .asciiz "\n"

.text
.globl main
main:
  addiu $sp, $sp, -256
  sw $ra, 252($sp)
  jal user_main
  lw $ra, 252($sp)
  addiu $sp, $sp, 256
  li $v0, 10
  syscall


# --- function user_main ---
user_main:
  addiu $sp, $sp, -12
  sw $ra, 8($sp)
  sw $s0, 4($sp)
  li $s0, 0
L0:
  move $t8, $s0
  li $t9, 5
  slt $t8, $t8, $t9
  move $t0, $t8
  beq $t0, $zero, L1
  move $a0, $s0
  jal print
  move $t1, $v0
  move $t8, $s0
  li $t9, 1
  add $t8, $t8, $t9
  move $t1, $t8
  move $s0, $t1
  j L0
L1:
.epilogue_user_main:
  lw $s0, 4($sp)
  lw $ra, 8($sp)
  addiu $sp, $sp, 12
  jr $ra

# --- Runtime Helpers ---
print:
  li $v0, 1      # syscall for print_int
  syscall
  li $v0, 4      # syscall for print_string
  la $a0, newline
  syscall
  jr $ra
