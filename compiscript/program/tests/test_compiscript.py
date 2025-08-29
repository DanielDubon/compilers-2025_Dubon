import os, sys, unittest
from antlr4 import InputStream, CommonTokenStream, ParseTreeWalker
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from CompiscriptLexer import CompiscriptLexer
from CompiscriptParser import CompiscriptParser
from PrettyErrorListener import PrettyErrorListener
from SemanticListener import SemanticListener
from ast_builder import AstBuilder
from dataclasses import is_dataclass

def analyze(source: str):
    inp = InputStream(source)
    lexer = CompiscriptLexer(inp)
    src_lines = source.splitlines(True)
    el = PrettyErrorListener(src_lines)
    lexer.removeErrorListeners()
    lexer.addErrorListener(el)
    stream = CommonTokenStream(lexer)
    parser = CompiscriptParser(stream)
    parser.removeErrorListeners()
    parser.addErrorListener(el)
    tree = parser.program()
    if getattr(el, "errors", []):
        return {"syntax_errors": el.errors, "sem_errors": None, "ast": None, "tree": tree}
    walker = ParseTreeWalker()
    sem = SemanticListener(src_lines)
    walker.walk(sem, tree)
    builder = AstBuilder()
    ast = builder.visit(tree)
    return {"syntax_errors": [], "sem_errors": sem.errors, "ast": ast, "tree": tree}

def assert_ok(t, res):
    t.assertEqual(res["syntax_errors"], [])
    t.assertEqual(res["sem_errors"], [])
    t.assertTrue(is_dataclass(res["ast"]))

def assert_has_error(t, res, needle):
    t.assertEqual(res["syntax_errors"], [])
    errs = [m for (_, _, m) in res["sem_errors"]]
    t.assertTrue(any(needle in m for m in errs), msg=f"No se encontró: {needle}\nErrores:\n" + "\n".join(errs))

