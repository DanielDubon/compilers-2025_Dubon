
from ast_nodes import Node, Program, VarDecl, Assign, Binary, LiteralInt, Name, LiteralString, LiteralBool, LiteralNull, If, Block, ExprStmt, Call, While, FunctionDecl # Importar nodos necesarios
from tac import TAC, Assign as TAC_Assign, BinaryOp, Label, Jump, CondJump, Param, Call as TAC_Call, BeginFunc, EndFunc
from symbol_table import SymbolTable

class TACGenerator:
    def __init__(self, symbtab: SymbolTable):
        self.symbtab = symbtab
        self.code = []
        self.temp_count = 0
        self.label_count = 0

    def new_temp(self) -> str:
        """Genera un nuevo nombre de variable temporal."""
        temp_name = f"t{self.temp_count}"
        self.temp_count += 1
        return temp_name

    def new_label(self) -> str:
        """Genera un nuevo nombre de etiqueta."""
        label_name = f"L{self.label_count}"
        self.label_count += 1
        return label_name

    def visit(self, node: Node):
        """Método de visita genérico que despacha al método específico del nodo."""
        if node is None:
            return
        method_name = 'visit' + node.__class__.__name__
        visitor = getattr(self, method_name, self.generic_visit)
        return visitor(node)

    def generic_visit(self, node: Node):
        """Visita los hijos de un nodo si no hay un método específico."""
        for field_name in node.__dataclass_fields__:
            field_value = getattr(node, field_name)
            if isinstance(field_value, list):
                for item in field_value:
                    if hasattr(item, '__dataclass_fields__'): # es un nodo AST
                        self.visit(item)
            elif hasattr(field_value, '__dataclass_fields__'): # es un nodo AST
                self.visit(field_value)

    def generate(self, node: Node):
        """Punto de entrada para generar el código TAC a partir de un nodo del AST."""
        self.visit(node)
        return self.code

    # --- Métodos Visit --- #

    def visitProgram(self, ctx: Program):
        for decl in ctx.decls:
            self.visit(decl)

    def visitBlock(self, ctx: Block):
        for stmt in ctx.stmts:
            self.visit(stmt)

    def visitFunctionDecl(self, ctx: FunctionDecl):
        self.code.append(Label(name=ctx.name))
        self.code.append(BeginFunc())
        self.visit(ctx.body)
        self.code.append(EndFunc())

    def visitVarDecl(self, ctx: VarDecl):
        if ctx.init:
            rhs_addr = self.visit(ctx.init)
            self.code.append(TAC_Assign(target=ctx.name, source=rhs_addr))

    def visitAssign(self, ctx: Assign):
        rhs_addr = self.visit(ctx.value)
        # Asumimos que el target es un nombre simple por ahora
        if hasattr(ctx.target, 'name'):
            self.code.append(TAC_Assign(target=ctx.target.name, source=rhs_addr))

    def visitBinary(self, ctx: Binary):
        left_addr = self.visit(ctx.left)
        right_addr = self.visit(ctx.right)
        temp_target = self.new_temp()
        self.code.append(BinaryOp(target=temp_target, left=left_addr, op=ctx.op, right=right_addr))
        return temp_target

    def visitLiteralInt(self, ctx: LiteralInt):
        return ctx.value

    def visitName(self, ctx: Name):
        return ctx.name

    def visitLiteralString(self, ctx: LiteralString):
        # Devolvemos el string entre comillas para diferenciarlo de los nombres de variables en el TAC
        return f'"{ctx.value}"'

    def visitLiteralBool(self, ctx: LiteralBool):
        return ctx.value

    def visitLiteralNull(self, ctx: LiteralNull):
        return "null"

    def visitIf(self, ctx: If):
        cond_addr = self.visit(ctx.cond)

        if ctx.else_:
            # Caso if-else
            else_label = self.new_label()
            end_label = self.new_label()

            self.code.append(CondJump(condition=cond_addr, target=else_label))
            self.visit(ctx.then)
            self.code.append(Jump(target=end_label))
            self.code.append(Label(name=else_label))
            self.visit(ctx.else_)
            self.code.append(Label(name=end_label))
        else:
            # Caso if sin else
            end_label = self.new_label()

            self.code.append(CondJump(condition=cond_addr, target=end_label))
            self.visit(ctx.then)
            self.code.append(Label(name=end_label))

    def visitExprStmt(self, ctx: ExprStmt):
        self.visit(ctx.expr)

    def visitCall(self, ctx: Call):
        # Por ahora, asumimos que el callee es un nombre simple
        callee_name = ctx.callee.name if hasattr(ctx.callee, 'name') else 'unknown_call'
        
        arg_addrs = [self.visit(arg) for arg in ctx.args]
        for arg_addr in arg_addrs:
            self.code.append(Param(value=arg_addr))
        
        # Las llamadas a función pueden devolver un valor, así que generamos un temporal para él
        ret_temp = self.new_temp()
        self.code.append(TAC_Call(target=ret_temp, name=callee_name, num_params=len(arg_addrs)))
        return ret_temp

    def visitWhile(self, ctx: While):
        start_label = self.new_label()
        end_label = self.new_label()

        self.code.append(Label(name=start_label))
        cond_addr = self.visit(ctx.cond)
        self.code.append(CondJump(condition=cond_addr, target=end_label))
        self.visit(ctx.body)
        self.code.append(Jump(target=start_label))
        self.code.append(Label(name=end_label))
