# auto-generated MIPS from tac
.text
.globl main

# --- function sum ---
sum:
  addi $sp, $sp, -32
  sw   $ra, 28($sp)
  sw   $fp, 24($sp)
  move $fp, $sp
  add  $t0, $a0, $a1
  move $v0, $t0
  lw   $fp, 24($sp)
  lw   $ra, 28($sp)
  addi $sp, $sp, 32
  jr   $ra

  addi $sp, $sp, -36
  sw   $ra, 32($sp)
  sw   $fp, 28($sp)
  move $fp, $sp
  sw   $s0, 24($sp)
  li   $s0, 0
  li   $a0, 2
  li   $a1, 3
  jal  sum
  move $t1, $v0
  move $s0, $t1
  move $v0, $s0
  lw   $s0, 24($sp)
  lw   $fp, 28($sp)
  lw   $ra, 32($sp)
  addi $sp, $sp, 36
  jr   $ra
