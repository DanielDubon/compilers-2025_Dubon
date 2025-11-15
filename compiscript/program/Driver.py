import sys
import os
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from PrettyErrorListener import PrettyErrorListener
from treeutils import tree_to_pretty_text, tree_to_dot
from SemanticListener import SemanticListener
from antlr4 import ParseTreeWalker
from ast_builder import AstBuilder
from tac_generator import TACGenerator
from dataclasses import is_dataclass, fields

def dump_ast_to_str(node, indent=0):
    pad = "  " * indent
    out = []
    if not is_dataclass(node):
        return f"{pad}{repr(node)}"
    cls = node.__class__.__name__
    out.append(f"{pad}{cls}")
    for f in fields(node):
        if f.name in ("line", "col"):  
            continue
        val = getattr(node, f.name)
        if is_dataclass(val):
            out.append(f"{pad}  .{f.name}:")
            out.append(dump_ast_to_str(val, indent + 2))
        elif isinstance(val, list):
            out.append(f"{pad}  .{f.name}:")
            for it in val:
                if is_dataclass(it):
                    out.append(dump_ast_to_str(it, indent + 2))
                else:
                    out.append(f"{pad}    {it}")
        else:
            out.append(f"{pad}  {f.name}={val}")
    return "\n".join(out)

def ast_to_dot(root):
    lines = ["digraph AST {", '  node [shape=box, fontname="Arial"];']
    counter = 0

    def new_id():
        nonlocal counter
        nid = f"n{counter}"
        counter += 1
        return nid

    def label_of(node):
        lbl = node.__class__.__name__
        for k in ("name", "op", "kind", "class_name"):
            if hasattr(node, k):
                v = getattr(node, k)
                if v is not None:
                    lbl += f"\\n{k}={v}"
        return lbl

    def is_node(x):
        return is_dataclass(x)

    def walk(node):
        nid = new_id()
        lines.append(f'  {nid} [label="{label_of(node)}"];')
        for f in fields(node):
            if f.name in ("line", "col"):
                continue
            val = getattr(node, f.name)
            def link(child):
                if child is None or not is_node(child):
                    return
                cid = walk(child)
                lines.append(f'  {nid} -> {cid} [label="{f.name}"];')
            if isinstance(val, list):
                for ch in val:
                    link(ch)
            else:
                link(val)
        return nid

    walk(root)
    lines.append("}")
    return "\n".join(lines)


