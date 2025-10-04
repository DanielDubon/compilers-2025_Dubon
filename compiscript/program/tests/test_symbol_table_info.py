import re
from .conftest import run_compiler

def test_symbol_table_has_memory_addresses_and_function_labels():
    src = """\
let a: integer = 1;
function foo(x: integer): integer { return x; }
let b: integer = foo(a);
"""
    out, err, tac, code = run_compiler(src)

    
    assert "Información adicional para generación de código assembler" in out
    assert "addr=mem_" in out, f"No se encontraron direcciones de memoria en la tabla.\n{out}"

    
    has_label_line = re.search(r"\bfoo\s*\([^)]*\)\s*->\s*\w+,\s*label\s*=\s*\w+", out)
    assert has_label_line, f"No se encontró label para foo() en la tabla extendida.\n{out}"
