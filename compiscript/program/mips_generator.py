#!/usr/bin/env python3
import sys
import re
from pathlib import Path

def is_temp(name):
    return re.fullmatch(r"t\d+", name) is not None

def is_label(line):
    return line.endswith(":")

def sanitize_ident(x):
    return x.strip()

class MIPSGen:
    def __init__(self, tac_lines):
        self.lines = [l.rstrip() for l in tac_lines if l.strip()]
        self.out_asm = []
        self.func_name = None
        self.local_map = {}
        self.spill_map = {}
        self.next_spill_offset = 0
        self.next_s_reg = 0
        self.call_args = []
        self.in_function = False
        self.current_func_buffer = []

    def emit(self, line=""):
        if self.in_function:
            self.current_func_buffer.append(line)
        else:
            self.out_asm.append(line)

    def start_function(self, label):
        self.func_name = label.rstrip(":")
        self.local_map = {}
        self.spill_map = {}
        self.next_spill_offset = 0
        self.next_s_reg = 0
        self.call_args = []
        self.in_function = True
        self.current_func_buffer = []
        self.emit(f"# --- start of function {self.func_name} ---")
        self.emit("# load parameters into s-registers")
        for i in range(4):
            self.emit(f"  move $s{i}, $a{i}")

    def end_function(self):
        if not self.in_function:
            return
        saved_s_regs = self.next_s_reg
        frame_size = self.next_spill_offset + 4 + saved_s_regs * 4
        prologue = [
            f"{self.func_name}:",
            f"  addiu $sp, $sp, -{frame_size}",
            f"  sw $ra, {frame_size - 4}($sp)"
        ]
        for i in range(saved_s_regs):
            prologue.append(f"  sw $s{i}, {frame_size - 8 - 4*i}($sp)")

        epilogue = [f".epilogue_{self.func_name}:"]
        for i in reversed(range(saved_s_regs)):
            epilogue.append(f"  lw $s{i}, {frame_size - 8 - 4*i}($sp)")
        epilogue += [
            f"  lw $ra, {frame_size - 4}($sp)",
            f"  addiu $sp, $sp, {frame_size}",
            "  jr $ra"
        ]

        self.out_asm.extend(prologue + self.current_func_buffer + epilogue)
        self.in_function = False
        self.current_func_buffer = []
        self.func_name = None

    def get_op_location(self, op):
        op = sanitize_ident(op)
        if op in self.local_map:
            return self.local_map[op]
        if is_temp(op):
            m = re.fullmatch(r"t(\d+)", op)
            idx = int(m.group(1))
            if idx < 10:
                reg = f"$t{idx}"
                self.local_map[op] = ('reg', reg)
                return ('reg', reg)
        if self.next_s_reg < 8:
            reg = f"$s{self.next_s_reg}"
            self.next_s_reg += 1
            self.local_map[op] = ('reg', reg)
            return ('reg', reg)
        if op not in self.spill_map:
            self.spill_map[op] = self.next_spill_offset
            self.next_spill_offset += 4
        offset = self.spill_map[op]
        self.local_map[op] = ('spill', offset)
        return ('spill', offset)

    def load_op(self, op, dest_reg):
        op = sanitize_ident(op)
        if re.fullmatch(r"-?\d+", op):
            self.emit(f"  li {dest_reg}, {op}")
            return
        kind, loc = self.get_op_location(op)
        if kind == 'reg':
            if loc != dest_reg:
                self.emit(f"  move {dest_reg}, {loc}")
        else:
            self.emit(f"  lw {dest_reg}, -{loc}($sp)")

    def store_op(self, src_reg, dest_op):
        dest_op = sanitize_ident(dest_op)
        kind, loc = self.get_op_location(dest_op)
        if kind == 'reg':
            if loc != src_reg:
                self.emit(f"  move {loc}, {src_reg}")
        else:
            self.emit(f"  sw {src_reg}, -{loc}($sp)")

    def translate(self):
        i = 0
        # Verificar si hay funciones definidas
        has_functions = any(line.strip() == "BeginFunc" for line in self.lines)

        # Si no hay funciones, crear main para todo el código global
        if not has_functions:
            self.emit(".globl main")
            self.emit("main:")
            self.emit("  addiu $sp, $sp, -256")
            self.emit("  sw $ra, 252($sp)")

        while i < len(self.lines):
            line = self.lines[i].strip()
            if is_label(line):
                if i+1 < len(self.lines) and self.lines[i+1].strip() == "BeginFunc":
                    self.end_function()
                    self.start_function(line)
                    i += 2
                    continue
                else:
                    self.emit(line)
                    i += 1
                    continue
            if line == "BeginFunc":
                self.end_function()
                self.start_function("anon_func:")
                i += 1
                continue
            if line == "EndFunc":
                self.end_function()
                i += 1
                continue

            # goto
            m = re.match(r"goto\s+(\w+)", line)
            if m:
                self.emit(f"  j {m.group(1)}")
                i += 1
                continue

            # if_false
            m = re.match(r"if_false\s+(.+)\s+goto\s+(.+)", line)
            if m:
                cond, label = m.groups()
                kind, loc = self.get_op_location(cond.strip())
                if kind == "reg":
                    self.emit(f"  beq {loc}, $zero, {label.strip()}")
                else:
                    self.load_op(cond.strip(), "$t8")
                    self.emit(f"  beq $t8, $zero, {label.strip()}")
                i += 1
                continue

            # param
            m = re.match(r"param\s+(.+)", line)
            if m:
                self.call_args.append(m.group(1).strip())
                i += 1
                continue

            # call
            m = re.match(r"(?:([\w\d]+)\s*=\s*)?call\s+([\w\d]+),\s*(\d+)", line)
            if m:
                dest, fname, num_args = m.groups()
                for j in range(min(int(num_args), 4)):
                    self.load_op(self.call_args[j], f"$a{j}")
                self.emit(f"  jal {fname}")
                self.call_args = []
                if dest:
                    self.store_op("$v0", dest)
                i += 1
                continue

            # return
            m = re.match(r"return(?:\s+(.+))?", line)
            if m:
                val = m.group(1)
                if val:
                    self.load_op(val, "$v0")
                if self.func_name:
                    self.emit(f"  j .epilogue_{self.func_name}")
                i += 1
                continue

            # assignment / binary
            m = re.match(r"([\w\d]+)\s*=\s*(.+)", line)
            if m:
                left, right = m.groups()
                mb = re.match(r"(.+)\s*([<>]=?|==|!=|[+\-*\/%])\s*(.+)", right)
                if mb:
                    L, op, R = mb.groups()
                    self.load_op(L, "$t8")
                    self.load_op(R, "$t9")
                    if op == "+": self.emit("  add $t8, $t8, $t9")
                    elif op == "-": self.emit("  sub $t8, $t8, $t9")
                    elif op == "*": self.emit("  mul $t8, $t8, $t9")
                    elif op == "/": self.emit("  div $t8, $t9\n  mflo $t8")
                    elif op == "%": self.emit("  div $t8, $t9\n  mfhi $t8")
                    elif op == "<": self.emit("  slt $t8, $t8, $t9")
                    elif op == ">": self.emit("  slt $t8, $t9, $t8")
                    elif op == "<=": self.emit("  slt $t8, $t9, $t8\n  xori $t8, $t8, 1")
                    elif op == ">=": self.emit("  slt $t8, $t8, $t9\n  xori $t8, $t8, 1")
                    elif op == "==": self.emit("  xor $t8, $t8, $t9\n  sltiu $t8, $t8, 1")
                    elif op == "!=": self.emit("  xor $t8, $t8, $t9\n  sltu $t8, $zero, $t8")
                    self.store_op("$t8", left)
                else:
                    self.load_op(right.strip(), "$t8")
                    self.store_op("$t8", left)
                i += 1
                continue

            self.emit(f"  # unhandled: {line}")
            i += 1

        # Cerrar cualquier función abierta
        self.end_function()

        # Si todo es global, cerrar main
        if not has_functions:
            self.emit("  lw $ra, 252($sp)")
            self.emit("  addiu $sp, $sp, 256")
            self.emit("  li $v0, 10")
            self.emit("  syscall")

        # Runtime helpers
        self.emit("\n# --- Runtime Helpers ---")
        self.emit("print:")
        self.emit("  li $v0, 1")
        self.emit("  syscall")
        self.emit("  li $v0, 4")
        self.emit("  la $a0, newline")
        self.emit("  syscall")
        self.emit("  jr $ra")

        full_asm = ["# auto-generated MIPS from tac", ".data", "newline: .asciiz \"\\n\"", "\n.text"]
        full_asm.extend(self.out_asm)
        return "\n".join(full_asm)

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 mips_generator.py tac.txt")
        sys.exit(1)
    path = Path(sys.argv[1])
    if not path.exists():
        print("File not found:", path)
        sys.exit(1)
    with path.open() as f:
        lines = f.readlines()
    gen = MIPSGen(lines)
    asm = gen.translate()
    out_path = path.parent / "out.s"
    with out_path.open("w") as f:
        f.write(asm + "\n")
    print("Wrote", out_path)

if __name__ == "__main__":
    main()
