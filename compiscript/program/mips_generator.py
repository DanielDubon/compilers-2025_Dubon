import sys
import re
from pathlib import Path

FRAME_SIZE = 32
RETURN_MARKER = "__RETURN_MARKER__"
MAX_EXTRAS_TO_LOAD = 16

def is_temp(name):
    return re.fullmatch(r"t\d+", name) is not None

def is_label(line):
    return line.endswith(":")

def reg_for_temp(name):
    m = re.fullmatch(r"t(\d+)", name)
    if not m:
        return None
    idx = int(m.group(1))
    return f"$t{idx}"

def sanitize_ident(x):
    return x.strip()

class MIPSGen:
    def __init__(self, tac_lines):
        self.lines = [l.rstrip() for l in tac_lines if l.strip()!=""]
        self.out = []
        self.func = None
        self.local_map = {}
        self.next_s = 0
        self.unk_param_order = {}
        self.unk_param_regs = {}
        self.next_param_idx = 0
        self.call_args = []
        self.returned = False
        self.current_func_buffer = []
        self.in_function = False
        self.base_frame = FRAME_SIZE
        self.saved_s_count = 0

    def emit(self, line=""):
        if self.in_function:
            self.current_func_buffer.append(line)
        else:
            self.out.append(line)

    def emit_out(self, line=""):
        self.out.append(line)

    def start_function(self, label):
        self.func = label.rstrip(":")
        self.local_map = {}
        self.next_s = 0
        self.unk_param_order = {}
        self.unk_param_regs = {}
        self.next_param_idx = 0
        self.call_args = []
        self.returned = False
        self.in_function = True
        self.current_func_buffer = []
        self.saved_s_count = 0
        self.emit_out(f"\n# --- function {self.func} ---")
        self.emit_out(f"{self.func}:")

    def end_function(self):
        if not self.in_function:
            return
        self.saved_s_count = self.next_s
        frame_for_s = 4 * self.saved_s_count
        frame_size = self.base_frame + frame_for_s
        self.emit_out(f"  addi $sp, $sp, -{frame_size}")
        self.emit_out(f"  sw   $ra, {frame_size-4}($sp)")
        self.emit_out(f"  sw   $fp, {frame_size-8}($sp)")
        self.emit_out(f"  move $fp, $sp")
        for i in range(self.saved_s_count):
            offset = frame_size - 12 - (4*i)
            self.emit_out(f"  sw   $s{i}, {offset}($sp)")
        for name, idx in list(self.unk_param_order.items()):
            if idx >= 4:
                j = idx - 4
                if j < MAX_EXTRAS_TO_LOAD:
                    assigned = self.unk_param_regs.get(name)
                    if assigned:
                        offset = frame_size + 4*j
                        self.emit_out(f"  lw   {assigned}, {offset}($fp)")
        had_return = False
        for ln in self.current_func_buffer:
            if ln.strip() == f"# {RETURN_MARKER}" or ln.strip() == RETURN_MARKER:
                had_return = True
                for i in range(self.saved_s_count-1, -1, -1):
                    offset = frame_size - 12 - (4*i)
                    self.emit_out(f"  lw   $s{i}, {offset}($sp)")
                self.emit_out(f"  lw   $fp, {frame_size-8}($sp)")
                self.emit_out(f"  lw   $ra, {frame_size-4}($sp)")
                self.emit_out(f"  addi $sp, $sp, {frame_size}")
                self.emit_out(f"  jr   $ra")
            else:
                self.out.append(ln)
        if not had_return:
            for i in range(self.saved_s_count-1, -1, -1):
                offset = frame_size - 12 - (4*i)
                self.emit_out(f"  lw   $s{i}, {offset}($sp)")
            self.emit_out(f"  lw   $fp, {frame_size-8}($sp)")
            self.emit_out(f"  lw   $ra, {frame_size-4}($sp)")
            self.emit_out(f"  addi $sp, $sp, {frame_size}")
            self.emit_out(f"  jr   $ra")
        self.in_function = False
        self.current_func_buffer = []
        self.func = None
        self.returned = False

    def get_s_reg_for_var(self, v):
        v = sanitize_ident(v)
        if v in self.local_map:
            return self.local_map[v]
        reg = f"$s{self.next_s}"
        self.local_map[v] = reg
        self.next_s += 1
        return reg

    def get_reg_for_operand(self, op):
        op = sanitize_ident(str(op))
        if op == "0" or re.fullmatch(r"-?\d+", op):
            return None
        if is_temp(op):
            return reg_for_temp(op)
        if op in self.unk_param_order:
            idx = self.unk_param_order[op]
            if idx < 4:
                return f"$a{idx}"
            else:
                return self.unk_param_regs.get(op)
        if op in self.local_map:
            return self.local_map[op]
        idx = self.next_param_idx
        self.unk_param_order[op] = idx
        self.next_param_idx += 1
        if idx < 4:
            reg = f"$a{idx}"
            return reg
        else:
            reg = self.get_s_reg_for_var(f"arg_{op}")
            self.unk_param_regs[op] = reg
            return reg

    def emit_load_immediate(self, reg, value):
        self.emit(f"  li   {reg}, {value}")

    def translate(self):
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()
            if is_label(line):
                self.start_function(line)
                i += 1
                continue
            if line == "BeginFunc":
                i += 1
                continue
            if line == "EndFunc":
                self.end_function()
                i += 1
                continue
            m = re.match(r"param\s+(.+)", line)
            if m:
                val = m.group(1).strip()
                self.call_args.append(val)
                i += 1
                continue
            m = re.match(r"(?:(\w+)\s*=\s*)?call\s+([A-Za-z_]\w*),\s*(\d+)", line)
            if m:
                target = m.group(1)
                fname = m.group(2)
                num = int(m.group(3))
                for idx in range(min(num,4)):
                    arg = self.call_args[idx] if idx < len(self.call_args) else "0"
                    if re.fullmatch(r"-?\d+", arg):
                        self.emit(f"  li   $a{idx}, {arg}")
                    else:
                        r = self.get_reg_for_operand(arg)
                        if r is None:
                            self.emit(f"  li   $a{idx}, {arg}")
                        else:
                            self.emit(f"  move $a{idx}, {r}")
                if num > 4:
                    extras = self.call_args[4:4+(num-4)]
                    for extra in reversed(extras):
                        if re.fullmatch(r"-?\d+", extra):
                            self.emit(f"  li $t9, {extra}")
                            self.emit(f"  addi $sp, $sp, -4")
                            self.emit(f"  sw $t9, 0($sp)")
                        else:
                            r = self.get_reg_for_operand(extra)
                            self.emit(f"  addi $sp, $sp, -4")
                            self.emit(f"  sw {r}, 0($sp)")
                label_to_call = fname
                if f"{fname}:" not in self.lines:
                    alt = f"func_{fname}:"
                    if alt in self.lines:
                        label_to_call = f"func_{fname}"
                self.emit(f"  jal  {label_to_call}")
                if num > 4:
                    self.emit(f"  addi $sp, $sp, {4*(num-4)}")
                if target:
                    if is_temp(target):
                        trg = reg_for_temp(target)
                    else:
                        trg = self.get_s_reg_for_var(target)
                    self.emit(f"  move {trg}, $v0")
                self.call_args = []
                i += 1
                continue
            m = re.match(r"return\s+(.+)", line)
            if m:
                val = m.group(1).strip()
                if re.fullmatch(r"-?\d+", val):
                    self.emit(f"  li   $v0, {val}")
                else:
                    r = self.get_reg_for_operand(val)
                    if r is None:
                        self.emit(f"  li $v0, {val}")
                    else:
                        self.emit(f"  move $v0, {r}")
                self.emit(f"  # {RETURN_MARKER}")
                self.returned = True
                i += 1
                continue
            m = re.match(r"(\w+)\s*=\s*(.+)", line)
            if m:
                left = m.group(1).strip()
                right = m.group(2).strip()
                mb = re.match(r"(.+)\s*([\+\-\*\/])\s*(.+)", right)
                if mb:
                    L = mb.group(1).strip()
                    op = mb.group(2).strip()
                    R = mb.group(3).strip()
                    rL = None
                    rR = None
                    immL = None
                    immR = None
                    if re.fullmatch(r"-?\d+", L):
                        immL = L
                    else:
                        rL = self.get_reg_for_operand(L)
                    if re.fullmatch(r"-?\d+", R):
                        immR = R
                    else:
                        rR = self.get_reg_for_operand(R)
                    if is_temp(left):
                        trg = reg_for_temp(left)
                    else:
                        trg = self.get_s_reg_for_var(left)
                    if op == "+":
                        if rL and rR:
                            self.emit(f"  add  {trg}, {rL}, {rR}")
                        elif rL and not rR:
                            self.emit(f"  addi {trg}, {rL}, {immR}")
                        elif not rL and rR:
                            self.emit(f"  addi {trg}, {rR}, {immL}")
                        else:
                            self.emit(f"  li {trg}, {immL}")
                            self.emit(f"  addi {trg}, {trg}, {immR}")
                    elif op == "-":
                        if rL and rR:
                            self.emit(f"  sub  {trg}, {rL}, {rR}")
                        elif rL and not rR:
                            self.emit(f"  addi {trg}, {rL}, -{immR}")
                        elif not rL and rR:
                            self.emit(f"  li {trg}, {immL}")
                            self.emit(f"  sub {trg}, {trg}, {rR}")
                        else:
                            self.emit(f"  li {trg}, {int(immL) - int(immR)}")
                    elif op == "*":
                        if rL and rR:
                            self.emit(f"  mul  {trg}, {rL}, {rR}")
                        elif rL and not rR:
                            self.emit(f"  li $t9, {immR}")
                            self.emit(f"  mul {trg}, {rL}, $t9")
                        elif not rL and rR:
                            self.emit(f"  li $t9, {immL}")
                            self.emit(f"  mul {trg}, $t9, {rR}")
                        else:
                            self.emit(f"  li {trg}, {int(immL) * int(immR)}")
                    else:
                        if rL and rR:
                            self.emit(f"  div  {trg}, {rL}, {rR}")
                        else:
                            self.emit(f"  # div with immediates not implemented")
                    i += 1
                    continue
                else:
                    if re.fullmatch(r"-?\d+", right):
                        if is_temp(left):
                            trg = reg_for_temp(left)
                        else:
                            trg = self.get_s_reg_for_var(left)
                        self.emit_load_immediate(trg, right)
                    else:
                        src_reg = self.get_reg_for_operand(right)
                        if src_reg is None:
                            src_reg = "$zero"
                        if is_temp(left):
                            trg = reg_for_temp(left)
                        else:
                            trg = self.get_s_reg_for_var(left)
                        self.emit(f"  move {trg}, {src_reg}")
                    i += 1
                    continue
            self.emit(f"  # unhandled: {line}")
            i += 1
        return "\n".join(self.out)

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
        f.write("# auto-generated MIPS from tac\n")
        f.write(".text\n")
        f.write(".globl main\n")
        f.write(asm)
        f.write("\n")
    print("Wrote", out_path)

if __name__ == "__main__":
    main()
