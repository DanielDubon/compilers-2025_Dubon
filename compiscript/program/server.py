from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
from io import StringIO
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from PrettyErrorListener import PrettyErrorListener
from SemanticListener import SemanticListener
from ast_builder import AstBuilder
from tac_generator import TACGenerator
from dataclasses import is_dataclass, fields # Necesario para dump_ast_to_str
from treeutils import tree_to_pretty_text # Importar para depurar el parse tree

app = Flask(__name__)
CORS(app)

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

@app.route('/compile', methods=['POST'])
def compile_code():
    data = request.get_json()
    code = data.get('code', '')

    # Capturar stderr para errores del compilador
    old_stderr = sys.stderr
    redirected_stderr = StringIO()
    sys.stderr = redirected_stderr

    output_tac = ""
    compiler_errors = ""

    try:
        # 1. Lexing y Parsing
        input_stream = InputStream(code + '\n')
        lexer = CompiscriptLexer(input_stream)
        
        # Capturar errores sintácticos
        parser_error_listener = PrettyErrorListener(code.splitlines())
        lexer.removeErrorListeners()
        lexer.addErrorListener(parser_error_listener)

        stream = CommonTokenStream(lexer)
        parser = CompiscriptParser(stream)
        parser.removeErrorListeners()
        parser.addErrorListener(parser_error_listener)

        tree = parser.program()

        # DEBUG: Imprimir el Parse Tree para verificar su contenido
        print("\n--- Parse Tree Generado ---")
        print(tree_to_pretty_text(tree, parser.ruleNames))
        print("---------------------------\n")

        if parser_error_listener.errors:
            compiler_errors = redirected_stderr.getvalue()
            return jsonify({'output': '', 'errors': compiler_errors})

        # 2. Análisis Semántico
        walker = ParseTreeWalker()
        semantic_listener = SemanticListener(code.splitlines())
        walker.walk(semantic_listener, tree)

        if semantic_listener.errors:
            compiler_errors = redirected_stderr.getvalue()
            return jsonify({'output': '', 'errors': compiler_errors})

        # 3. Construcción del AST
        ast_builder = AstBuilder()
        ast = ast_builder.visitProgram(tree)

        # DEBUG: Imprimir el AST para verificar su contenido
        print("\n--- AST Generado ---")
        print(dump_ast_to_str(ast))
        print("--------------------\n")

        # 4. Generación de TAC
        tac_generator = TACGenerator(semantic_listener.symbtab)
        tac_code = tac_generator.generate(ast)
        
        # DEBUG: Imprimir el contenido de tac_code
        print(f"\n--- TAC Generado (longitud: {len(tac_code)}) ---")
        for i, instr in enumerate(tac_code[:10]): # Imprimir las primeras 10 instrucciones
            print(f"  {i}: {instr}")
        if len(tac_code) > 10:
            print("  ...")
        print("------------------------------------\n")

        output_tac = "\n".join(map(str, tac_code))

    except Exception as e:
        compiler_errors = redirected_stderr.getvalue() + str(e)
    finally:
        sys.stderr = old_stderr # Restaurar stderr

    return jsonify({'output': output_tac, 'errors': compiler_errors})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)