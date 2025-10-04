
from ast_nodes import Node, Program, VarDecl, Assign, Binary, LiteralInt, Name, LiteralString, LiteralBool, LiteralNull, If, Block, ExprStmt, Call, While, FunctionDecl, DoWhile, For, Foreach, Switch, SwitchCase, Break, Continue, Return, TryCatch, Member, Index, New, Ternary, Unary, ArrayLiteral, LiteralFloat # Importar nodos necesarios
from tac import TAC, Assign as TAC_Assign, BinaryOp, Label, Jump, CondJump, Param, Call as TAC_Call, BeginFunc, EndFunc, Return, UnaryOp
from symbol_table import SymbolTable
from ast_nodes import Return as AST_Return
from tac import Return as TAC_Return

class TempPool:
    def __init__(self, prefix="t"):
        self.prefix = prefix
        self.free = []         
        self.counter = 0       

    def acquire(self) -> str:
        """Devuelve el nombre de un temporal reusandolo si hay libres"""
        if self.free:
            return self.free.pop()
        name = f"{self.prefix}{self.counter}"
        self.counter += 1
        return name

    def release(self, name: str) -> None:
        """Devuelve un temporal al pool (si tiene el prefijo correcto)"""
        if isinstance(name, str) and name.startswith(self.prefix):
            self.free.append(name)

