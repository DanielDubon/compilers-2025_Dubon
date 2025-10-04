from tests.conftest import run_compiler, temp_set

def test_linear_chain_reuses_single_temp():
    
    src = "let r: integer = 1 + 2 + 3 + 4 + 5;"
    out, err, tac, code = run_compiler(src)
    temps = temp_set(tac)
    
    
    assert len(temps) == 1, f"Se esperaban 1 temporal, se vieron: {temps}\nTAC:\n{tac}"

def test_parenthesized_uses_at_most_two_temps():
    
    src = "let r: integer = (1 + 2) + (3 + 4);"
    out, err, tac, code = run_compiler(src)
    temps = temp_set(tac)
   
    assert 1 <= len(temps) <= 2, f"Se esperaban 1..2 temporales, se vieron: {temps}\nTAC:\n{tac}"

def test_reuse_across_statements():
    
    src = """\
let a: integer = 2 + 3 * 4;
let b: integer = 10 - a / 2;
"""
    out, err, tac, code = run_compiler(src)
    temps = temp_set(tac)
    assert len(temps) == 1, f"Se esperaba reutilizar el mismo temporal en ambas expresiones. Vistos: {temps}\nTAC:\n{tac}"