def main(argv):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if len(argv) < 2:
        print("Uso: python3 Driver.py <archivo.cps> [--ast-dump] [--ast-dot] [--tac] [--mips]")
        return

    want_ast_dump = ("--ast-dump" in argv)
    want_ast_dot  = ("--ast-dot" in argv)
    want_tac = ("--tac" in argv)
    want_mips = ("--mips" in argv)

    with open(argv[1], encoding="utf-8") as f:
        source_lines = f.readlines()

    input_stream = FileStream(argv[1], encoding="utf-8")
    lexer = CompiscriptLexer(input_stream)
    err = PrettyErrorListener(source_lines)
    lexer.removeErrorListeners()
    lexer.addErrorListener(err)

    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(err)

    tree = parser.program()

    
    if getattr(err, "errors", []):
        print("No se genero el arbol por errores sintacticos...")
        return

    
    pretty = tree_to_pretty_text(tree, parser.ruleNames)
    with open(os.path.join(script_dir, "parse_tree.txt"), "w", encoding="utf-8") as f:
        f.write(pretty)

    dot = tree_to_dot(tree, parser)
    with open(os.path.join(script_dir, "parse_tree.dot"), "w", encoding="utf-8") as f:
        f.write(dot)

    
    walker = ParseTreeWalker()
    sem = SemanticListener(source_lines)
    walker.walk(sem, tree)

    if sem.errors:
        print(f"{len(sem.errors)} error(es) semantico(s) encontrados.")
        print("Analisis completado.")
        return
    else:
        print("Chequeos semanticos OK.")
        if hasattr(sem, "symbtab"):
            print(sem.symbtab.dump())

    builder = AstBuilder()
    ast = builder.visit(tree)

    if want_ast_dump or (not want_ast_dot and not want_ast_dump):
        txt = dump_ast_to_str(ast)
        with open(os.path.join(script_dir, "ast.txt"), "w", encoding="utf-8") as f:
            f.write(txt)

    if want_ast_dot or (not want_ast_dot and not want_ast_dump):
        astdot = ast_to_dot(ast)
        with open(os.path.join(script_dir, "ast.dot"), "w", encoding="utf-8") as f:
            f.write(astdot)

    if want_tac:
        print("Generando codigo intermedio (TAC)...")
        # Asignar direcciones de memoria y etiquetas antes de generar TAC
        sem.symbtab.assign_memory_addresses()
        sem.symbtab.assign_function_labels()
        
        tac_gen = TACGenerator(sem.symbtab)
        tac_code = tac_gen.generate(ast)
        tac_path = os.path.join(script_dir, "tac.txt")
        with open(tac_path, "w", encoding="utf-8") as f:
            f.write("\n".join(map(str, tac_code)))
        print(f"TAC guardado en: {tac_path}")
        
        # Mostrar información adicional de la tabla de símbolos
        print("\n--- Información adicional para generación de código assembler ---")
        print(sem.symbtab.dump())
        
        # Generar MIPS si se solicita
        if want_mips:
            print("\nGenerando codigo MIPS...")
            from mips_generator import MIPSGen
            # Convert TAC objects to strings for MIPSGen
            tac_strings = [str(t) for t in tac_code]
            mips_gen = MIPSGen(tac_strings)
            mips_asm = mips_gen.translate()
            mips_path = os.path.join(script_dir, "out.s")
            with open(mips_path, "w", encoding="utf-8") as f:
                f.write(mips_asm)
                f.write("\n")
            print(f"MIPS guardado en: {mips_path}")
    elif want_mips:
        # Si se pide MIPS sin TAC, generar TAC primero
        print("Generando codigo MIPS (requiere TAC)...")
        sem.symbtab.assign_memory_addresses()
        sem.symbtab.assign_function_labels()
        
        tac_gen = TACGenerator(sem.symbtab)
        tac_code = tac_gen.generate(ast)
        tac_path = os.path.join(script_dir, "tac.txt")
        with open(tac_path, "w", encoding="utf-8") as f:
            f.write("\n".join(map(str, tac_code)))
        
        print("Generando codigo MIPS...")
        from mips_generator import MIPSGen
        # Convert TAC objects to strings for MIPSGen
        tac_strings = [str(t) for t in tac_code]
        mips_gen = MIPSGen(tac_strings)
        mips_asm = mips_gen.translate()
        mips_path = os.path.join(script_dir, "out.s")
        with open(mips_path, "w", encoding="utf-8") as f:
            f.write(mips_asm)
            f.write("\n")
        print(f"MIPS guardado en: {mips_path}")

    # Generar imágenes PNG automáticamente
    print("Generando imágenes PNG...")
    try:
        import subprocess
        
        # Generar parse_tree.png
        parse_tree_dot = os.path.join(script_dir, 'parse_tree.dot')
        parse_tree_png = os.path.join(script_dir, 'parse_tree.png')
        result = subprocess.run(['dot', '-Tpng', parse_tree_dot, '-o', parse_tree_png], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ Parse tree PNG generado: {parse_tree_png}")
        else:
            print(f"⚠ Error generando parse_tree.png: {result.stderr}")
        
        # Generar ast.png
        ast_dot = os.path.join(script_dir, 'ast.dot')
        ast_png = os.path.join(script_dir, 'ast.png')
        result = subprocess.run(['dot', '-Tpng', ast_dot, '-o', ast_png], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✓ AST PNG generado: {ast_png}")
        else:
            print(f"⚠ Error generando ast.png: {result.stderr}")
            
    except FileNotFoundError:
        print("⚠ Graphviz (dot) no encontrado. Instala con: sudo apt-get install graphviz")
    except Exception as e:
        print(f"⚠ Error generando imágenes PNG: {e}")

    print("Analisis completado.")
    print(f"Parse tree: {os.path.join(script_dir, 'parse_tree.txt')}, {os.path.join(script_dir, 'parse_tree.dot')}, {os.path.join(script_dir, 'parse_tree.png')}")
    print(f"AST:        {os.path.join(script_dir, 'ast.txt')}, {os.path.join(script_dir, 'ast.dot')}, {os.path.join(script_dir, 'ast.png')}")

if __name__ == "__main__":
    main(sys.argv)
