import pytest
import re
from pathlib import Path
from tests.conftest import run_compiler

class TestMIPSGeneratorArithmetic:
    """Tests para operaciones aritméticas en MIPS"""
    
    def test_generate_addition(self):
        """Debe generar instrucción ADD"""
        src = "let x: integer = 2 + 3;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "add" in mips.lower(), "No se generó instrucción ADD"
            print(f"Instrucción ADD generada correctamente")
    
    def test_generate_subtraction(self):
        """Debe generar instrucción SUB"""
        src = "let x: integer = 5 - 3;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "sub" in mips.lower(), "No se generó instrucción SUB"
            print(f"Instrucción SUB generada correctamente")
    
    def test_generate_multiplication(self):
        """Debe generar instrucción MUL o MULT"""
        src = "let x: integer = 4 * 5;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "mul" in mips.lower() or "mult" in mips.lower(), \
                "No se generó instrucción MUL/MULT"
            print(f"Instrucción MUL generada correctamente")
    
    def test_generate_division(self):
        """Debe generar instrucción DIV"""
        src = "let x: integer = 10 / 2;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "div" in mips.lower(), "No se generó instrucción DIV"
            print(f"Instrucción DIV generada correctamente")

class TestMIPSGeneratorFunctions:
    """Tests para generación de funciones en MIPS"""
    
    def test_function_prologue(self):
        """Debe generar prólogo de función"""
        src = "function foo(): integer { return 0; }"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "addi $sp, $sp" in mips, "No se genera prólogo (ajuste SP)"
            assert "sw" in mips.lower(), "No se guarda registro de retorno"
            print(f"Prólogo de función generado correctamente")
    
    def test_function_epilogue(self):
        """Debe generar epílogo de función"""
        src = "function foo(): integer { return 0; }"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "lw" in mips.lower(), "No se restauran registros"
            assert "jr $ra" in mips or "jr   $ra" in mips, "No hay retorno de función"
            print(f"Epílogo de función generado correctamente")
    
    def test_function_call(self):
        """Debe generar instrucción JAL"""
        src = """\
function add(a: integer, b: integer): integer {
    return a + b;
}
let result: integer = add(2, 3);
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "jal" in mips.lower(), "No se generó instrucción JAL para llamada"
            print(f"Llamada a función (JAL) generada correctamente")
    
    def test_parameter_loading(self):
        """Debe cargar parámetros en $a0-$a3"""
        src = "function foo(x: integer, y: integer): integer { return x + y; }"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "$a0" in mips or "$a1" in mips, "No se cargan parámetros"
            print(f"Parámetros cargados en registros de argumentos")
    
    def test_return_value(self):
        """Debe asignar valor de retorno a $v0"""
        src = "function getValue(): integer { return 42; }"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "$v0" in mips or "v0" in mips, "No se asigna retorno a $v0"
            print(f"Valor de retorno asignado a $v0")

class TestMIPSGeneratorControl:
    """Tests para estructuras de control en MIPS"""
    
    def test_if_statement(self):
        """Debe generar saltos condicionales"""
        src = """\
let x: integer = 5;
if (x > 3) {
    let y: integer = 1;
} else {
    let y: integer = 2;
}
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "beq" in mips.lower() or "bne" in mips.lower() or \
                   "blt" in mips.lower() or "bgt" in mips.lower(), \
                "No se generan saltos condicionales"
            print(f"Estructuras de control (if) generadas correctamente")
    
    def test_while_loop(self):
        """Debe generar etiquetas y saltos para while"""
        src = """\
let i: integer = 0;
while (i < 5) {
    i = i + 1;
}
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            # Debe tener etiquetas
            assert re.search(r'L\d+:', mips) or "label" in mips.lower(), \
                "No se generan etiquetas para while"
            print(f"Bucle while generado con etiquetas")
    
    def test_label_generation(self):
        """Debe generar etiquetas únicas"""
        src = """\
if (true) { let x: integer = 1; }
if (true) { let y: integer = 2; }
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            labels = re.findall(r'L(\d+):', mips)
            # Todas las etiquetas deben ser únicas
            assert len(labels) == len(set(labels)), "Etiquetas duplicadas"
            print(f"Etiquetas únicas generadas: {set(labels)}")

