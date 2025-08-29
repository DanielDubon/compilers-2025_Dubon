
from dataclasses import dataclass
from typing import Optional, Dict, List
from symbols import TypeLike, VarInfo, ScopeStack

@dataclass
class FunctionInfo:
    name: str
    params: List[VarInfo]
    ret_type: Optional[TypeLike]
    is_method: bool = False
    is_constructor: bool = False

@dataclass
class ClassInfo:
    name: str
    base: Optional[str]
    fields: Dict[str, VarInfo]
    methods: Dict[str, FunctionInfo]

class SymbolTable:
    def __init__(self):
        self.scopes = ScopeStack()      # variables locales y globales
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}

    # ------------------ VARIABLES ------------------
    def declare_var(self, name: str, varinfo: VarInfo) -> bool:
        """Declara variable en el entorno actual"""
        return self.scopes.declare(name, varinfo)

    def resolve_var(self, name: str) -> Optional[VarInfo]:
        """Busca variable en todos los entornos"""
        return self.scopes.resolve(name)

    # ------------------ FUNCIONES ------------------
    def declare_func(self, finfo: FunctionInfo) -> bool:
        if finfo.name in self.functions:
            return False
        self.functions[finfo.name] = finfo
        return True

    def resolve_func(self, name: str) -> Optional[FunctionInfo]:
        return self.functions.get(name)

    # ------------------ CLASES ------------------
    def declare_class(self, cinfo: ClassInfo) -> bool:
        if cinfo.name in self.classes:
            return False
        self.classes[cinfo.name] = cinfo
        return True

    def resolve_class(self, name: str) -> Optional[ClassInfo]:
        return self.classes.get(name)

    # ------------------ ENTORNOS ------------------
    def push_scope(self):
        self.scopes.push()

    def pop_scope(self):
        self.scopes.pop()

    # ------------------ IMPRESION ------------------
    def dump(self) -> str:
        lines = ["--- Symbol Table ---"]
        
        # Variables (solo el scope global)
        lines.append("Variables:")
        for i, scope in enumerate(self.scopes.stack):
            lines.append(f"  Scope {i}:")
            for name, varinfo in scope.items():
                lines.append(f"    {name} -> type={varinfo.type}, const={varinfo.is_const}")

        # Funciones
        lines.append("Functions:")
        for fname, finfo in self.functions.items():
            params = ", ".join(f"{p.name}:{p.type}" for p in finfo.params)
            lines.append(f"  {fname}({params}) -> {finfo.ret_type}")

        # Clases
        lines.append("Classes:")
        for cname, cinfo in self.classes.items():
            lines.append(f"  class {cinfo.name} extends {cinfo.base}")
            for fname, finfo in cinfo.methods.items():
                params = ", ".join(f"{p.name}:{p.type}" for p in finfo.params)
                lines.append(f"    method {fname}({params}) -> {finfo.ret_type}")
            for vname, vinfo in cinfo.fields.items():
                lines.append(f"    field {vname}: {vinfo.type}")

        return "\n".join(lines)