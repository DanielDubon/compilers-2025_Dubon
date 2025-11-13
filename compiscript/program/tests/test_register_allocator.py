import pytest
import sys
import os

# python3 -m pytest compiscript/program/tests/test_register_allocator.py

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../lab-obtenReg')))

from RegisterAllocator import RegisterAllocator

@pytest.fixture
def allocator():
    """Fixture de pytest para crear una nueva instancia de RegisterAllocator para cada test."""
    return RegisterAllocator()

def test_initial_state(allocator):
    """Verifica el estado inicial del asignador."""
    assert len(allocator.temp_regs) == 10
    assert len(allocator.saved_regs) == 8
    assert not allocator.register_descriptor
    assert not allocator.address_descriptor
    assert allocator.stack_offset == 0

def test_get_single_register(allocator):
    """Prueba la asignación de un único registro."""
    reg = allocator.get_reg('var_a')
    assert reg == '$t0'
    assert allocator.address_descriptor['var_a'] == '$t0'
    assert allocator.register_descriptor['$t0'] == 'var_a'
    assert len(allocator.temp_regs) == 9

def test_get_all_temp_registers(allocator):
    """Prueba la asignación de todos los registros temporales."""
    vars = [f'var_{i}' for i in range(10)]
    regs = set()
    for var in vars:
        reg = allocator.get_reg(var)
        regs.add(reg)
    
    assert len(regs) == 10
    assert not allocator.temp_regs  # Todos los registros $t deben estar en uso
    assert len(allocator.register_descriptor) == 10

def test_get_register_for_existing_variable(allocator):
    """Prueba que al pedir un registro para una variable existente, devuelve el mismo."""
    reg1 = allocator.get_reg('var_a')
    assert len(allocator.temp_regs) == 9
    
    reg2 = allocator.get_reg('var_a')
    assert reg1 == reg2
    assert len(allocator.temp_regs) == 9  # No se debe asignar un nuevo registro

def test_free_register(allocator):
    """Prueba que la liberación de un registro funciona correctamente."""
    reg = allocator.get_reg('var_a')
    assert reg == '$t0'
    assert len(allocator.temp_regs) == 9

    freed = allocator.free_reg(reg)
    assert freed is True
    assert len(allocator.temp_regs) == 10
    assert reg not in allocator.register_descriptor
    assert 'var_a' not in allocator.address_descriptor

def test_free_non_existent_register(allocator):
    """Prueba que intentar liberar un registro ya libre no causa problemas."""
    freed = allocator.free_reg('$t5')
    assert freed is False
    assert len(allocator.temp_regs) == 10

def test_spill_register_on_overflow(allocator):
    """Prueba el mecanismo de desbordamiento (spill) cuando no hay registros libres."""
    # Ocupar todos los registros temporales
    for i in range(10):
        allocator.get_reg(f'var_{i}')
    
    assert not allocator.temp_regs

    # Esta llamada debería disparar un desbordamiento
    new_reg = allocator.get_reg('new_var')
    
    # La estrategia de spill es sacar $t0 (el primero asignado)
    assert new_reg == '$t0'
    
    # Verificar que la variable original de $t0 ('var_0') fue movida a la pila
    assert allocator.address_descriptor['var_0'] == -4  # Primera posición en la pila
    assert allocator.stack_offset == -4
    
    # Verificar que la nueva variable ahora ocupa el registro $t0
    assert allocator.address_descriptor['new_var'] == '$t0'
    assert allocator.register_descriptor['$t0'] == 'new_var'
    
    # Verificar que se generó el código de spill
    spill_code = allocator.get_spill_code()
    assert len(spill_code) == 1
    assert spill_code[0] == "sw $t0, -4($sp)  # Spill var_0"

def test_multiple_spills(allocator):
    """Prueba múltiples desbordamientos para asegurar que la pila crece."""
    # Ocupar todos los registros
    for i in range(10):
        allocator.get_reg(f'var_{i}')

    # Primer spill
    allocator.get_reg('spill_1')
    assert allocator.address_descriptor['var_0'] == -4
    assert allocator.stack_offset == -4

    # Segundo spill
    allocator.get_reg('spill_2')
    assert allocator.address_descriptor['var_1'] == -8
    assert allocator.stack_offset == -8
    
    spill_code = allocator.get_spill_code()
    assert len(spill_code) == 2
    assert spill_code[0] == "sw $t0, -4($sp)  # Spill var_0"
    assert spill_code[1] == "sw $t1, -8($sp)  # Spill var_1"

def test_load_from_stack(allocator):
    """Prueba la carga de una variable desde la pila a un registro."""
    # Ocupar registros para forzar un spill
    for i in range(10):
        allocator.get_reg(f'var_{i}')
    
    allocator.get_reg('spill_var') # Esto desborda var_0 a -4($sp)
    
    # Ahora, cargar 'var_0' desde la pila. Debería usar el registro recién liberado ($t1)
    # porque la estrategia de spill saca el primero de la lista de descriptores.
    # En este caso, get_reg('spill_var') desborda $t0, que contenía 'var_0'.
    # Luego, load_from_stack('var_0') pide un registro, que será $t1.
    
    # Antes de cargar, 'var_0' está en la pila
    assert allocator.address_descriptor['var_0'] == -4

    # Para hacer espacio para cargar, otro registro debe ser desbordado.
    # 'spill_var' está en $t0. 'var_1' está en $t1.
    # load_from_stack pide un registro para 'var_0'. No hay libres.
    # Se desbordará 'var_1' (de $t1) para hacer espacio.
    reg = allocator.load_from_stack('var_0')

    # 'var_1' debería haber sido desbordado a -8($sp)
    assert allocator.address_descriptor['var_1'] == -8
    
    # 'var_0' ahora debería estar en el registro $t1
    assert reg == '$t1'
    assert allocator.address_descriptor['var_0'] == '$t1'
    assert allocator.register_descriptor['$t1'] == 'var_0'
    
    # Verificar el código generado
    code = allocator.get_spill_code()
    assert len(code) == 3
    assert "sw $t0, -4($sp)  # Spill var_0" in code
    assert "sw $t1, -8($sp)  # Spill var_1" in code
    assert f"lw {reg}, -4($sp)  # Load var_0" in code

def test_load_from_stack_error(allocator):
    """Prueba que se lanza un error si la variable no está en la pila."""
    allocator.get_reg('var_a') # var_a está en $t0, no en la pila
    with pytest.raises(ValueError, match="La variable 'var_a' no está en la pila."):
        allocator.load_from_stack('var_a')
