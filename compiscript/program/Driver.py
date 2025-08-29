import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from PrettyErrorListener import PrettyErrorListener
from treeutils import tree_to_pretty_text, tree_to_dot
from SemanticListener import SemanticListener
from antlr4 import ParseTreeWalker
from ast_builder import AstBuilder
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
    if len(argv) < 2:
        print("Uso: python3 Driver.py <archivo.cps> [--ast-dump] [--ast-dot]")
        return

    want_ast_dump = ("--ast-dump" in argv)
    want_ast_dot  = ("--ast-dot" in argv)

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
    with open("parse_tree.txt", "w", encoding="utf-8") as f:
        f.write(pretty)

    dot = tree_to_dot(tree, parser)
    with open("parse_tree.dot", "w", encoding="utf-8") as f:
        f.write(dot)

    
    walker = ParseTreeWalker()
    sem = SemanticListener(source_lines)
    walker.walk(sem, tree)

    
    if sem.errors:
        print(f"{len(sem.errors)} error(es) semantico(s) encontrados.")
    else:
        print("Chequeos semanticos OK.")

   
    builder = AstBuilder()
    ast = builder.visit(tree)

    
    if want_ast_dump or (not want_ast_dot and not want_ast_dump):
        txt = dump_ast_to_str(ast)
        with open("ast.txt", "w", encoding="utf-8") as f:
            f.write(txt)

    if want_ast_dot or (not want_ast_dot and not want_ast_dump):
        astdot = ast_to_dot(ast)
        with open("ast.dot", "w", encoding="utf-8") as f:
            f.write(astdot)

   
    print("Analisis completado.")
    print("Parse tree: parse_tree.txt, parse_tree.dot  (usa: dot -Tpng parse_tree.dot -o parse_tree.png)")
    print("AST:        ast.txt, ast.dot                (usa: dot -Tpng ast.dot -o ast.png)")

if __name__ == "__main__":
    main(sys.argv)
