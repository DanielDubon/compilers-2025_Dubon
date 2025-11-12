# auto-generated MIPS from tac
.text
.globl main

# --- function foo ---
foo:
  addi $sp, $sp, -36
  sw   $ra, 32($sp)
  sw   $fp, 28($sp)
  move $fp, $sp
  sw   $s0, 24($sp)
  lw   $s0, 36($fp)
  add  $t0, $a0, $a1
  add  $t1, $t0, $a2
  add  $t2, $t1, $a3
  add  $t3, $t2, $s0
  move $v0, $t3
  lw   $s0, 24($sp)
  lw   $fp, 28($sp)
  lw   $ra, 32($sp)
  addi $sp, $sp, 36
  jr   $ra

# --- function main ---
main:
  addi $sp, $sp, -32
  sw   $ra, 28($sp)
  sw   $fp, 24($sp)
  move $fp, $sp
  li   $a0, 1
  li   $a1, 2
  li   $a2, 3
  li   $a3, 4
  li $t9, 5
  addi $sp, $sp, -4
  sw $t9, 0($sp)
  jal  foo
  addi $sp, $sp, 4
  move $t4, $v0
  move $v0, $t4
  lw   $fp, 24($sp)
  lw   $ra, 28($sp)
  addi $sp, $sp, 32
  jr   $ra
