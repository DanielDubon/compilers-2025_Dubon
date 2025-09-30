
from dataclasses import dataclass
from typing import Optional, Union

# Define los posibles "operandos" en una instrucción TAC.
# Puede ser una variable, una constante, o un temporal.
Address = Union[str, int, None]

@dataclass
class TAC:
    """Clase base para todas las instrucciones TAC."""
    def __str__(self):
        return "TAC Instruction"

@dataclass
class Assign(TAC):
    """Asignación: target = source"""
    target: Address
    source: Address

    def __str__(self):
        return f"{self.target} = {self.source}"

@dataclass
class BinaryOp(TAC):
    """Operación binaria: target = left op right"""
    target: Address
    left: Address
    op: str
    right: Address

    def __str__(self):
        return f"{self.target} = {self.left} {self.op} {self.right}"

@dataclass
class UnaryOp(TAC):
    """Operación unaria: target = op source"""
    target: Address
    op: str
    source: Address

    def __str__(self):
        return f"{self.target} = {self.op} {self.source}"

@dataclass
class Label(TAC):
    """Etiqueta para saltos: label_name:"""
    name: str

    def __str__(self):
        return f"{self.name}:"

@dataclass
class Jump(TAC):
    """Salto incondicional: goto label_name"""
    target: str

    def __str__(self):
        return f"goto {self.target}"

@dataclass
class CondJump(TAC):
    """Salto condicional: if_false condition goto label_name"""
    condition: Address
    target: str

    def __str__(self):
        return f"if_false {self.condition} goto {self.target}"

@dataclass
class Param(TAC):
    """Pasar un parámetro a una función: param p"""
    value: Address

    def __str__(self):
        return f"param {self.value}"

@dataclass
class Call(TAC):
    """Llamada a función: [target =] call name, num_params"""
    target: Optional[Address]
    name: str
    num_params: int

    def __str__(self):
        if self.target:
            return f"{self.target} = call {self.name}, {self.num_params}"
        return f"call {self.name}, {self.num_params}"

@dataclass
class Return(TAC):
    """Retorno de una función: return [value]"""
    value: Optional[Address]

    def __str__(self):
        if self.value is not None:
            return f"return {self.value}"
        return "return"

@dataclass
class BeginFunc(TAC):
    """Marcador de inicio de una función."""
    def __str__(self):
        return "BeginFunc"

@dataclass
class EndFunc(TAC):
    """Marcador de fin de una función."""
    def __str__(self):
        return "EndFunc"
