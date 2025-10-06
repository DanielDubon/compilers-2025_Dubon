from dataclasses import dataclass, field
from typing import Optional, Dict, List, Tuple
from symbols import TypeLike, VarInfo, ScopeStack, TYPE_SIZES



@dataclass
class FunctionInfo:
    name: str
    params: List[VarInfo]
    ret_type: Optional[TypeLike]
    is_method: bool = False
    is_constructor: bool = False
    label: Optional[str] = None
    stack_size: int = 0
    local_vars: List[VarInfo] = field(default_factory=list)  
    level: int = 0
    frame_layout: "FrameLayout" = None


@dataclass
class FrameLayout:
    static_link_offset: int = -8
    dynamic_link_offset: int = 0
    return_addr_offset: int = 8
    next_local_offset: int = 16
    next_param_offset: int = -16
    locals: Dict[str, int] = field(default_factory=dict)   # <- default_factory
    params: Dict[str, int] = field(default_factory=dict)   # <- default_factory

    def alloc_local(self, v: VarInfo) -> int:
        size = TYPE_SIZES.get(getattr(v.type, "name", ""), TYPE_SIZES["default"])
        off = self.next_local_offset
        self.locals[v.name] = off
        self.next_local_offset += size
        return off

    def alloc_param(self, v: VarInfo) -> int:
        size = TYPE_SIZES.get(getattr(v.type, "name", ""), TYPE_SIZES["default"])
        off = self.next_param_offset
        self.params[v.name] = off
        self.next_param_offset -= size
        return off

    @property
    def frame_size(self) -> int:

        return self.next_local_offset


    
@dataclass
class ClassInfo:
    name: str
    base: Optional[str]
    fields: Dict[str, VarInfo]
    methods: Dict[str, FunctionInfo]
    vtable_label: Optional[str] = None  
    size: int = 0  # Tamaño total de la clase en memoria

