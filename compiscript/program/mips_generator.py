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
        self.lines = [l.rstrip() for l in tac_lines if l.strip() != ""]
        self.out_asm = []
        self.main_buffer = []
        self.func_name = None
        
        # Per-function state
        self.local_map = {}
        self.spill_map = {}
        self.next_spill_offset = 4 # Start after $ra
        self.next_s_reg = 0
        self.call_args = []
        self.in_function = False
        self.current_func_buffer = []

    def emit(self, line=""):
        if self.in_function:
            self.current_func_buffer.append(line)
        else:
            self.main_buffer.append(line)

    def emit_out(self, line=""):
        self.out_asm.append(line)

    def start_function(self, label):
        self.func_name = "user_main" if label.startswith("main:") else label.rstrip(":")
        self.local_map = {}
        self.spill_map = {}
        self.next_spill_offset = 4 # Start after $ra
        self.next_s_reg = 0
        self.call_args = []
        self.in_function = True
        self.current_func_buffer = []

    def end_function(self):
        if not self.in_function:
            return

        # Frame size calculation
        saved_s_regs = self.next_s_reg
        frame_size = 4 + (4 * saved_s_regs) + self.next_spill_offset

        # Prologue
        prologue = [
            f"\n# --- function {self.func_name} ---",
            f"{self.func_name}:",
            f"  addiu $sp, $sp, -{frame_size}",
            f"  sw $ra, {frame_size - 4}($sp)",
        ]
        for i in range(saved_s_regs):
            prologue.append(f"  sw $s{i}, {frame_size - 8 - (4*i)}($sp)")
        
        # Epilogue
        epilogue = [f".epilogue_{self.func_name}:"]
        for i in range(saved_s_regs - 1, -1, -1):
            epilogue.append(f"  lw $s{i}, {frame_size - 8 - (4*i)}($sp)")
        epilogue.extend([
            f"  lw $ra, {frame_size - 4}($sp)",
            f"  addiu $sp, $sp, {frame_size}",
            f"  jr $ra"
        ])

        # Insert prologue at the beginning and epilogue at the end
        final_func_code = prologue + self.current_func_buffer
        final_func_code.extend(epilogue)

        self.out_asm.extend(final_func_code)
        self.in_function = False

    def get_op_location(self, op):
        op = sanitize_ident(op)
        if op in self.local_map:
            return self.local_map[op]

        if is_temp(op):
            # High-numbered temps are spilled
            m = re.fullmatch(r"t(\d+)", op)
            idx = int(m.group(1))
            if idx < 8:
                reg = f"$t{idx}"
                self.local_map[op] = ('reg', reg)
                return ('reg', reg)
        
        # Spill other temps and all user variables
        if self.next_s_reg < 8:
            reg = f"$s{self.next_s_reg}"
            self.next_s_reg += 1
            self.local_map[op] = ('reg', reg)
            return ('reg', reg)
        else:
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
        else: # spill
            self.emit(f"  lw {dest_reg}, -{loc}($sp)")

    def store_op(self, src_reg, dest_op):
        dest_op = sanitize_ident(dest_op)
        kind, loc = self.get_op_location(dest_op)
        if kind == 'reg':
            if loc != src_reg:
                self.emit(f"  move {loc}, {src_reg}")
        else: # spill
            self.emit(f"  sw {src_reg}, -{loc}($sp)")

    def translate(self):
        i = 0
        while i < len(self.lines):
            line = self.lines[i].strip()

            if is_label(line):
                if i + 1 < len(self.lines) and self.lines[i+1].strip() == 'BeginFunc':
                    self.end_function()
                    self.start_function(line)
                    i += 2
                    continue
                else:
                    self.emit(line)
                    i += 1
                    continue

            if line == "EndFunc":
                self.end_function()
                i += 1
                continue
            
            m = re.match(r"goto\s+([A-Za-z_0-9]+)", line)
            if m:
                self.emit(f"  j {m.group(1)}")
                i += 1
                continue

            m = re.match(r"if_false\s+(.+)\s+goto\s+(.+)", line)
            if m:
                op = sanitize_ident(m.group(1))
                label = m.group(2)
                kind, loc = self.get_op_location(op)
                if kind == 'reg':
                    self.emit(f"  beq {loc}, $zero, {label}")
                else: # spill
                    self.load_op(op, "$t8")
                    self.emit(f"  beq $t8, $zero, {label}")
                i += 1
                continue

            m = re.match(r"param\s+(.+)", line)
            if m:
                self.call_args.append(m.group(1).strip())
                i += 1
                continue

            m = re.match(r"(?:([\w\d]+)\s*=\s*)?call\s+([\w\d]+),\s*(\d+)", line)
            if m:
                dest, fname, num_args = m.groups()
                fname = "user_main" if fname == "main" else fname
                
                for j in range(min(int(num_args), 4)):
                    self.load_op(self.call_args[j], f"$a{j}")
                
                self.emit(f"  jal {fname}")
                self.call_args = []
                if dest:
                    self.store_op("$v0", dest)
                i += 1
                continue

            m = re.match(r"return(?:\s+(.+))?", line)
            if m:
                val = m.group(1)
                if val:
                    self.load_op(val, "$v0")
                self.emit(f"  j .epilogue_{self.func_name}")
                i += 1
                continue

            m = re.match(r"([\w\d]+)\s*=\s*(.+)", line)
            if m:
                left, right = m.groups()
                
                mb = re.match(r"(.+)\s*([<>]=?|==|!=|[+\-*\/])\s*(.+)", right)
                if mb:
                    L, op, R = mb.groups()
                    self.load_op(L, "$t8")
                    self.load_op(R, "$t9")
                    
                    op_map = {
                        '+': 'add', '-': 'sub', '*': 'mul', '/': 'div',
                        '<': 'slt', '>': 'sgt', '<=': 'sle', '>=': 'sge',
                        '==': 'seq', '!=': 'sne'
                    }
                    if op in op_map:
                        self.emit(f"  {op_map[op]} $t8, $t8, $t9")
                    
                    if op == '/':
                        self.emit("  mflo $t8")

                    self.store_op("$t8", left)
                else: # Simple assignment: left = right
                    right_op = sanitize_ident(right)
                    dest_op = sanitize_ident(left)
                    dest_kind, dest_loc = self.get_op_location(dest_op)

                    # Handle right operand
                    if re.fullmatch(r"-?\d+", right_op): # RHS is a literal
                        if dest_kind == 'reg':
                            self.emit(f"  li {dest_loc}, {right_op}")
                        else: # dest is spill
                            self.emit(f"  li $t8, {right_op}")
                            self.store_op("$t8", dest_op)
                    else: # RHS is a variable
                        right_kind, right_loc = self.get_op_location(right_op)
                        if dest_kind == 'reg':
                            if right_kind == 'reg':
                                if dest_loc != right_loc:
                                    self.emit(f"  move {dest_loc}, {right_loc}")
                            else: # right is spill
                                self.load_op(right_op, dest_loc)
                        else: # dest is spill
                            if right_kind == 'reg':
                                self.store_op(right_loc, dest_op)
                            else: # both are spill
                                self.load_op(right_op, "$t8")
                                self.store_op("$t8", dest_op)
                i += 1
                continue

            self.emit(f"  # unhandled: {line}")
            i += 1
        
        self.end_function()

        has_user_main = any(line.strip() == "user_main:" for line in self.out_asm)

        final_code = [
            "main:",
            "  addiu $sp, $sp, -256",
            "  sw $ra, 252($sp)",
        ]
        final_code.extend(self.main_buffer)

        if has_user_main:
            final_code.append("  jal user_main")

        final_code.extend([
            "  lw $ra, 252($sp)",
            "  addiu $sp, $sp, 256",
            "  li $v0, 10",
            "  syscall",
            ""
        ])
        final_code.extend(self.out_asm)

        # Add runtime helpers
        final_code.append("\n# --- Runtime Helpers ---")
        final_code.append("print:")
        final_code.append("  li $v0, 1      # syscall for print_int")
        final_code.append("  syscall")
        final_code.append("  li $v0, 4      # syscall for print_string")
        final_code.append("  la $a0, newline")
        final_code.append("  syscall")
        final_code.append("  jr $ra")

        # Assemble the full file
        full_asm = [
            "# auto-generated MIPS from tac",
            ".data",
            "newline: .asciiz \"\\n\"",
            "\n.text",
            ".globl main",
        ]
        full_asm.extend(final_code)
        
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
        f.write(asm)
        f.write("\n")
    print("Wrote", out_path)