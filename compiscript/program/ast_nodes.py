
from dataclasses import dataclass, field
from typing import List, Optional, Union


@dataclass
class Node:
    line: int
    col: int


class TypeRef(Node): pass

@dataclass
class SimpleType(TypeRef):
    name: str

@dataclass
class ArrayTypeRef(TypeRef):
    elem: TypeRef


@dataclass
class Program(Node):
    decls: List["Decl"] = field(default_factory=list)

class Decl(Node): pass

@dataclass
class VarDecl(Decl):
    name: str
    type: Optional[TypeRef]
    init: Optional["Expr"]
    kind: str 

@dataclass
class Param(Node):
    name: str
    type: Optional[TypeRef]

@dataclass
class FunctionDecl(Decl):
    name: str
    params: List[Param]
    ret: Optional[TypeRef]
    body: "Block"
    is_method: bool = False  
    is_constructor: bool = False

@dataclass
class ClassDecl(Decl):
    name: str
    base: Optional[str]
    fields: List[VarDecl]
    methods: List[FunctionDecl]

# ---- sentencias ----
class Stmt(Node): pass

@dataclass
class Block(Stmt):
    stmts: List[Stmt]

@dataclass
class If(Stmt):
    cond: "Expr"
    then: Block
    else_: Optional[Block]

@dataclass
class While(Stmt):
    cond: "Expr"
    body: Block

@dataclass
class DoWhile(Stmt):
    body: Block
    cond: "Expr"

@dataclass
class For(Stmt):
    init: Optional[Union[VarDecl, "Expr"]]
    cond: Optional["Expr"]
    update: Optional["Expr"]
    body: Block

@dataclass
class Foreach(Stmt):
    var_name: str
    elem_type: Optional[TypeRef]
    seq: "Expr"
    body: Block

@dataclass
class SwitchCase(Node):
    value: "Expr"
    body: Block

@dataclass
class Switch(Stmt):
    expr: "Expr"
    cases: List[SwitchCase]
    default: Optional[Block]

@dataclass
class Break(Stmt): pass
@dataclass
class Continue(Stmt): pass

@dataclass
class Return(Stmt):
    expr: Optional["Expr"]

@dataclass
class TryCatch(Stmt):
    try_block: Block
    err_name: str
    catch_block: Block

@dataclass
class ExprStmt(Stmt):
    expr: "Expr"

@dataclass
class Assign(Stmt):
    target: "LValue"
    value: "Expr"

# ---- expresiones ----
class Expr(Node): pass
class LValue(Expr): pass

@dataclass
class Name(LValue):
    name: str

@dataclass
class Member(LValue):
    obj: Expr
    name: str

@dataclass
class Index(LValue):
    arr: Expr
    index: Expr

@dataclass
class Call(Expr):
    callee: Expr
    args: List[Expr]

@dataclass
class New(Expr):
    class_name: str
    args: List[Expr]

@dataclass
class Unary(Expr):
    op: str
    expr: Expr

@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr

@dataclass
class Ternary(Expr):
    cond: Expr
    then: Expr
    otherwise: Expr

@dataclass
class ArrayLiteral(Expr):
    elems: List[Expr]

@dataclass
class LiteralInt(Expr):
    value: int

@dataclass
class LiteralFloat(Expr):
    value: float

@dataclass
class LiteralString(Expr):
    value: str

@dataclass
class LiteralBool(Expr):
    value: bool

@dataclass
class LiteralNull(Expr):
    pass