class SymbolTable:
    def __init__(self):
        self.scopes = ScopeStack()    
        if not self.scopes.stack:
            self.scopes.push()  # variables por nivel
        self.functions: Dict[str, FunctionInfo] = {}
        self.classes: Dict[str, "ClassInfo"] = {}
        self.next_memory_address = 0
        self.next_label_id = 0
        self.func_stack: list[FunctionInfo] = []   # para conocer función actual al entrar/salir
        self.current_function: Optional[FunctionInfo] = None
    @property
    
    def globals(self):
        """Devuelve el diccionario del scope global (índice 0)."""
        # por si acaso alguien vació la pila
        if not self.scopes.stack:
            self.scopes.push()
        return self.scopes.stack[0]

    # ------------- VARIABLES -------------
    def declare_var(self, name: str, varinfo: VarInfo) -> bool:
        if self.scopes.level == 0:
            varinfo.is_global = True
            self.globals[name] = varinfo
        return True

    def resolve_var(self, name: str) -> Optional[VarInfo]:
        return self.scopes.resolve(name)

    # ------------- FUNCIONES -------------
    def declare_func(self, finfo: FunctionInfo) -> bool:
        if finfo.name in self.functions:
            return False
        # Inicializa layout del frame y nivel léxico de la función
        finfo.level = self.scopes.level
        finfo.frame_layout = FrameLayout()
        self.functions[finfo.name] = finfo
        return True

    def resolve_func(self, name: str) -> Optional[FunctionInfo]:
        return self.functions.get(name)

    # --- Entrar/salir de función (para semántica/TAC) ---
    def enter_function(self, name: str) -> None:
        finfo = self.functions[name]
        self.func_stack.append(finfo)
        self.current_function = finfo
        self.push_scope()  # abre entorno de función

        # Asignar offsets a parámetros (FP-negativos)
        if finfo.params:
            for p in finfo.params:
                p.is_parameter = True
                p.frame_offset = finfo.frame_layout.alloc_param(p)
                p.level = self.scopes.level
                self.scopes.declare(p.name, p)

    def leave_function(self) -> None:
        finfo = self.func_stack.pop()
        # Cierra el scope de función
        self.pop_scope()
        # Finaliza tamaño de frame
        finfo.stack_size = finfo.frame_layout.frame_size
        self.current_function = self.func_stack[-1] if self.func_stack else None

    # ------------- CLASES -------------
    def declare_class(self, cinfo: "ClassInfo") -> bool:
        if cinfo.name in self.classes:
            return False
        self.classes[cinfo.name] = cinfo
        return True

    def resolve_class(self, name: str) -> Optional["ClassInfo"]:
        return self.classes.get(name)

    # ------------- ENTORNOS -------------
    def push_scope(self):
        self.scopes.push()

    def pop_scope(self):
        self.scopes.pop()

    # ------------- ASIGNACIÓN DE MEMORIA (GLOBALES) -------------
    def allocate_memory_address(self, size: int = 1) -> str:
        address = f"mem_{self.next_memory_address}"
        self.next_memory_address += size
        return address

    def assign_memory_addresses(self):
        if not self.scopes.stack:
            return
        global_scope = self.scopes.stack[0]
        for name, varinfo in global_scope.items():
            if not varinfo.memory_address:
                varinfo.memory_address = self.allocate_memory_address()
                varinfo.is_global = True

    # ------------- LABELS -------------
    def generate_label(self, prefix: str = "L") -> str:
        label = f"{prefix}{self.next_label_id}"
        self.next_label_id += 1
        return label

    def assign_function_labels(self):
        for func_name, func_info in self.functions.items():
            if not func_info.label:
                func_info.label = f"func_{func_name}"

    # ------------- API de AR -------------
    def allocate_local(self, v: VarInfo) -> int:
        if self.current_function is None:
            return 0
        off = self.current_function.frame_layout.alloc_local(v)
        v.frame_offset = off
        v.level = self.scopes.level      # <- importante para address_of / dumps
        v.is_global = False
        self.current_function.local_vars.append(v)  # opcional, útil para inspección
        return off

    def address_of(self, name: str) -> Tuple[int, Optional[int]]:
        """
        Devuelve (level, frame_offset) para direccionamiento FP relativo.
        Si es global: (0, None) y deberías mirar VarInfo.memory_address.
        """
        v = self.resolve_var(name)
        if v is None:
            return (0, None)
        if v.is_global:
            return (0, None)
        return (v.level, v.frame_offset)

    # ------------- DUMP -------------
    def dump(self) -> str:
        lines = ["--- Symbol Table ---"]

        lines.append("Variables:")
        for i, scope in enumerate(self.scopes.stack):
            lines.append(f"  Scope {i}:")
            for name, varinfo in scope.items():
                mem_addr = varinfo.memory_address or "N/A"
                lines.append(
                    f"    {name} -> type={varinfo.type}, const={varinfo.is_const}, "
                    f"offset={varinfo.offset}, frame_off={varinfo.frame_offset}, "
                    f"level={varinfo.level}, global={varinfo.is_global}, addr={mem_addr}"
                )

        lines.append("Functions:")
        for fname, finfo in self.functions.items():
            params = ", ".join(f"{p.name}:{p.type}@{p.frame_offset}" for p in finfo.params)
            label = finfo.label or "N/A"
            fl = finfo.frame_layout
            lines.append(
                f"  {fname}({params}) -> {finfo.ret_type}, label={label}, "
                f"stack_size={finfo.stack_size}, locals={list(fl.locals.items()) if fl else []}"
            )

        lines.append("Classes:")
        for cname, cinfo in self.classes.items():
            lines.append(f"  class {cinfo.name} extends {cinfo.base}")
            for fname, f in cinfo.methods.items():
                params = ", ".join(f"{p.name}:{p.type}" for p in f.params)
                lines.append(f"    method {fname}({params}) -> {f.ret_type}")
            for vname, vinfo in cinfo.fields.items():
                lines.append(f"    field {vname}: {vinfo.type}")
        return "\n".join(lines)