class TestMIPSGeneratorMemory:
    """Tests para manejo de memoria en MIPS"""
    
    def test_stack_allocation(self):
        """Debe asignar espacio en stack"""
        src = """\
function foo(): integer {
    let x: integer = 1;
    let y: integer = 2;
    return x + y;
}
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "addi $sp, $sp, -" in mips, "No se asigna stack"
            print(f"Espacio en stack asignado")
    
    def test_stack_deallocation(self):
        """Debe liberar espacio en stack"""
        src = "function foo(): integer { return 0; }"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            assert "addi $sp, $sp, " in mips and "addi $sp, $sp, -" in mips, \
                "No se libera stack correctamente"
            print(f"Stack liberado al salir de función")
    
    def test_save_restore_registers(self):
        """Debe guardar y restaurar registros saved"""
        src = """\
function foo(): integer {
    let local1: integer = 10;
    let local2: integer = 20;
    return local1 + local2;
}
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            # Debe haber sw y lw para registros
            sw_count = mips.lower().count("sw")
            lw_count = mips.lower().count("lw")
            assert sw_count > 0 and lw_count > 0, "No se guardan/restauran registros"
            print(f"Registros guardados ({sw_count}) y restaurados ({lw_count})")

class TestMIPSGeneratorErrors:
    """Tests para manejo de errores en generación MIPS"""
    
    def test_no_duplicate_labels(self):
        """No debe generar etiquetas duplicadas"""
        src = """\
if (true) { let x: integer = 1; }
if (true) { let y: integer = 2; }
if (true) { let z: integer = 3; }
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            labels = re.findall(r'(\w+):', mips)
            duplicates = [label for label in labels if labels.count(label) > 1]
            assert len(duplicates) == 0, f"Etiquetas duplicadas encontradas: {duplicates}"
            print(f"No hay etiquetas duplicadas")
    
    def test_no_duplicate_main(self):
        """No debe haber múltiples definiciones de main"""
        src = "let x: integer = 1;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            main_count = mips.count("main:")
            assert main_count == 1, f"main aparece {main_count} veces (debe ser 1)"
            print(f"Una sola definición de main")
    
    def test_balanced_stack_operations(self):
        """Las operaciones de stack deben estar balanceadas"""
        src = """\
function foo(a: integer, b: integer): integer {
    let x: integer = a + b;
    return x;
}
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            # Extraer decrementos y incrementos de SP
            decrements = re.findall(r'addi \$sp, \$sp, -(\d+)', mips)
            increments = re.findall(r'addi \$sp, \$sp, (\d+)(?![a-z])', mips)
            
            total_decrement = sum(int(x) for x in decrements)
            total_increment = sum(int(x) for x in increments)
            
            assert total_decrement == total_increment, \
                f"Stack no balanceado: -{total_decrement} vs +{total_increment}"
            print(f"Stack balanceado: -{total_decrement} == +{total_increment}")

class TestMIPSGeneratorIntegration:
    """Tests de integración para el generador MIPS"""
    
    def test_complete_program_execution(self):
        """Programa completo debe generar MIPS válido"""
        src = """\
function fibonacci(n: integer): integer {
    if (n <= 1) {
        return n;
    } else {
        return fibonacci(n - 1) + fibonacci(n - 2);
    }
}

let result: integer = fibonacci(5);
"""
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            # Validaciones básicas
            assert ".text" in mips, "No hay sección .text"
            assert "main:" in mips or ".globl" in mips, "No hay punto de entrada"
            assert "fibonacci:" in mips, "No se generó función fibonacci"
            print(f"Programa completo generado correctamente")
    
    def test_mips_syntax_validity(self):
        """El MIPS generado debe tener sintaxis válida"""
        src = "let x: integer = 10; let y: integer = 20; let z: integer = x + y;"
        out, err, tac, code = run_compiler(src)
        
        mips_file = Path(__file__).resolve().parents[1] / "out.s"
        if mips_file.exists():
            mips = mips_file.read_text()
            lines = mips.split('\n')
            
            # Verificar que las líneas tengan instrucciones válidas
            valid_instrs = [
                'add', 'sub', 'mul', 'div', 'addi', 'subi', 'li',
                'lw', 'sw', 'move', 'beq', 'bne', 'blt', 'bgt',
                'jal', 'jr', 'j', 'and', 'or', 'xor'
            ]
            
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('.'):
                    # Debe ser etiqueta o instrucción válida
                    if ':' not in line:
                        first_word = line.split()[0] if line.split() else ''
                        assert any(instr in first_word for instr in valid_instrs) or \
                               first_word in ['main', 'fibonacci'], \
                               f"Instrucción inválida: {first_word}"
            
            print(f"Sintaxis MIPS válida")