class TACGenerator:
    def __init__(self, symbtab: SymbolTable):
        self.symbtab = symbtab
        self.code = []
        self.temp_count = 0
        self.label_count = 0
        self.temp_pool = TempPool("t")

    def new_temp(self) -> str:
        return self.temp_pool.acquire()
    
    ARITH_OPS = {"+", "-", "*", "/"}
    
    def _is_temp(self, addr):
        return isinstance(addr, str) and addr.startswith(self.temp_pool.prefix)
    
    def _release_if_temp(self, addr):
        if isinstance(addr, str) and addr.startswith(self.temp_pool.prefix):
            self.temp_pool.release(addr)

    def new_label(self) -> str:
        """Genera un nuevo nombre de etiqueta."""
        label_name = f"L{self.label_count}"
        self.label_count += 1
        return label_name

    def visit(self, node: Node):
        if node is None:
            return
        method_name = 'visit' + node.__class__.__name__
        print(f"[DEBUG TACGen] Visiting node: {node.__class__.__name__}, method: {method_name}")
        visitor = getattr(self, method_name, self.generic_visit)
        result = visitor(node)
        print(f"[DEBUG TACGen] Finished visiting node: {node.__class__.__name__}, result: {result}")
        return result

    def generic_visit(self, node: Node):
        print(f"[DEBUG TACGen] Entering simplified generic_visit for {node.__class__.__name__}")
        if hasattr(node, '__dataclass_fields__'): # Check if it's an AST node
            for field_name in node.__dataclass_fields__:
                field_value = getattr(node, field_name)
                if isinstance(field_value, list):
                    for item in field_value:
                        if hasattr(item, '__dataclass_fields__'): # is an AST node
                            self.visit(item)
                elif hasattr(field_value, '__dataclass_fields__'): # is an AST node
                    self.visit(field_value)
                elif field_value is not None and not isinstance(field_value, (str, int, float, bool)):
                    # Handle other non-primitive values
                    self.visit(field_value)
        print(f"[DEBUG TACGen] Exiting simplified generic_visit for {node.__class__.__name__}")
        return None # Generic visit usually doesn't return a specific value for statements

    def generate(self, node: Node):
        """Punto de entrada para generar el código TAC a partir de un nodo del AST."""
        self.visit(node)
        return self.code

    # --- Métodos Visit --- #

    def visitProgram(self, ctx: Program):
        print(f"[DEBUG TACGen] Entering visitProgram")
        
        self.generic_visit(ctx)
        print(f"[DEBUG TACGen] Exiting visitProgram")



    def visitBlock(self, ctx: Block):
        self.generic_visit(ctx)

    def visitFunctionDecl(self, ctx: FunctionDecl):
        self.code.append(Label(name=ctx.name))
        self.code.append(BeginFunc())
        self.visit(ctx.body)
        self.code.append(EndFunc())

    def visitVarDecl(self, ctx: VarDecl):
        print(f"[DEBUG TACGen] Entering visitVarDecl for {ctx.name}")
        print(f"[DEBUG TACGen] ctx.init type: {type(ctx.init)}, value: {ctx.init}")
        if ctx.init:
            # Si ctx.init es una lista, tomar el primer elemento
            if isinstance(ctx.init, list) and len(ctx.init) > 0:
                init_node = ctx.init[0]
            else:
                init_node = ctx.init
            
            rhs_addr = self.visit(init_node)
            print(f"[DEBUG TACGen] rhs_addr after visit: {rhs_addr}")
            if rhs_addr is None:
                rhs_addr = "0"  # Valor por defecto
            self.code.append(TAC_Assign(target=ctx.name, source=rhs_addr))
            self._release_if_temp(rhs_addr)
        print(f"[DEBUG TACGen] Exiting visitVarDecl for {ctx.name}")

    def visitAssign(self, ctx: Assign):
        # Si ctx.value es una lista, tomar el primer elemento
        if isinstance(ctx.value, list) and len(ctx.value) > 0:
            value_node = ctx.value[0]
        else:
            value_node = ctx.value
            
        rhs_addr = self.visit(value_node)
        if rhs_addr is None:
            rhs_addr = "0"  # Valor por defecto
            
        # Asumimos que el target es un nombre simple por ahora
        if hasattr(ctx.target, 'name'):
            self.code.append(TAC_Assign(target=ctx.target.name, source=rhs_addr))
            self._release_if_temp(rhs_addr)

    def visitBinary(self, ctx: Binary):
        # normaliza si vienen listas
        left_node  = ctx.left[0]  if isinstance(ctx.left, list) and ctx.left  else ctx.left
        right_node = ctx.right[0] if isinstance(ctx.right, list) and ctx.right else ctx.right

        left_addr  = self.visit(left_node)
        right_addr = self.visit(right_node)

        if left_addr is None:  left_addr = "0"
        if right_addr is None: right_addr = "0"

        if ctx.op in self.ARITH_OPS:
            
            if self._is_temp(left_addr):
                target = left_addr
            elif self._is_temp(right_addr):
                target = right_addr
            else:
                target = self.new_temp()

            self.code.append(BinaryOp(target=target, left=left_addr, op=ctx.op, right=right_addr))

            
            if target != left_addr:
                self._release_if_temp(left_addr)
            if target != right_addr:
                self._release_if_temp(right_addr)

            return target

        
        temp_target = self.new_temp()
        self.code.append(BinaryOp(target=temp_target, left=left_addr, op=ctx.op, right=right_addr))
        self._release_if_temp(left_addr)
        self._release_if_temp(right_addr)
        return temp_target


    def visitExprStmt(self, ctx: ExprStmt):
        addr = self.visit(ctx.expr)
        self._release_if_temp(addr)
        
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
        return "None"

    def visitIf(self, ctx: If):
        # Manejar el caso donde ctx.cond puede ser una lista
        if isinstance(ctx.cond, list) and len(ctx.cond) > 0:
            cond_node = ctx.cond[0]
        else:
            cond_node = ctx.cond
            
        cond_addr = self.visit(cond_node)
        if cond_addr is None:
            cond_addr = "True"  # Valor por defecto si no se puede evaluar la condición

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



    def visitCall(self, ctx: Call):
        # Por ahora, asumimos que el callee es un nombre simple
        callee_name = ctx.callee.name if hasattr(ctx.callee, 'name') else 'unknown_call'
        
        arg_addrs = []
        for arg in ctx.args:
            # Manejar el caso donde arg puede ser una lista
            if isinstance(arg, list) and len(arg) > 0:
                arg_node = arg[0]
            else:
                arg_node = arg
                
            arg_addr = self.visit(arg_node)
            if arg_addr is None:
                arg_addr = "0"  # Valor por defecto
            arg_addrs.append(arg_addr)
            self.code.append(Param(value=arg_addr))
        
        # Las llamadas a función pueden devolver un valor, así que generamos un temporal para él
        ret_temp = self.new_temp()
        self.code.append(TAC_Call(target=ret_temp, name=callee_name, num_params=len(arg_addrs)))
        return ret_temp

    def visitWhile(self, ctx: While):
        start_label = self.new_label()
        end_label = self.new_label()

        self.code.append(Label(name=start_label))
        
        # Manejar el caso donde ctx.cond puede ser una lista
        if isinstance(ctx.cond, list) and len(ctx.cond) > 0:
            cond_node = ctx.cond[0]
        else:
            cond_node = ctx.cond
            
        cond_addr = self.visit(cond_node)
        if cond_addr is None:
            cond_addr = "True"  # Valor por defecto
        self.code.append(CondJump(condition=cond_addr, target=end_label))
        self.visit(ctx.body)
        self.code.append(Jump(target=start_label))
        self.code.append(Label(name=end_label))

    def visitDoWhile(self, ctx: DoWhile):
        start_label = self.new_label()
        end_label = self.new_label()

        self.code.append(Label(name=start_label))
        self.visit(ctx.body)
        cond_addr = self.visit(ctx.cond)
        if cond_addr is None:
            cond_addr = "True"
        self.code.append(CondJump(condition=cond_addr, target=end_label))
        self.code.append(Jump(target=start_label))
        self.code.append(Label(name=end_label))

    def visitFor(self, ctx: For):
        start_label = self.new_label()
        end_label = self.new_label()
        update_label = self.new_label()

        # Inicialización
        if ctx.init:
            self.visit(ctx.init)

        self.code.append(Label(name=start_label))
        
        # Condición
        if ctx.cond:
            cond_addr = self.visit(ctx.cond)
            if cond_addr is None:
                cond_addr = "True"
            self.code.append(CondJump(condition=cond_addr, target=end_label))
        
        # Cuerpo del bucle
        self.visit(ctx.body)
        
        # Actualización
        self.code.append(Label(name=update_label))
        if ctx.update:
            self.visit(ctx.update)
        
        self.code.append(Jump(target=start_label))
        self.code.append(Label(name=end_label))

    def visitForeach(self, ctx: Foreach):
        start_label = self.new_label()
        end_label = self.new_label()
        next_label = self.new_label()

        # Generar código para iterar sobre la secuencia
        seq_addr = self.visit(ctx.seq)
        if seq_addr is None:
            seq_addr = "[]"
        
        # Crear variable temporal para el índice
        index_temp = self.new_temp()
        self.code.append(TAC_Assign(target=index_temp, source="0"))
        
        self.code.append(Label(name=start_label))
        
        # Verificar si hay más elementos
        length_temp = self.new_temp()
        self.code.append(BinaryOp(target=length_temp, left=seq_addr, op="length", right="0"))
        
        cond_temp = self.new_temp()
        self.code.append(BinaryOp(target=cond_temp, left=index_temp, op="<", right=length_temp))
        self.code.append(CondJump(condition=cond_temp, target=end_label))
        
        # Obtener elemento actual
        elem_temp = self.new_temp()
        self.code.append(BinaryOp(target=elem_temp, left=seq_addr, op="[]", right=index_temp))
        
        # Asignar a la variable del foreach
        self.code.append(TAC_Assign(target=ctx.var_name, source=elem_temp))
        
        # Cuerpo del bucle
        self.visit(ctx.body)
        
        # Incrementar índice
        self.code.append(Label(name=next_label))
        inc_temp = self.new_temp()
        self.code.append(BinaryOp(target=inc_temp, left=index_temp, op="+", right="1"))
        self.code.append(TAC_Assign(target=index_temp, source=inc_temp))
        
        self.code.append(Jump(target=start_label))
        self.code.append(Label(name=end_label))

    def visitSwitch(self, ctx: Switch):
        expr_addr = self.visit(ctx.expr)
        if expr_addr is None:
            expr_addr = "0"
        
        end_label = self.new_label()
        default_label = self.new_label() if ctx.default else end_label
        
        # Generar casos
        for case in ctx.cases:
            case_label = self.new_label()
            case_value = self.visit(case.value)
            if case_value is None:
                case_value = "0"
            
            # Comparar con el valor del switch
            cond_temp = self.new_temp()
            self.code.append(BinaryOp(target=cond_temp, left=expr_addr, op="==", right=case_value))
            self.code.append(CondJump(condition=cond_temp, target=case_label))
            
            # Cuerpo del caso
            self.code.append(Label(name=case_label))
            self.visit(case.body)
            self.code.append(Jump(target=end_label))
        
        # Caso por defecto
        if ctx.default:
            self.code.append(Label(name=default_label))
            self.visit(ctx.default)
        
        self.code.append(Label(name=end_label))

    def visitBreak(self, ctx: Break):
        # Por simplicidad, asumimos que siempre hay una etiqueta de fin disponible
        # En una implementación completa, esto requeriría una pila de etiquetas
        self.code.append(Jump(target="break_target"))

    def visitContinue(self, ctx: Continue):
        # Por simplicidad, asumimos que siempre hay una etiqueta de continuación disponible
        # En una implementación completa, esto requeriría una pila de etiquetas
        self.code.append(Jump(target="continue_target"))

    def visitReturn(self, ctx: Return):
        if ctx.expr:
            # Si ctx.expr es una lista, tomar el primer elemento
            if isinstance(ctx.expr, list) and len(ctx.expr) > 0:
                expr_node = ctx.expr[0]
            else:
                expr_node = ctx.expr
            
            ret_addr = self.visit(expr_node)
            if ret_addr is None:
                ret_addr = "0"
            self.code.append(Return(value=ret_addr))
        else:
            self.code.append(Return(value=None))

    def visitTryCatch(self, ctx: TryCatch):
        try_label = self.new_label()
        catch_label = self.new_label()
        end_label = self.new_label()
        
        self.code.append(Label(name=try_label))
        self.visit(ctx.try_block)
        self.code.append(Jump(target=end_label))
        
        self.code.append(Label(name=catch_label))
        # Asignar el error a la variable
        self.code.append(TAC_Assign(target=ctx.err_name, source="error"))
        self.visit(ctx.catch_block)
        
        self.code.append(Label(name=end_label))

    def visitMember(self, ctx: Member):
        obj_addr = self.visit(ctx.obj)
        if obj_addr is None:
            obj_addr = "null"
        
        # Generar acceso a miembro
        temp_target = self.new_temp()
        self.code.append(BinaryOp(target=temp_target, left=obj_addr, op=".", right=f'"{ctx.name}"'))
        return temp_target

    def visitIndex(self, ctx: Index):
        arr_addr = self.visit(ctx.arr)
        index_addr = self.visit(ctx.index)
        
        if arr_addr is None:
            arr_addr = "null"
        if index_addr is None:
            index_addr = "0"
        
        # Generar acceso por índice
        temp_target = self.new_temp()
        self.code.append(BinaryOp(target=temp_target, left=arr_addr, op="[]", right=index_addr))
        return temp_target

    def visitNew(self, ctx: New):
        # Generar llamada al constructor
        class_name = ctx.class_name if hasattr(ctx, 'class_name') else 'Object'
        arg_addrs = []
        
        for arg in ctx.args:
            arg_addr = self.visit(arg)
            if arg_addr is None:
                arg_addr = "0"
            arg_addrs.append(arg_addr)
            self.code.append(Param(value=arg_addr))
        
        # Crear objeto
        obj_temp = self.new_temp()
        self.code.append(TAC_Call(target=obj_temp, name=f"new_{class_name}", num_params=len(arg_addrs)))
        return obj_temp


    def visitTernary(self, ctx: Ternary):
        # Manejar el caso donde ctx.cond puede ser una lista
        if isinstance(ctx.cond, list) and len(ctx.cond) > 0:
            cond_node = ctx.cond[0]
        else:
            cond_node = ctx.cond
            
        cond_addr = self.visit(cond_node)
        if cond_addr is None:
            cond_addr = "True"
        
        true_label = self.new_label()
        false_label = self.new_label()
        end_label = self.new_label()
        
        self.code.append(CondJump(condition=cond_addr, target=true_label))
        
        # Caso falso
        self.code.append(Label(name=false_label))
        false_addr = self.visit(ctx.otherwise)
        if false_addr is None:
            false_addr = "0"
        temp_target = self.new_temp()
        self.code.append(TAC_Assign(target=temp_target, source=false_addr))
        self.code.append(Jump(target=end_label))
        
        # Caso verdadero
        self.code.append(Label(name=true_label))
        true_addr = self.visit(ctx.then)
        if true_addr is None:
            true_addr = "0"
        self.code.append(TAC_Assign(target=temp_target, source=true_addr))
        
        self.code.append(Label(name=end_label))
        return temp_target

    def visitUnary(self, ctx: Unary):
        operand_addr = self.visit(ctx.operand)
        if operand_addr is None:
            operand_addr = "0"
        
        temp_target = self.new_temp()
        self.code.append(BinaryOp(target=temp_target, left=ctx.op, op="", right=operand_addr))
        self._release_if_temp(operand_addr)
        return temp_target

    def visitArrayLiteral(self, ctx: ArrayLiteral):
        # Crear array temporal
        arr_temp = self.new_temp()
        self.code.append(TAC_Assign(target=arr_temp, source="[]"))
        
        # Agregar elementos
        for elem in ctx.elems:
            elem_addr = self.visit(elem)
            if elem_addr is None:
                elem_addr = "0"
            self.code.append(BinaryOp(target=arr_temp, left=arr_temp, op="append", right=elem_addr))
        
        return arr_temp

    def visitLiteralFloat(self, ctx: LiteralFloat):
        return ctx.value
