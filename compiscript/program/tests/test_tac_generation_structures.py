from tests.conftest import run_compiler, has_labels

def test_if_else_generates_labels_and_assigns():
    src = """\
let cond: boolean = true;
let x: integer = 0;
if (cond) {
  x = x + 1;
} else {
  x = x + 2;
}
"""
    out, err, tac, code = run_compiler(src)
    
    assert has_labels(tac), f"No se detectaron etiquetas de control (L0/L1/Label) en TAC:\n{tac}"
    assert " + " in tac, f"No se detectó suma en el TAC.\n{tac}"

def test_while_generates_label_and_conditional_jump():
    src = """\
let sum: integer = 0;
let i: integer = 0;
while (i < 3) {
  sum = sum + 1;
  i = i + 1;
}
"""
    out, err, tac, code = run_compiler(src)
    assert has_labels(tac), f"Se esperaban etiquetas en el while.\n{tac}"
    assert "<" in tac, f"No se encontró comparación '<' en TAC.\n{tac}"

def test_call_and_param_generates_temp_result():
    src = """\
function id(x: integer): integer { return x; }
let a: integer = 7;
let b: integer = id(a);
"""
    out, err, tac, code = run_compiler(src)
    # La llamada debe producir un temp de retorno
    assert "id" in tac.lower(), f"No se encontró la llamada a 'id' en TAC:\n{tac}"
    assert "t" in tac, f"No se encontraron temporales en el resultado de la llamada.\n{tac}"
