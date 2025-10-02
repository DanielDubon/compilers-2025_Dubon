
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
    label: Optional[str] = None  # Etiqueta para el código assembler
    stack_size: int = 0  # Tamaño del stack frame
    local_vars: List[VarInfo] = None  # Variables locales de la función

@dataclass
class ClassInfo:
    name: str
    base: Optional[str]
    fields: Dict[str, VarInfo]
    methods: Dict[str, FunctionInfo]
    vtable_label: Optional[str] = None  # Etiqueta para la tabla virtual
    size: int = 0  # Tamaño total de la clase en memoria

class SymbolTable:
    def __init__(self):
        self.scopes = ScopeStack()      # variables locales y globales
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, ClassInfo] = {}
        self.next_memory_address = 0    # Contador para direcciones de memoria
        self.next_label_id = 0          # Contador para etiquetas

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

    # ------------------ GENERACIÓN DE CÓDIGO ------------------
    def allocate_memory_address(self, size: int = 1) -> str:
        """Asigna una dirección de memoria y la devuelve"""
        address = f"mem_{self.next_memory_address}"
        self.next_memory_address += size
        return address

    def generate_label(self, prefix: str = "L") -> str:
        """Genera una nueva etiqueta única"""
        label = f"{prefix}{self.next_label_id}"
        self.next_label_id += 1
        return label

    def assign_memory_addresses(self):
        """Asigna direcciones de memoria a todas las variables globales"""
        for scope in self.scopes.stack:
            for name, varinfo in scope.items():
                if not varinfo.memory_address:
                    varinfo.memory_address = self.allocate_memory_address()
                    varinfo.is_global = True

    def assign_function_labels(self):
        """Asigna etiquetas a todas las funciones"""
        for func_name, func_info in self.functions.items():
            if not func_info.label:
                func_info.label = f"func_{func_name}"

    # ------------------ IMPRESION ------------------
    def dump(self) -> str:
        lines = ["--- Symbol Table ---"]
        
        # Variables (solo el scope global)
        lines.append("Variables:")
        for i, scope in enumerate(self.scopes.stack):
            lines.append(f"  Scope {i}:")
            for name, varinfo in scope.items():
                mem_addr = varinfo.memory_address or "N/A"
                lines.append(f"    {name} -> type={varinfo.type}, const={varinfo.is_const}, offset={varinfo.offset}, addr={mem_addr}")

        # Funciones
        lines.append("Functions:")
        for fname, finfo in self.functions.items():
            params = ", ".join(f"{p.name}:{p.type}" for p in finfo.params)
            label = finfo.label or "N/A"
            lines.append(f"  {fname}({params}) -> {finfo.ret_type}, label={label}")

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