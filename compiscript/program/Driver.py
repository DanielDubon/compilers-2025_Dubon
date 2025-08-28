import sys
from antlr4 import *
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from PrettyErrorListener import PrettyErrorListener
from treeutils import tree_to_pretty_text, tree_to_dot
from SemanticListener import SemanticListener
from antlr4 import ParseTreeWalker

def main(argv):
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
        print("Analisis completado sin errores.")
        print("Arbol guardado en: parse_tree.txt y parse_tree.dot")
        print("dot -Tpng parse_tree.dot -o parse_tree.png")

if __name__ == "__main__":
    main(sys.argv)
