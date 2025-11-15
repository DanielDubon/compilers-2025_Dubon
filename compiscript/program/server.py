from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from pathlib import Path
import subprocess, re, traceback, time
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
from mips_generator import MIPSGen

PROG_DIR = Path(__file__).resolve().parent
FRONTEND_PUBLIC = PROG_DIR / "my-ide-app" / "public"
FRONTEND_STATIC = FRONTEND_PUBLIC / "static"

app = Flask(__name__, static_folder=str(FRONTEND_PUBLIC), static_url_path='/ide/static')
CORS(app)  # permitir llamadas desde el IDE en dev

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

        semantic_listener.symbtab.assign_memory_addresses()  # solo globales (scope 0)
        semantic_listener.symbtab.assign_function_labels()
        print(semantic_listener.symbtab.dump())

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

def compile_code(source_code: str, output_format: str = "all"):
    """
    Compila el código fuente usando Driver.py en el directorio PROG_DIR.
    Retorna un objeto con atributos: success, tac, mips, ast, stdout, stderr, errors, warnings, compilation_time
    """
    class Result:
        success = False
        tac = ""
        mips = ""
        ast = ""
        stdout = ""
        stderr = ""
        errors = []
        warnings = []
        compilation_time = 0.0

    res = Result()
    import time
    start = time.time()

    try:
        # escribir archivo temporal
        tmp_file = PROG_DIR / "tmp_compile.cps"
        tmp_file.write_text(source_code)

        # verificar Driver.py
        if not (PROG_DIR / "Driver.py").exists():
            res.stderr = f"Driver.py not found at {PROG_DIR / 'Driver.py'}"
            res.errors = [res.stderr]
            return res

        # construir y ejecutar Driver.py con los flags correctos
        driver_cmd = [sys.executable, str(PROG_DIR / "Driver.py"), tmp_file.name]
        # Driver supports --tac, --ast-dump and --ast-dot (not --mips)
        if output_format in ("all", "tac", "mips"):
            driver_cmd.append("--tac")
        if output_format in ("all", "ast"):
            driver_cmd.append("--ast-dump")
        # always generate tac when mips requested

        print("[server] Running Driver:", " ".join(driver_cmd))
        cp = subprocess.run(driver_cmd, cwd=str(PROG_DIR), capture_output=True, text=True, timeout=60)

        res.stdout = cp.stdout or ""
        res.stderr = cp.stderr or ""

        # leer TAC si fue generado
        tac_file = PROG_DIR / "tac.txt"
        if tac_file.exists():
            res.tac = tac_file.read_text()

        # Si pidieron MIPS, invocar el mips_generator explícitamente
        if output_format in ("all", "mips"):
            # ensure tac exists
            if tac_file.exists():
                mips_cmd = [sys.executable, str(PROG_DIR / "mips_generator.py"), str(tac_file.name)]
                print("[server] Running MIPS generator:", " ".join(mips_cmd))
                mcp = subprocess.run(mips_cmd, cwd=str(PROG_DIR), capture_output=True, text=True, timeout=60)
                # append any messages
                if mcp.stdout:
                    res.stdout += "\n" + mcp.stdout
                if mcp.stderr:
                    res.stderr += "\n" + mcp.stderr

        # leer mips y ast si existen
        mips_file = PROG_DIR / "out.s"
        if mips_file.exists():
            try:
                res.mips = mips_file.read_text()
            except Exception:
                res.mips = ""

        ast_file = PROG_DIR / "ast.txt"
        if ast_file.exists():
            res.ast = ast_file.read_text()

        res.success = (cp.returncode == 0)
        if not res.success and not res.errors:
            # intentar extraer mensaje útil
            err_msg = res.stderr.strip() or res.stdout.strip() or f"Driver exited with code {cp.returncode}"
            res.errors = [err_msg]

    except subprocess.TimeoutExpired:
        res.stderr = "Compilación excedió el tiempo límite"
        res.errors = [res.stderr]
    except Exception as e:
        import traceback
        res.stderr = traceback.format_exc()
        res.errors = [str(e)]

    finally:
        res.compilation_time = time.time() - start

    return res

def _normalize_result(result):
    """Normaliza el objeto de resultado para devolver un dict consistente."""
    # Si ya es dict, devolver con claves esperadas
    if isinstance(result, dict):
        return {
            "success": result.get("success", False),
            "tac": result.get("tac", "") or "",
            "mips": result.get("mips", "") or "",
            "ast": result.get("ast", "") or "",
            "stdout": result.get("stdout", "") or "",
            "stderr": result.get("stderr", "") or "",
            "errors": result.get("errors", []) or [],
            "warnings": result.get("warnings", []) or [],
            "compilation_time": float(result.get("compilation_time", 0) or 0)
        }
    # Si es el objeto CompilationResult u otro con atributos
    return {
        "success": getattr(result, "success", False),
        "tac": getattr(result, "tac", "") or "",
        "mips": getattr(result, "mips", "") or "",
        "ast": getattr(result, "ast", "") or "",
        "stdout": getattr(result, "stdout", "") or "",
        "stderr": getattr(result, "stderr", "") or "",
        "errors": getattr(result, "errors", []) or [],
        "warnings": getattr(result, "warnings", []) or [],
        "compilation_time": float(getattr(result, "compilation_time", 0) or 0)
    }

@app.route('/ide/compile', methods=['POST', 'GET'])
def ide_compile():
    """POST: compila; GET: sirve el IDE (index.html)"""
    if request.method == 'GET':
        # servir index (mantén tu lógica existente)
        static_index = FRONTEND_STATIC / "index.html"
        public_index = FRONTEND_PUBLIC / "index.html"
        if static_index.exists():
            return send_from_directory(str(FRONTEND_STATIC), "index.html")
        if public_index.exists():
            return send_from_directory(str(FRONTEND_PUBLIC), "index.html")
        return ("IDE static not found. Coloca index.html en my-ide-app/public o my-ide-app/public/static", 404)

    # POST -> compilación
    try:
        data = request.get_json() or {}
        code = data.get('code', '')
        fmt = data.get('format', 'all')
        if not code:
            return jsonify({"success": False, "errors": ["No se recibió 'code' en el body"]}), 400

        raw = compile_code(code, fmt)
        resp = _normalize_result(raw)
        return jsonify(resp)
    except Exception as e:
        return jsonify({"success": False, "errors": [str(e)], "stderr": traceback.format_exc()}), 500

# servir recursos estáticos bajo /ide/static/...
@app.route('/ide/static/<path:filename>')
def serve_ide_static(filename):
    f1 = FRONTEND_STATIC / filename
    f2 = FRONTEND_PUBLIC / filename
    if f1.exists():
        return send_from_directory(str(FRONTEND_STATIC), filename)
    if f2.exists():
        return send_from_directory(str(FRONTEND_PUBLIC), filename)
    return ("Not found", 404)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)