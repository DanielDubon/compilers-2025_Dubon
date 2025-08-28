from antlr4 import ParserRuleContext, ParseTreeWalker
from CompiscriptListener import CompiscriptListener
from symbols import (
    ScopeStack, VarInfo,
    Type, ArrayType, TypeLike,
    INT, BOOL, STR, FLT, VOID, NULL, UNKNOWN,
    TYPE_BY_NAME,
    is_boolean, is_numeric, is_string, is_unknown,
    type_equals, numeric_result, are_eq_comparable, are_order_comparable,
    can_concat_with_plus, is_assignable,
)
from typing import Optional, Tuple, Dict, List
import sys

class SemanticListener(CompiscriptListener):
   

    def __init__(self, source_lines):
        self.scopes = ScopeStack()
        self.errors = []
        self.source_lines = source_lines
        self.types: dict[object, TypeLike] = {}
        self.funcs: Dict[tuple[Optional[str], str], tuple[list[TypeLike], TypeLike]] = {}
        self.loop_depth = 0            
        self.func_ret_stack: list[TypeLike] = []  
        self.switch_depth = 0
        self.block_term_stack = []
        self.class_stack: list[str] = []




    # ------------ Utilidades ----------------

    def _tok(self, ctx: ParserRuleContext):
        
        if hasattr(ctx, "start"):
            return ctx.start
        
        if hasattr(ctx, "symbol"):
            return ctx.symbol
        return None

    def _lc(self, tok):
        line = getattr(tok, "line", 0) or 0
        col  = getattr(tok, "column", 0) or 0
        return line, col

    def _err(self, ctx, msg: str):
        tok = self._tok(ctx)
        line, col = self._lc(tok)
        sys.stderr.write("\x1b[91;1mError semantico (linea {}, columna {})\x1b[0m\n".format(line, col))
        if 1 <= line <= len(self.source_lines):
            src = self.source_lines[line - 1].rstrip("\n")
            sys.stderr.write("\x1b[2m    {}\n    {}\x1b[0m\n".format(src, " " * col + "^"))
        sys.stderr.write("  {}\n\n".format(msg))
        self.errors.append((line, col, msg))

    def set_type(self, node, t: TypeLike):
        self.types[node] = t

    def t(self, node) -> TypeLike:
        return self.types.get(node, UNKNOWN)

    # ----------- ambitos ----------------

    def enterBlock(self, ctx):
        # Abre un nuevo ambito
        self.scopes.push()
        self.block_term_stack.append(False)

       
        parent = getattr(ctx, "parentCtx", None)
        if parent is None:
            return

        pname = parent.__class__.__name__

        
        if pname == "ForeachStatementContext":
            id_tok = parent.Identifier().getSymbol()
            vname = id_tok.text
            seq_expr = parent.expression()
            # por si expression() devuelve lista
            if isinstance(seq_expr, list):
                seq_expr = seq_expr[0] if seq_expr else None
            seq_t = self.t(seq_expr) if seq_expr is not None else UNKNOWN
            if isinstance(seq_t, ArrayType):
                elem_t = seq_t.elem
            else:
                elem_t = UNKNOWN
                self._err(parent, "La expresion de 'foreach' debe ser un arreglo.")
            self.scopes.declare(vname, VarInfo(vname, elem_t, False, id_tok))

       
        elif pname == "TryCatchStatementContext":
            blocks = parent.block()
            # normaliza a lista
            if not isinstance(blocks, list):
                blocks = [blocks]
          
            if len(blocks) >= 2 and ctx is blocks[1]:
                id_tok = parent.Identifier().getSymbol()
                ename = id_tok.text
                
                self.scopes.declare(ename, VarInfo(ename, STR, False, id_tok))



    def exitBlock(self, ctx):
        self.scopes.pop()
        self.block_term_stack.pop()
        
    def _mark_terminator(self):
        if self.block_term_stack:
            self.block_term_stack[-1] = True

    def _check_unreachable(self, ctx):
        if self.block_term_stack and self.block_term_stack[-1]:
            self._err(ctx, "Codigo inalcanzable: aparece despues de un return/break/continue.")


    # ----------- Declaraciones ----------------

    def exitConstantDeclaration(self, ctx):
        id_tok = ctx.Identifier().getSymbol()
        name = id_tok.text

        annotated = None
        if ctx.typeAnnotation():
            annotated = self._type_from_annotation(ctx.typeAnnotation().type_())

        
        rhs_node = None
        
        if hasattr(ctx, "expression"):
            try:
                rhs_node = ctx.expression()
            except TypeError:
               
                try:
                    rhs_node = ctx.expression(0)
                except Exception:
                    rhs_node = None
        
        if rhs_node is None and hasattr(ctx, "initializer") and ctx.initializer():
            rhs_node = ctx.initializer().expression()

        if rhs_node is None:
            self._err(ctx, "La constante '{}' debe inicializarse.".format(name))
            return

        rhs_t = self.t(rhs_node)

       
        if annotated is not None and not is_assignable(annotated, rhs_t):
            self._err(
                ctx,
                "Tipo incompatible en inicializacion de const '{}': se esperaba {}, se obtuvo {}."
                .format(name, annotated, rhs_t)
            )
            typ = annotated
        else:
            typ = annotated if annotated is not None else rhs_t

        ok = self.scopes.declare(name, VarInfo(name, typ, True, id_tok))
        if not ok:
            self._err(ctx, "Redeclaracion de '{}' en el mismo ambito.".format(name))


    def exitVariableDeclaration(self, ctx):
        id_tok = ctx.Identifier().getSymbol()
        name = id_tok.text

        annotated = None
        if ctx.typeAnnotation():
            annotated = self._type_from_annotation(ctx.typeAnnotation().type_())

        init_t = None
        if ctx.initializer():
            init_t = self.t(ctx.initializer().expression())

       
        if annotated is None and init_t is not None:
            var_t = init_t
        else:
            var_t = annotated if annotated is not None else UNKNOWN

      
        if annotated is not None and init_t is not None:
            if not is_assignable(annotated, init_t):
                self._err(ctx, "Tipo incompatible en inicializacion de variable '{}': se esperaba {}, se obtuvo {}."
                          .format(name, annotated, init_t))

        ok = self.scopes.declare(name, VarInfo(name, var_t, False, id_tok))
        if not ok:
            self._err(ctx, "Redeclaracion de '{}' en el mismo ambito.".format(name))

    # ---------- Asignaciones ----------------

    def exitAssignment(self, ctx):
        
        ids = ctx.Identifier()
        name = (ids[0] if isinstance(ids, list) else ids).getText()

        
        exprs = ctx.expression()
        if isinstance(exprs, list):
            rhs_node = exprs[-1] if exprs else None
        else:
            rhs_node = exprs

        rhs_t = self.t(rhs_node) if rhs_node is not None else UNKNOWN
        self._assign_to_name(ctx, name, rhs_t)




    def exitAssignExpr(self, ctx):
      
        rhs_t = self.t(ctx.assignmentExpr())
        
        lhs = ctx.leftHandSide()
        base = lhs.primaryAtom()
        if base is not None and base.getChildCount() == 1 and base.getChild(0).getText().isidentifier():
            name = base.getChild(0).getText()
            self._assign_to_name(ctx, name, rhs_t)
            self.set_type(ctx, rhs_t) 
        else:
           
            self.set_type(ctx, UNKNOWN)

    def _assign_to_name(self, ctx, name: str, rhs_t: TypeLike):
        info = self.scopes.resolve(name)
        if info is None:
            self._err(ctx, "Asignacion a identificador no declarado: '{}'.".format(name))
            return
        if info.is_const:
            self._err(ctx, "No se puede reasignar a constante '{}'."
                      .format(name))
            return
        # Inferencia si la variable no tenía tipo concreto
        if is_unknown(info.type):
            info.type = rhs_t
            return
        if not is_assignable(info.type, rhs_t):
            self._err(ctx, "Tipo incompatible en asignacion a '{}': se esperaba {}, se obtuvo {}."
                      .format(name, info.type, rhs_t))

    # --------- Expresiones y tipos ----------------

    def exitPrimaryExpr(self, ctx):
        if ctx.literalExpr():
            self.set_type(ctx, self.t(ctx.literalExpr()))
        elif ctx.leftHandSide():
            self.set_type(ctx, self.t(ctx.leftHandSide()))
        else:
            self.set_type(ctx, self.t(ctx.expression()))

    def exitLiteralExpr(self, ctx):
        # Literal | arrayLiteral | 'null' | 'true' | 'false'
        if ctx.arrayLiteral():
            self.set_type(ctx, self.t(ctx.arrayLiteral()))
            return

        text = ctx.getText()
        if text == "true" or text == "false":
            self.set_type(ctx, BOOL)
        elif text == "null":
            self.set_type(ctx, NULL)
        else:
            # Token Literal: entero o cadena
            # Si comienza con comillas => string; si no => integer
            if len(text) > 0 and text[0] == '"':
                self.set_type(ctx, STR)
            else:
                self.set_type(ctx, INT)

    def exitExpression(self, ctx):
        
        self.set_type(ctx, self.t(ctx.assignmentExpr()))

    def exitExprNoAssign(self, ctx):
        
        self.set_type(ctx, self.t(ctx.conditionalExpr()))

    def exitIdentifierExpr(self, ctx):
        
        parent = getattr(ctx, "parentCtx", None)
        is_call_position = False
        if parent is not None and parent.__class__.__name__ == "LeftHandSideContext" and parent.getChildCount() >= 2:
            for i in range(1, parent.getChildCount()):
                if parent.getChild(i).__class__.__name__ == "CallExprContext":
                    is_call_position = True
                    break

        name = ctx.getText()

        
        info = self.scopes.resolve(name)
        if info is not None:
            self.set_type(ctx, info.type)
            return

        
        if self._is_global_func(name):
            if is_call_position:
                self.set_type(ctx, UNKNOWN)   # lo tipa exitLeftHandSide
            else:
                self._err(ctx, f"No se puede usar la funcion '{name}' como valor; invócala con '()'.")
                self.set_type(ctx, UNKNOWN)
            return

        
        if is_call_position:
            self._err(ctx, f"Llamada a identificador no declarado: '{name}'.")
        else:
            self._err(ctx, f"Uso de variable no declarada: '{name}'.")
        self.set_type(ctx, UNKNOWN)



    def exitArrayLiteral(self, ctx):
        elems = ctx.expression()
        if not elems:
            self.set_type(ctx, ArrayType(UNKNOWN))
            return
        elem_type = self.t(elems[0])
        ok = True
        for e in elems[1:]:
            t = self.t(e)
            if not type_equals(t, elem_type):
                ok = False
                break
        if not ok:
            self._err(ctx, "Elementos del arreglo con tipos inconsistentes.")
            self.set_type(ctx, ArrayType(UNKNOWN))
        else:
            self.set_type(ctx, ArrayType(elem_type))

    def exitLeftHandSide(self, ctx):
        
        curr = self._type_of_primary_atom(ctx.primaryAtom())

       
        n = ctx.getChildCount()
        i = 1
        while i < n:
            child = ctx.getChild(i)
            cname = child.__class__.__name__

            if cname == "CallExprContext":
                
                atom = ctx.primaryAtom()
                base_name = atom.getText() if atom and atom.__class__.__name__ == "IdentifierExprContext" else None

                if base_name and self._is_global_func(base_name):
                    
                    param_types, ret_t = [], UNKNOWN
                    for (cls, fname), sig in self.funcs.items():
                        if cls is None and fname == base_name:
                            param_types, ret_t = sig
                            break

                    
                    args_node = child.arguments() if hasattr(child, "arguments") else None
                    if args_node is None:
                        for k in range(child.getChildCount()):
                            if child.getChild(k).__class__.__name__ == "ArgumentsContext":
                                args_node = child.getChild(k)
                                break

                    arg_types = []
                    if args_node:
                        exprs = args_node.expression()
                        if not isinstance(exprs, list):
                            exprs = [exprs] if exprs else []
                        for e in exprs:
                            arg_types.append(self.t(e))

                    
                    if len(arg_types) != len(param_types):
                        self._err(child, f"Llamada a '{base_name}' con {len(arg_types)} argumento(s), se esperaban {len(param_types)}.")
                    else:
                        for i_arg, (pt, at) in enumerate(zip(param_types, arg_types), 1):
                            if not is_assignable(pt, at):
                                self._err(child, f"Argumento {i_arg} de '{base_name}' incompatible: se esperaba {pt}, se obtuvo {at}.")

                    curr = ret_t
                else:
                    
                    curr = UNKNOWN

            elif cname == "IndexExprContext":
                
                if isinstance(curr, ArrayType):
                  
                    idx_expr = None
                    if hasattr(child, "expression"):
                        try:
                            idx_expr = child.expression()
                            if isinstance(idx_expr, list):
                                idx_expr = idx_expr[0] if idx_expr else None
                        except Exception:
                            idx_expr = None
                    idx_t = self.t(idx_expr) if idx_expr is not None else UNKNOWN
                    if idx_t != INT:
                        self._err(child, "El indice de un arreglo debe ser de tipo integer.")
                    curr = curr.elem
                else:
                    self._err(child, "Indexacion sobre un valor no-arreglo.")
                    curr = UNKNOWN

            elif cname == "PropertyAccessExprContext":
                
                curr = UNKNOWN

            i += 1

        self.set_type(ctx, curr)


    def _type_of_primary_atom(self, atom_ctx) -> TypeLike:
        # primaryAtom:
        #   Identifier                 # IdentifierExpr
        # | 'new' Identifier '(' ...  # NewExpr
        # | 'this'                    # ThisExpr

        if atom_ctx is None:
            return UNKNOWN

        cname = atom_ctx.__class__.__name__
        if cname == "IdentifierExprContext":
            # El tipo se guarda en el contexto 
            return self.t(atom_ctx)
        if cname == "NewExprContext":
            tname = atom_ctx.getChild(1).getText()
            return Type(tname)
        #asda
        if cname == "ThisExprContext":
            return UNKNOWN

        # Fallback: intenta con el primer hijo
        first = atom_ctx.getChild(0)
        return self.t(first)


    # --- Operadores binarios -----

    def exitMultiplicativeExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            t2 = self.t(ctx.getChild(i+1))
            if numeric_result(tcur, t2) is None:
                self._err(ctx.getChild(i), "Operandos de '{}' deben ser numericos.".format(op))
                tcur = UNKNOWN
            else:
                tcur = numeric_result(tcur, t2)
            i += 2
        self.set_type(ctx, tcur)

    def exitAdditiveExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            t2 = self.t(ctx.getChild(i+1))
            if op == "+":
                # concat o suma
                if can_concat_with_plus(tcur, t2):
                    tcur = STR
                else:
                    res = numeric_result(tcur, t2)
                    if res is None:
                        self._err(ctx.getChild(i), "Tipos invalidos para '+': {} y {}."
                                  .format(tcur, t2))
                        tcur = UNKNOWN
                    else:
                        tcur = res
            else:  # '-'
                res = numeric_result(tcur, t2)
                if res is None:
                    self._err(ctx.getChild(i), "Operandos de '-' deben ser numericos.")
                    tcur = UNKNOWN
                else:
                    tcur = res
            i += 2
        self.set_type(ctx, tcur)

    def exitLogicalAndExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op_node = ctx.getChild(i)
            t2 = self.t(ctx.getChild(i+1))
            if not (is_boolean(tcur) and is_boolean(t2)):
                self._err(op_node, "Operandos de '&&' deben ser booleanos.")
                tcur = UNKNOWN
            else:
                tcur = BOOL
            i += 2
        self.set_type(ctx, tcur)

    def exitLogicalOrExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op_node = ctx.getChild(i)
            t2 = self.t(ctx.getChild(i+1))
            if not (is_boolean(tcur) and is_boolean(t2)):
                self._err(op_node, "Operandos de '||' deben ser booleanos.")
                tcur = UNKNOWN
            else:
                tcur = BOOL
            i += 2
        self.set_type(ctx, tcur)

    def exitEqualityExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            t2 = self.t(ctx.getChild(i+1))
            if not are_eq_comparable(tcur, t2):
                self._err(ctx.getChild(i), "Operandos de '{}' deben ser de tipos compatibles (mismo tipo o numericos)."
                          .format(op))
            tcur = BOOL
            i += 2
        self.set_type(ctx, tcur)

    def exitRelationalExpr(self, ctx):
        tcur = self.t(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            t2 = self.t(ctx.getChild(i+1))
            if not are_order_comparable(tcur, t2):
                self._err(ctx.getChild(i), "Operandos de '{}' deben ser numericos.".format(op))
            tcur = BOOL
            i += 2
        self.set_type(ctx, tcur)

    def exitUnaryExpr(self, ctx):
        # ('-' | '!') unaryExpr | primaryExpr
        if ctx.getChildCount() == 2:
            op = ctx.getChild(0).getText()
            t1 = self.t(ctx.getChild(1))
            if op == "!":
                if not is_boolean(t1):
                    self._err(ctx, "Operando de '!' debe ser booleano.")
                    self.set_type(ctx, UNKNOWN)
                else:
                    self.set_type(ctx, BOOL)
            else:
                # '-'
                if not is_numeric(t1):
                    self._err(ctx, "Operando de '-' debe ser numerico.")
                    self.set_type(ctx, UNKNOWN)
                else:
                    self.set_type(ctx, t1)
        else:
            self.set_type(ctx, self.t(ctx.getChild(0)))

    def exitTernaryExpr(self, ctx):
        
        if ctx.getChildCount() == 1:
            self.set_type(ctx, self.t(ctx.getChild(0)))
            return
        cond_t = self.t(ctx.getChild(0))
        then_t = self.t(ctx.getChild(2))
        else_t = self.t(ctx.getChild(4))
        if not is_boolean(cond_t):
            self._err(ctx, "La condicion del operador ternario debe ser boolean.")
        if not type_equals(then_t, else_t):
            self._err(ctx, "Las ramas del ternario deben ser del mismo tipo ({} vs {})."
                      .format(then_t, else_t))
            self.set_type(ctx, UNKNOWN)
        else:
            self.set_type(ctx, then_t)

    # ----------- Condiciones en estructuras ----------------

    def exitIfStatement(self, ctx):
        self._check_boolean_cond(ctx.expression(), "if")

    

  

    

    # ----------- Parse de anotaciones de tipo ----------------

    def _type_from_annotation(self, type_ctx) -> TypeLike:
      
        base = self._base_from_baseType(type_ctx.baseType())
    
        dims = 0
        for i in range(1, type_ctx.getChildCount()):
            if type_ctx.getChild(i).getText() == "[":
                dims += 1
        t: TypeLike = base
        for _ in range(dims):
            t = ArrayType(t)
        return t

    def _base_from_baseType(self, base_ctx) -> TypeLike:
        name = base_ctx.getText()
        return TYPE_BY_NAME.get(name, Type(name))

    def _check_boolean_cond(self, expr_ctx, where: str):
        cond_t = self.t(expr_ctx)
        if not is_boolean(cond_t):
            self._err(expr_ctx, f"La condicion de {where} debe ser boolean.")
            
    def enterFunctionDeclaration(self, ctx):
        fname = ctx.Identifier().getText()
        params_nodes = ctx.parameters().parameter() if ctx.parameters() else []
        param_types = [(self._type_from_annotation(p.type_()) if p.type_() else UNKNOWN) for p in params_nodes]
        ret_t = self._type_from_annotation(ctx.type_()) if ctx.type_() else UNKNOWN
        
        current_class = self.class_stack[-1] if self.class_stack else None
        key = (current_class, fname)

        if key in self.funcs:
           
            self._err(ctx, f"Funcion '{fname}' redeclarada.")
        else:
            self.funcs[key] = (param_types, ret_t)
       
        self.scopes.push()
        for p, ptype in zip(params_nodes, param_types):
            id_tok = p.Identifier().getSymbol()
            pname = id_tok.text
            ok = self.scopes.declare(pname, VarInfo(pname, ptype, False, id_tok))
            if not ok:
                self._err(p, f"Parametro '{pname}' redeclarado en la misma funcion.")
        self.func_ret_stack.append(ret_t)
                
    def _is_global_func(self, name: str) -> bool:
        for (cls, fname) in self.funcs.keys():
            if cls is None and fname == name:
                return True
        return False

        
    

    def exitFunctionDeclaration(self, ctx):
        self.scopes.pop()
        
        self.func_ret_stack.pop()

    
    def exitReturnStatement(self, ctx):
        
        if not self.func_ret_stack:
            self._err(ctx, "return fuera de una funcion.")
            return

        expected = self.func_ret_stack[-1]
        expr = getattr(ctx, "expression", None)
        has_expr = False
        expr_t = VOID

        if callable(expr):
            ex = ctx.expression()
            if isinstance(ex, list):
                ex = ex[0] if ex else None
            if ex is not None:
                has_expr = True
                expr_t = self.t(ex)

        if expected == VOID:
            if has_expr:
                self._err(ctx, f"La funcion es 'void' y no debe retornar valor (se obtuvo {expr_t}).")
        else:
            if not has_expr:
                self._err(ctx, f"La funcion debe retornar {expected}, pero no se retorno valor.")
            elif not is_assignable(expected, expr_t):
                self._err(ctx, f"Tipo de retorno incompatible: se esperaba {expected}, se obtuvo {expr_t}.")
        self._mark_terminator()

   
    def enterWhileStatement(self, ctx):
        self.loop_depth += 1
    def exitWhileStatement(self, ctx):
        self._check_boolean_cond(ctx.expression(), "while")
        self.loop_depth -= 1

    def enterDoWhileStatement(self, ctx):
        self.loop_depth += 1
    def exitDoWhileStatement(self, ctx):
        self._check_boolean_cond(ctx.expression(), "do-while")
        self.loop_depth -= 1

    def enterForStatement(self, ctx):
        self.loop_depth += 1
    def exitForStatement(self, ctx):
        
        children = ctx.children or []
        exprs = [ch for ch in children if ch.__class__.__name__.endswith("ExpressionContext")]
        if exprs:
            cond_t = self.t(exprs[0])
            if not is_boolean(cond_t):
                self._err(exprs[0], "La condicion del for debe ser boolean.")
        self.loop_depth -= 1

    def enterForeachStatement(self, ctx):
        self.loop_depth += 1

    def exitForeachStatement(self, ctx):
        self.loop_depth -= 1
    
    def exitBreakStatement(self, ctx):
        if self.loop_depth == 0 and self.switch_depth == 0:
            self._err(ctx, "'break' solo puede usarse dentro de un bucle o switch.")
        self._mark_terminator()

    def exitContinueStatement(self, ctx):
        if self.loop_depth == 0:
            self._err(ctx, "'continue' solo puede usarse dentro de un bucle.")
        self._mark_terminator()
    
    def enterSwitchStatement(self, ctx):
        self.switch_depth += 1

    def exitSwitchStatement(self, ctx):
        
        sw_expr = getattr(ctx, "expression", None)
        if callable(sw_expr):
            sw_expr = ctx.expression()
        sw_t = self.t(sw_expr) if sw_expr is not None else UNKNOWN

        # ver cada case
        cases = []
        if hasattr(ctx, "caseClause"):
            try:
                cases = ctx.caseClause()
            except Exception:
                cases = []
        for cc in (cases or []):
            ce = getattr(cc, "expression", None)
            if callable(ce):
                ce = cc.expression()
            ct = self.t(ce) if ce is not None else UNKNOWN
            if not are_eq_comparable(sw_t, ct):
                self._err(ce or cc, f"Tipo de 'case' incompatible con 'switch' ({sw_t} vs {ct}).")

        self.switch_depth -= 1
        
    def enterStatement(self, ctx):
        self._check_unreachable(ctx)

    def enterClassDeclaration(self, ctx):
        cname = ctx.Identifier(0).getText()
        self.class_stack.append(cname)

    def exitClassDeclaration(self, ctx):
        self.class_stack.pop()
