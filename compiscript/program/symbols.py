from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Type:
    name: str
    def __str__(self) -> str:
        return self.name

@dataclass(frozen=True)
class ArrayType:
    elem: "TypeLike"
    def __str__(self) -> str:
        return f"{self.elem}[]"

TypeLike = Union[Type, ArrayType]


INT   = Type("integer")
BOOL  = Type("boolean")
STR   = Type("string")
VOID  = Type("void")
FLT   = Type("float")      
NULL  = Type("null")
UNKNOWN = Type("<unknown>")

# Mapa por nombre
TYPE_BY_NAME = {
    "integer": INT,
    "boolean": BOOL,
    "string":  STR,
    "void":    VOID,
    "float":   FLT, 
}


def is_unknown(t: TypeLike) -> bool:
    return isinstance(t, Type) and t.name == UNKNOWN.name

def is_numeric(t: TypeLike) -> bool:
    return t in (INT, FLT)

def is_boolean(t: TypeLike) -> bool:
    return t == BOOL

def is_string(t: TypeLike) -> bool:
    return t == STR

def type_equals(a: TypeLike, b: TypeLike) -> bool:
    if isinstance(a, ArrayType) and isinstance(b, ArrayType):
        return type_equals(a.elem, b.elem)
    return a == b

def numeric_result(a: TypeLike, b: TypeLike) -> Optional[TypeLike]:
  
    if is_numeric(a) and is_numeric(b):
        if FLT in (a, b):
            return FLT
        return INT
    return None

def are_eq_comparable(a: TypeLike, b: TypeLike) -> bool:
    
    if type_equals(a, b):
        return True
    if is_numeric(a) and is_numeric(b):
        return True
    return False

def are_order_comparable(a: TypeLike, b: TypeLike) -> bool:

    return is_numeric(a) and is_numeric(b)

def can_concat_with_plus(a: TypeLike, b: TypeLike) -> bool:
   
    return is_string(a) or is_string(b)


def is_assignable(target: TypeLike, value: TypeLike) -> bool:
    
    if is_unknown(value):
        return True
    if is_unknown(target):
        return True
   
    if isinstance(target, ArrayType) and isinstance(value, ArrayType):
        return is_assignable(target.elem, value.elem)

    if is_numeric(target) and is_numeric(value):
        
        return type_equals(target, value)
    return type_equals(target, value)


@dataclass
class VarInfo:
    name: str
    type: TypeLike
    is_const: bool
    token: object

class ScopeStack:
    def __init__(self) -> None:
        self.stack: list[dict[str, VarInfo]] = [ {} ]

    def push(self) -> None:
        self.stack.append({})

    def pop(self) -> None:
        self.stack.pop()

    def declare(self, name: str, info: VarInfo) -> bool:
        curr = self.stack[-1]
        if name in curr:
            return False
        curr[name] = info
        return True

    def resolve(self, name: str) -> Optional[VarInfo]:
        for env in reversed(self.stack):
            if name in env:
                return env[name]
        return None