class TestCompiscript(unittest.TestCase):
    def test_arithmetic_ok(self):
        src = "let a: integer = 1 + 2 * 3; let b: integer = a - 4; let c = a / 2;"
        res = analyze(src)
        assert_ok(self, res)

    def test_arithmetic_type_error(self):
        src = 'let s: string = "x"; let y = s - 1;'
        res = analyze(src)
        assert_has_error(self, res, "Operandos de '-' deben ser numericos.")

    def test_logical_ok(self):
        src = "let a: boolean = true && (false || !false);"
        res = analyze(src)
        assert_ok(self, res)

    def test_logical_error(self):
        src = "let a = 1 && true;"
        res = analyze(src)
        assert_has_error(self, res, "Operandos de '&&' deben ser booleanos.")

    def test_comparison_ok(self):
        src = 'let a: boolean = 1 < 2; let b: boolean = 1 == 2; let c: boolean = "x" == "y";'
        res = analyze(src)
        assert_ok(self, res)

    def test_comparison_error(self):
        src = 'let a = "x" < 2;'
        res = analyze(src)
        assert_has_error(self, res, "Operandos de '<' deben ser numericos.")

    def test_assignment_type_mismatch(self):
        src = 'let x: integer = "a";'
        res = analyze(src)
        assert_has_error(self, res, "Tipo incompatible en inicializacion de variable 'x'")

    def test_const_requires_init(self):
        src = 'const K: integer;'
        res = analyze(src)
        assert_has_error(self, res, "La constante 'K' debe inicializarse.")

    def test_const_reassign(self):
        src = 'const K: integer = 1; K = 2;'
        res = analyze(src)
        assert_has_error(self, res, "No se puede reasignar a constante 'K'.")

    def test_array_ok(self):
        src = 'let a: integer[] = [1,2,3]; let x = a[0];'
        res = analyze(src)
        assert_ok(self, res)

    def test_array_inconsistent(self):
        src = 'let a = [1,"x"];'
        res = analyze(src)
        assert_has_error(self, res, "Elementos del arreglo con tipos inconsistentes.")

    def test_undeclared_var(self):
        src = 'print(y);'
        res = analyze(src)
        assert_has_error(self, res, "Uso de variable no declarada: 'y'.")

    def test_redeclaration_same_scope(self):
        src = 'let x: integer = 1; let x: integer = 2;'
        res = analyze(src)
        assert_has_error(self, res, "Redeclaracion de 'x' en el mismo ambito.")

    def test_block_scoping(self):
        src = 'let x: integer = 1; { let x: integer = 2; }'
        res = analyze(src)
        assert_ok(self, res)

    def test_func_call_ok(self):
        src = 'function sum(a: integer, b: integer): integer { return a + b; } let z: integer = sum(1,2);'
        res = analyze(src)
        assert_ok(self, res)

    def test_func_call_bad_arity(self):
        src = 'function sum(a: integer, b: integer): integer { return a + b; } let z = sum(1);'
        res = analyze(src)
        assert_has_error(self, res, "Llamada a 'sum' con 1 argumento(s), se esperaban 2.")

    def test_func_call_bad_type(self):
        src = 'function sum(a: integer, b: integer): integer { return a + b; } let z = sum(1,"x");'
        res = analyze(src)
        assert_has_error(self, res, "Argumento 2 de 'sum' incompatible")

    def test_return_type_mismatch(self):
        src = 'function f(): integer { return "x"; }'
        res = analyze(src)
        assert_has_error(self, res, "Tipo de retorno incompatible")

    def test_return_missing_path(self):
        src = 'function f(x: integer): integer { if (x > 0) { return 1; } }'
        res = analyze(src)
        assert_has_error(self, res, "debe retornar integer en todos los caminos")

    def test_recursion_ok(self):
        src = 'function fact(n: integer): integer { if (n <= 1) { return 1; } return n * fact(n - 1); }'
        res = analyze(src)
        assert_ok(self, res)

    def test_nested_functions_closure_ok(self):
        src = 'function outer(): integer { var x: integer = 1; function inner(): integer { return x; } return inner(); }'
        res = analyze(src)
        assert_ok(self, res)

    def test_duplicate_function(self):
        src = 'function f(): integer { return 1; } function f(): integer { return 2; }'
        res = analyze(src)
        assert_has_error(self, res, "Funcion 'f' redeclarada.")

    def test_if_cond_boolean_error(self):
        src = 'if (1) { }'
        res = analyze(src)
        assert_has_error(self, res, "La condicion de if debe ser boolean.")

    def test_while_cond_boolean_error(self):
        src = 'while ("x") { }'
        res = analyze(src)
        assert_has_error(self, res, "La condicion de while debe ser boolean.")

    def test_for_cond_boolean_error(self):
        src = 'for (let i: integer = 0; 1; i = i + 1) { }'
        res = analyze(src)
        assert_has_error(self, res, "La condicion del for debe ser boolean.")

    def test_break_outside_loop(self):
        src = 'break;'
        res = analyze(src)
        assert_has_error(self, res, "'break' solo puede usarse dentro de un bucle o switch.")

    def test_continue_outside_loop(self):
        src = 'continue;'
        res = analyze(src)
        assert_has_error(self, res, "'continue' solo puede usarse dentro de un bucle.")

    def test_return_outside_function(self):
        src = 'return 1;'
        res = analyze(src)
        assert_has_error(self, res, "return fuera de una funcion.")

    def test_class_access_ok(self):
        src = 'class A { let x: integer; function constructor() { this.x = 1; } function get(): integer { return this.x; } } let a: A = new A(); let y: integer = a.get();'
        res = analyze(src)
        assert_ok(self, res)

    def test_constructor_args_error(self):
        src = 'class A { function constructor(x: integer) { } } let a: A = new A();'
        res = analyze(src)
        assert_has_error(self, res, "Constructor de 'A' espera 1 argumento(s)")

    def test_this_outside_class(self):
        src = 'this;'
        res = analyze(src)
        assert_has_error(self, res, "Uso de 'this' fuera de una clase.")

    def test_property_access_non_object(self):
        src = 'let n: integer = 1; n.foo;'
        res = analyze(src)
        assert_has_error(self, res, "Acceso a propiedad sobre un valor no-objeto.")

    def test_index_non_array(self):
        src = 'let n: integer = 1; n[0];'
        res = analyze(src)
        assert_has_error(self, res, "Indexacion sobre un valor no-arreglo.")

    def test_index_non_int(self):
        src = 'let a: integer[] = [1,2]; let i: string = "0"; a[i];'
        res = analyze(src)
        assert_has_error(self, res, "El indice de un arreglo debe ser de tipo integer")

    def test_array_element_assign_type_error(self):
        src = 'let a: integer[] = [1,2]; a[0] = "x";'
        res = analyze(src)
        assert_has_error(self, res, "Tipo incompatible en asignacion a elemento de arreglo")

    def test_foreach_ok(self):
        src = 'let ns: integer[] = [1,2]; foreach (n in ns) { print(n); }'
        res = analyze(src)
        assert_ok(self, res)

    def test_foreach_non_array(self):
        src = 'let x: integer = 1; foreach (n in x) { }'
        res = analyze(src)
        assert_has_error(self, res, "La expresion de 'foreach' debe ser un arreglo.")

    def test_switch_case_type_mismatch(self):
        src = 'let s: string = "a"; switch (s) { case 1: print(1); }'
        res = analyze(src)
        assert_has_error(self, res, "Tipo de 'case' incompatible con 'switch'")

    def test_try_catch_ok(self):
        src = 'try { print("x"); } catch (e) { print(e); }'
        res = analyze(src)
        assert_ok(self, res)

    def test_method_as_value_error(self):
        src = 'class C { function constructor() {} function m(): integer { return 1; } } let c: C = new C(); let f = c.m;'
        res = analyze(src)
        assert_has_error(self, res, "No se puede usar el metodo 'C.m' como valor; invocalo con '()'.")

    def test_unknown_member_error(self):
        src = 'class C { function constructor() {} } let c: C = new C(); c.x = 1;'
        res = analyze(src)
        assert_has_error(self, res, "Atributo 'x' no existe en clase 'C'.")

    def test_assign_to_method_error(self):
        src = 'class C { function constructor() {} function m(): integer { return 1; } } let c: C = new C(); c.m = 2;'
        res = analyze(src)
        assert_has_error(self, res, "No se puede asignar al metodo 'C.m'.")

    def test_global_function_as_value_error(self):
        src = 'function foo(): integer { return 1; } let g = foo;'
        res = analyze(src)
        assert_has_error(self, res, "No se puede usar la funcion 'foo' como valor; invócala con '()'.")

    def test_unreachable_after_return(self):
        src = 'function f(): integer { return 1; let z = 2; }'
        res = analyze(src)
        assert_has_error(self, res, "Codigo inalcanzable")

    def test_unreachable_after_break(self):
        src = 'while (true) { break; let z = 1; }'
        res = analyze(src)
        assert_has_error(self, res, "Codigo inalcanzable")

    def test_dead_code_inside_if_true(self):
        src = 'function f(): integer { if (true) { return 1; print(2); } return 2; }'
        res = analyze(src)
        assert_has_error(self, res, "Codigo inalcanzable")

    def test_override_incompatible(self):
        src = 'class A { function m(x: integer): integer { return x; } } class B : A { function m(x: string): integer { return 1; } }'
        res = analyze(src)
        assert_has_error(self, res, "Override incompatible de metodo")

if __name__ == "__main__":
    unittest.main(verbosity=2)
