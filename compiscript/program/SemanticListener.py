from antlr4 import ParserRuleContext, ParseTreeWalker
from symbol_table import SymbolTable, FunctionInfo, ClassInfo
from CompiscriptListener import CompiscriptListener
from symbols import (
    ScopeStack, VarInfo,
    Type, ArrayType, TypeLike,
    INT, BOOL, STR, FLT, VOID, NULL, UNKNOWN,
    TYPE_BY_NAME, TYPE_SIZES,
    is_boolean, is_numeric, is_string, is_unknown,
    type_equals, numeric_result, are_eq_comparable, are_order_comparable,
    can_concat_with_plus, is_assignable,
)
from typing import Optional, Tuple, Dict, List
import sys

class SemanticListener(CompiscriptListener):
    def __init__(self, source_lines):
        self.symbtab = SymbolTable()
        self.scopes = self.symbtab.scopes
        self.errors = []
        self.source_lines = source_lines
        self.types: dict[object, TypeLike] = {}
        self.funcs: Dict[tuple[Optional[str], str], tuple[list[TypeLike], TypeLike]] = {}
        self.loop_depth = 0
        self.func_ret_stack: list[TypeLike] = []
        self.switch_depth = 0
        self.block_term_stack = []
        self.class_stack: list[str] = []
        self.class_fields: dict[str, dict[str, TypeLike]] = {}
        self.class_extends: dict[str, Optional[str]] = {}
        self.returns: dict[object, bool] = {}
        self._switch_expr_nodes: list[object] = []
        self._switch_types: list[TypeLike] = []
        self.func_key_stack: list[tuple[Optional[str], str]] = []
        self.func_locals: Dict[tuple[Optional[str], str], set[str]] = {}
        self.func_captures: Dict[tuple[Optional[str], str], set[str]] = {}


    def _get_type_size(self, var_type: TypeLike) -> int:
        if isinstance(var_type, Type):
            return TYPE_SIZES.get(var_type.name, TYPE_SIZES["default"])
        elif isinstance(var_type, ArrayType):
            return TYPE_SIZES["default"] # Arrays are references
        return 0 # Unknown or void types

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
        always_returns = False
        for st in (ctx.statement() or []):
            if not always_returns and self._ret(st):
                always_returns = True
        self._set_returns(ctx, always_returns)
        
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

        # Campos de clase fuera de métodos
        if self.class_stack and not self.func_ret_stack:
            annotated = self._type_from_annotation(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
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
                self._err(ctx, f"La constante de clase '{name}' debe inicializarse.")
                return
            rhs_t = self.t(rhs_node)
            if annotated is not None and not self._is_assignable(annotated, rhs_t):
                self._err(ctx, f"Tipo incompatible en inicializacion de const de clase '{name}': {annotated} vs {rhs_t}")
                typ = annotated
            else:
                typ = annotated if annotated is not None else rhs_t
            cname = self.class_stack[-1]
            fields = self.class_fields.setdefault(cname, {})
            if name in fields:
                self._err(ctx, f"Campo '{name}' redeclarado en la clase '{cname}'.")
            else:
                fields[name] = typ
                self._set_returns(ctx, False)
            return

        # Variables top-level / locales
        annotated = self._type_from_annotation(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None

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
            self._err(ctx, f"La constante '{name}' debe inicializarse.")
            return

        rhs_t = self.t(rhs_node)
        if annotated is not None and not self._is_assignable(annotated, rhs_t):
            self._err(ctx, f"Tipo incompatible en inicializacion de const '{name}': se esperaba {annotated}, se obtuvo {rhs_t}.")
            typ = annotated
        else:
            typ = annotated if annotated is not None else rhs_t

        var_info = VarInfo(name, typ, True, id_tok)  # sin offset manual

        ok = self.scopes.declare(name, var_info)
        if not ok:
            self._err(ctx, f"Redeclaracion de '{name}' en el mismo ambito.")
        else:
            if self.func_key_stack:
                # Local de función
                self.symbtab.allocate_local(var_info)
                self.func_locals[self.func_key_stack[-1]].add(name)
            else:
                # Global
                self.symbtab.declare_var(name, var_info)
        self._set_returns(ctx, False)

    def exitPrintStatement(self, ctx):
        
        self._set_returns(ctx, False)
    
    def exitExpressionStatement(self, ctx):
    
        self._set_returns(ctx, False)
        
    def exitVariableDeclaration(self, ctx):
        id_tok = ctx.Identifier().getSymbol()
        name = id_tok.text

        if self.class_stack and not self.func_ret_stack:
            annotated = self._type_from_annotation(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
            init_t = self.t(ctx.initializer().expression()) if ctx.initializer() else None
            var_t = init_t if (annotated is None and init_t is not None) else (annotated if annotated is not None else UNKNOWN)

            if annotated is not None and init_t is not None and not self._is_assignable(annotated, init_t):
                self._err(ctx, f"Tipo incompatible en inicializacion de variable '{name}': se esperaba {annotated}, se obtuvo {init_t}")

            cname = self.class_stack[-1]
            fields = self.class_fields.setdefault(cname, {})
            if name in fields:
                self._err(ctx, f"Campo '{name}' redeclarado en la clase '{cname}'.")
            else:
                fields[name] = var_t
                self._set_returns(ctx, False)
            return

        # --- Variables top-level o locales de función ---
        annotated = self._type_from_annotation(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
        init_t = self.t(ctx.initializer().expression()) if ctx.initializer() else None
        var_t = init_t if (annotated is None and init_t is not None) else (annotated if annotated is not None else UNKNOWN)

        if annotated is not None and init_t is not None and not self._is_assignable(annotated, init_t):
            self._err(ctx, f"Tipo incompatible en inicializacion de variable '{name}': se esperaba {annotated}, se obtuvo {init_t}")

        var_info = VarInfo(name, var_t, False, id_tok)  # sin offset manual

        ok = self.scopes.declare(name, var_info)
        if not ok:
            self._err(ctx, f"Redeclaracion de '{name}' en el mismo ambito.")
        else:
            if self.symbtab.current_function is not None:
                # Local de función: asigna offset relativo a FP
                self.symbtab.allocate_local(var_info)
                if self.func_key_stack:
                    self.func_locals[self.func_key_stack[-1]].add(name)
            else:
                # Global: solo se declara; la dirección se asigna al final
                self.symbtab.declare_var(name, var_info)

        self._set_returns(ctx, False)



    # ---------- Asignaciones ----------------

    def exitAssignment(self, ctx):
        self._set_returns(ctx, False)

        exprs = ctx.expression()

        if isinstance(exprs, list):
           
            if len(exprs) == 2 and hasattr(ctx, "Identifier") and ctx.Identifier():
                obj_expr = exprs[0]
                rhs_node = exprs[1]
                obj_t = self.t(obj_expr)
                member = ctx.Identifier().getText()
                rhs_t = self.t(rhs_node)
                self._check_property_assignment(ctx, obj_t, member, rhs_t)
                return

           
            if len(exprs) == 3:
                arr_expr, idx_expr, rhs_node = exprs[0], exprs[1], exprs[2]
                arr_t = self.t(arr_expr)
                idx_t = self.t(idx_expr)
                rhs_t = self.t(rhs_node)

                if not isinstance(arr_t, ArrayType):
                    self._err(ctx, "Indexacion sobre un valor no-arreglo")
                    return
                if idx_t != INT:
                    self._err(ctx, "El indice de un arreglo debe ser de tipo integer")
                    return
                if not self._is_assignable(arr_t.elem, rhs_t):
                    self._err(ctx, f"Tipo incompatible en asignacion a elemento de arreglo: se esperaba {arr_t.elem}, se obtuvo {rhs_t}")
                return

           
            rhs_node = exprs[-1] if exprs else None
        else:
            rhs_node = exprs

        rhs_t = self.t(rhs_node) if rhs_node is not None else UNKNOWN

        
        ids = ctx.Identifier()
        if ids:
            name = (ids[0] if isinstance(ids, list) else ids).getText()
            self._maybe_mark_capture(name)
            self._assign_to_name(ctx, name, rhs_t)
            return

        
        if isinstance(exprs, list) and exprs:
            lhs_t = self.t(exprs[0])
            if not self._is_assignable(lhs_t, rhs_t):
                self._err(ctx, f"Tipo incompatible en asignacion: se esperaba {lhs_t}, se obtuvo {rhs_t}")



    def _const_bool_expr(self, expr_ctx):
        try:
            txt = expr_ctx.getText()
            if txt == "true":  return True
            if txt == "false": return False
        except Exception:
            pass
        return None



    def exitAssignExpr(self, ctx):
        rhs_t = self.t(ctx.assignmentExpr())
        lhs = ctx.leftHandSide()
        lhs_text = lhs.getText() if hasattr(lhs, "getText") else ""
        if lhs_text and lhs_text.isidentifier():
            name = lhs_text
            self._maybe_mark_capture(name)
            self._assign_to_name(ctx, name, rhs_t)
            self.set_type(ctx, rhs_t)
            return
        lhs_t = self.t(lhs)
        elem_expected = self._lhs_expected_array_elem(lhs)
        if elem_expected is not None and not self._is_assignable(elem_expected, rhs_t):
            self._err(ctx, f"Tipo incompatible en asignacion a elemento de arreglo: se esperaba {elem_expected}, se obtuvo {rhs_t}.")
        elif not self._is_assignable(lhs_t, rhs_t):
            self._err(ctx, f"Tipo incompatible en asignacion: se esperaba {lhs_t}, se obtuvo {rhs_t}.")
        self.set_type(ctx, rhs_t)


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
        if not self._is_assignable(info.type, rhs_t):
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

       
        parent = getattr(ctx, "parentCtx", None)
        if parent is not None and parent.__class__.__name__ == "SwitchStatementContext":
            if self._switch_types:
                self._switch_types[-1] = self.t(ctx)

   
        if self._switch_expr_nodes and ctx is self._switch_expr_nodes[-1]:
            if self._switch_types:
                self._switch_types[-1] = self.t(ctx)

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
            self._maybe_mark_capture(name)
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
                    # recuperar firma global (cls=None)
                    param_types, ret_t = None, UNKNOWN
                    for (cls, fname), sig in self.funcs.items():
                        if cls is None and fname == base_name:
                            param_types, ret_t = sig
                            break
                    arg_types = [ self.t(e) for e in self._extract_arg_exprs(child) ]
                    if param_types is not None:
                        if len(arg_types) != len(param_types):
                            self._err(child, f"Llamada a '{base_name}' con {len(arg_types)} argumento(s), se esperaban {len(param_types)}.")
                        else:
                            for j, (pt, at) in enumerate(zip(param_types, arg_types), 1):
                                if not self._is_assignable(pt, at):
                                    self._err(child, f"Argumento {j} de '{base_name}' incompatible: se esperaba {pt}, se obtuvo {at}.")
                        curr = ret_t
                    else:
                        curr = UNKNOWN
                else:
                   
                    curr = UNKNOWN

            elif cname == "PropertyAccessExprContext":
                
                if (not isinstance(curr, Type)) or curr in (INT, BOOL, FLT, STR, NULL, UNKNOWN):
                    self._err(child, "Acceso a propiedad sobre un valor no-objeto.")
                    curr = UNKNOWN
                    i += 1
                    continue

                cls_name = curr.name
                prop_text = child.getText()
                member = prop_text[1:] if prop_text.startswith(".") else prop_text
                
                              
                if member == "constructor":
                    next_is_call = (i + 1 < n) and (ctx.getChild(i+1).__class__.__name__ == "CallExprContext")
                    if next_is_call:
                        self._err(child, f"No se puede invocar 'constructor' como metodo de instancia; usa 'new {cls_name}(...)'.")
                        curr = UNKNOWN
                        i += 1  # saltar el CallExpr
                    else:
                        self._err(child, "No se puede usar 'constructor' como valor.")
                        curr = UNKNOWN
                    i += 1
                    continue


                
                next_is_call = (i + 1 < n) and (ctx.getChild(i+1).__class__.__name__ == "CallExprContext")
                if next_is_call:
                    call_node = ctx.getChild(i+1)
                    sig = self._find_method_sig(cls_name, member)
                    if sig is None:
                        self._err(child, f"Metodo '{member}' no existe en clase '{cls_name}'.")
                        curr = UNKNOWN
                    else:
                        param_types, ret_t = sig
                        arg_types = [ self.t(e) for e in self._extract_arg_exprs(call_node) ]
                        if len(arg_types) != len(param_types):
                            self._err(call_node, f"Llamada a metodo '{cls_name}.{member}' con {len(arg_types)} argumento(s), se esperaban {len(param_types)}.")
                        else:
                            for j, (pt, at) in enumerate(zip(param_types, arg_types), 1):
                                if not self._is_assignable(pt, at):
                                    self._err(call_node, f"Argumento {j} de metodo '{cls_name}.{member}' incompatible: {pt} vs {at}.")
                        curr = ret_t
                        i += 1 
                else:
                    
                    ftype = self._lookup_field(cls_name, member)
                    if ftype is not None:
                        curr = ftype
                    else:
                        
                        if self._find_method_sig(cls_name, member) is not None:
                            self._err(child, f"No se puede usar el metodo '{cls_name}.{member}' como valor; invocalo con '()'.")
                        else:
                            self._err(child, f"Atributo '{member}' no existe en clase '{cls_name}'.")
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

            else:
                
                curr = UNKNOWN

            i += 1

        self.set_type(ctx, curr)



    def _type_of_primary_atom(self, atom_ctx) -> TypeLike:
        if atom_ctx is None:
            return UNKNOWN

        cname = atom_ctx.__class__.__name__

        
        if cname == "ThisExprContext":
            if self.class_stack:
                return Type(self.class_stack[-1])
            else:
                self._err(atom_ctx, "Uso de 'this' fuera de una clase.")
                return UNKNOWN

        
        if cname == "NewExprContext":
            tname = atom_ctx.getChild(1).getText()
            arg_types = [ self.t(e) for e in self._extract_arg_exprs(atom_ctx) ]
            sig = self._find_method_sig(tname, "constructor")
            if sig is not None:
                param_types, _ = sig
                if len(arg_types) != len(param_types):
                    self._err(atom_ctx, f"Constructor de '{tname}' espera {len(param_types)} argumento(s), se pasaron {len(arg_types)}.")
                else:
                    for i, (pt, at) in enumerate(zip(param_types, arg_types), 1):
                        if not self._is_assignable(pt, at):
                            self._err(atom_ctx, f"Argumento {i} del constructor de '{tname}' incompatible: {pt} vs {at}.")
            else:
                if len(arg_types) != 0:
                    self._err(atom_ctx, f"La clase '{tname}' no define constructor que acepte {len(arg_types)} argumento(s).")
            return Type(tname)

       
        first = atom_ctx.getChild(0)

        
        try:
            if first.getText() == "(" and atom_ctx.getChildCount() >= 3:
                return self.t(atom_ctx.getChild(1))
        except Exception:
            pass

        
        try:
            name = first.getText()
        except Exception:
            name = ""

        
        if name and name.isidentifier() and name not in ("this", "new", "true", "false", "null"):
            info = self.scopes.resolve(name)
            if info is not None:
                return info.type

        
        return self.t(first)


    def _extract_arg_exprs(self, node):
     
        args_node = None
        
        if hasattr(node, "arguments"):
            try:
                args_node = node.arguments()
            except Exception:
                args_node = None
        if args_node is None:
            for k in range(getattr(node, "getChildCount", lambda:0)()):
                ch = node.getChild(k)
                if ch.__class__.__name__ == "ArgumentsContext":
                    args_node = ch
                    break

        exprs = []
        if args_node:
            e = args_node.expression()
            if isinstance(e, list):
                exprs = e
            elif e is not None:
                exprs = [e]
        return exprs


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

        
        blocks = ctx.block()
        then_b = blocks[0] if isinstance(blocks, list) else blocks
        else_b = blocks[1] if (isinstance(blocks, list) and len(blocks) > 1) else None

        then_ret = self._ret(then_b)
        else_ret = self._ret(else_b) if else_b else False

        cconst = self._const_bool_expr(ctx.expression())

        
        if cconst is True:
            stmt_returns = then_ret
        elif cconst is False:
            stmt_returns = else_ret
        else:
            stmt_returns = (then_ret and else_ret) if else_b else False

       
        self._set_returns(ctx, stmt_returns)

        
        if stmt_returns:
            self._mark_terminator()


    

  

    

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

        if fname == "constructor":
            if ctx.type_():
                pass
            ret_t = VOID
            if not self.class_stack:
                self._err(ctx, "constructor fuera de una clase.")

        current_class = self.class_stack[-1] if self.class_stack else None
        key = (current_class, fname)

        self.func_key_stack.append(key)
        self.func_locals.setdefault(key, set())
        self.func_captures.setdefault(key, set())

        if key in self.funcs:
            self._err(ctx, f"Funcion '{fname}' redeclarada.")
        else:
            # Validaciones de override (igual que ya tienes)
            if current_class is not None and fname != "constructor":
                anc_sig = self._find_method_sig_in_ancestors(current_class, fname)
                if anc_sig is not None:
                    anc_params, anc_ret = anc_sig
                    same_arity = (len(anc_params) == len(param_types))
                    same_params = same_arity and all(type_equals(p, q) for p, q in zip(anc_params, param_types))
                    same_ret = type_equals(anc_ret, ret_t)
                    if not (same_arity and same_params and same_ret):
                        self._err(
                            ctx,
                            f"Override incompatible de metodo '{current_class}.{fname}': "
                            f"se esperaba {self._sig_to_str(anc_params, anc_ret)}, "
                            f"se definio {self._sig_to_str(param_types, ret_t)}."
                        )

            # Construye VarInfo de params (sin offsets manuales)
            params_infos = []
            for p, ptype in zip(params_nodes, param_types):
                id_tok = p.Identifier().getSymbol()
                pname = id_tok.text
                params_infos.append(VarInfo(pname, ptype, False, id_tok))
                # marca para captura
                self.func_locals[key].add(pname)

            # Declara función UNA sola vez
            f_info = FunctionInfo(fname, params_infos, ret_t,
                                  is_method=(self.class_stack != []),
                                  is_constructor=(fname == "constructor"))
            self.symbtab.declare_func(f_info)

            self.symbtab.enter_function(fname)
            self.funcs[key] = ([p.type for p in params_infos], ret_t)

        self.func_ret_stack.append(ret_t)



                
    def _is_global_func(self, name: str) -> bool:
        for (cls, fname) in self.funcs.keys():
            if cls is None and fname == name:
                return True
        return False

    def exitTryCatchStatement(self, ctx):
        
        blocks = ctx.block()
        if not isinstance(blocks, list): blocks = [blocks]
        try_b = blocks[0] if len(blocks) > 0 else None
        catch_b = blocks[1] if len(blocks) > 1 else None
        self._set_returns(ctx, self._ret(try_b) and self._ret(catch_b))
    

    def exitFunctionDeclaration(self, ctx):
        expected = self.func_ret_stack[-1]
        if expected != VOID and expected != UNKNOWN:
            fun_block = ctx.block()
            if not self._ret(fun_block):
                self._err(ctx, f"La funcion '{ctx.Identifier().getText()}' debe retornar {expected} en todos los caminos.")

        self.func_key_stack.pop()

        # Cierra function frame y scope
        self.symbtab.leave_function()



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
            elif not self._is_assignable(expected, expr_t):
                self._err(ctx, f"Tipo de retorno incompatible: se esperaba {expected}, se obtuvo {expr_t}.")
        self._mark_terminator()
        self._set_returns(ctx, True)

   
    def enterWhileStatement(self, ctx):
        self.loop_depth += 1
    def exitWhileStatement(self, ctx):
        self._check_boolean_cond(ctx.expression(), "while")
        self.loop_depth -= 1
        self._set_returns(ctx, False)

    def enterDoWhileStatement(self, ctx):
        self.loop_depth += 1
    def exitDoWhileStatement(self, ctx):
        self._check_boolean_cond(ctx.expression(), "do-while")
        self.loop_depth -= 1
        self._set_returns(ctx, False)

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
        self._set_returns(ctx, False)

    def enterForeachStatement(self, ctx):
        self.loop_depth += 1

    def exitForeachStatement(self, ctx):
        self.loop_depth -= 1
        self._set_returns(ctx, False)
    
    def exitBreakStatement(self, ctx):
        if self.loop_depth == 0 and self.switch_depth == 0:
            self._err(ctx, "'break' solo puede usarse dentro de un bucle o switch.")
        self._mark_terminator()
        self._set_returns(ctx, False)

    def exitContinueStatement(self, ctx):
        if self.loop_depth == 0:
            self._err(ctx, "'continue' solo puede usarse dentro de un bucle.")
        self._mark_terminator()
        self._set_returns(ctx, False)
    
    def enterSwitchStatement(self, ctx):
        self.switch_depth += 1
        sw_expr = ctx.expression() if callable(ctx.expression) else None
        if isinstance(sw_expr, list):
            sw_expr = sw_expr[0] if sw_expr else None
        self._switch_expr_nodes.append(sw_expr)
        self._switch_types.append(UNKNOWN)

    def exitSwitchStatement(self, ctx):
        
        sw_t = self._switch_types[-1] if self._switch_types else UNKNOWN
        if sw_t == UNKNOWN:
            sw_node = self._switch_expr_nodes[-1] if self._switch_expr_nodes else None
            if sw_node is not None:
                sw_t = self.t(sw_node)
                if sw_t == UNKNOWN:
                    txt = getattr(sw_node, "getText", lambda: "")()
                    if txt and txt.isidentifier():
                        info = self.scopes.resolve(txt)
                        if info is not None:
                            sw_t = info.type
                    elif txt.isdigit():
                        sw_t = INT
                    elif len(txt) > 0 and txt[0] == '"':
                        sw_t = STR

        
        self.switch_depth -= 1
        if self._switch_expr_nodes:
            self._switch_expr_nodes.pop()
        if self._switch_types:
            self._switch_types.pop()
        self._set_returns(ctx, False)


        
    def enterStatement(self, ctx):
        self._check_unreachable(ctx)

    def enterClassDeclaration(self, ctx):
        cname = ctx.Identifier(0).getText()

        base = None
        ids = ctx.Identifier()
        if isinstance(ids, list) and len(ids) >= 2:
            base = ids[1].getText()

        self.class_stack.append(cname)
        
        self.class_extends[cname] = base


    def exitClassDeclaration(self, ctx):
        self.class_stack.pop()
        cname = ctx.Identifier(0).getText()
        base = self.class_extends.get(cname)

        fields = {n: VarInfo(n, t, False, None)
                  for n, t in self.class_fields.get(cname, {}).items()}

        methods = {}
        for (cls, fname), (param_types, ret_t) in self.funcs.items():
            if cls == cname:
                params_infos = [VarInfo(f"p{i}", pt, False, None)
                                for i, pt in enumerate(param_types)]
                methods[fname] = FunctionInfo(fname, params_infos, ret_t,
                                              is_method=True,
                                              is_constructor=(fname=="constructor"))

        c_info = ClassInfo(cname, base, fields, methods)
        self.symbtab.declare_class(c_info)

        
    def _lookup_field(self, cls_name: str, member: str) -> Optional[TypeLike]:
        cur = cls_name
        while cur is not None:
            fields = self.class_fields.get(cur, {})
            if member in fields:
                return fields[member]
            cur = self.class_extends.get(cur)
        return None

    def _find_method_sig(self, cls_name: str, method: str) -> Optional[tuple[list[TypeLike], TypeLike]]:
        cur = cls_name
        while cur is not None:
            key = (cur, method)
            if key in self.funcs:
                return self.funcs[key]
            cur = self.class_extends.get(cur)
        return None

    def _set_returns(self, node, val: bool):
        self.returns[node] = bool(val)
    
    def _ret(self, node) -> bool:
        return bool(self.returns.get(node, False))
    
    def exitStatement(self, ctx):
        
        child = None
        
        for getter in (
            "returnStatement", "ifStatement", "block",
            "tryCatchStatement", "whileStatement",
            "doWhileStatement", "forStatement",
            "switchStatement", "expressionStatement",
            "assignment", "variableDeclaration",
            "constantDeclaration", "printStatement",
            "breakStatement", "continueStatement",
            "functionDeclaration", "classDeclaration",
            "foreachStatement",
        ):
            if hasattr(ctx, getter) and getattr(ctx, getter)():
                child = getattr(ctx, getter)()
                break
        self._set_returns(ctx, self._ret(child))
        
    
    def _check_property_assignment(self, ctx, obj_t: TypeLike, member: str, rhs_t: TypeLike):
        
        if (not isinstance(obj_t, Type)) or obj_t in (INT, BOOL, FLT, STR, NULL, UNKNOWN) or isinstance(obj_t, ArrayType):
            self._err(ctx, "Asignacion a propiedad sobre un valor no-objeto.")
            return
        cls = obj_t.name

        
        ftype = self._lookup_field(cls, member)
        if ftype is not None:
            if not self._is_assignable(ftype, rhs_t):
                self._err(ctx, f"Tipo incompatible en asignacion a '{cls}.{member}': se esperaba {ftype}, se obtuvo {rhs_t}.")
            return

       
        if self._find_method_sig(cls, member) is not None:
            self._err(ctx, f"No se puede asignar al metodo '{cls}.{member}'.")
            return

        
        self._err(ctx, f"Atributo '{member}' no existe en clase '{cls}'.")

    def exitPropertyAssignExpr(self, ctx):
        obj_t = self.t(ctx.lhs)
        member = ctx.Identifier().getText()
        rhs_t = self.t(ctx.assignmentExpr())
        self._check_property_assignment(ctx, obj_t, member, rhs_t)
       
        self.set_type(ctx, rhs_t)
        
    # -- Helpers de tipado subtipado ---  
        
    def _is_assignable(self, expected: TypeLike, got: TypeLike) -> bool:
      
        if is_assignable(expected, got):
            return True
        # subtipado derivada -> base
        if isinstance(expected, Type) and isinstance(got, Type):
            cur = got.name
            while cur is not None:
                if cur == expected.name:
                    return True
                cur = self.class_extends.get(cur)
        return False

    def _find_method_sig_in_ancestors(self, cls_name: str, method: str) -> Optional[tuple[list[TypeLike], TypeLike]]:
        base = self.class_extends.get(cls_name)
        while base is not None:
            sig = self.funcs.get((base, method))
            if sig is not None:
                return sig
            base = self.class_extends.get(base)
        return None

    def _sig_to_str(self, params: list[TypeLike], ret: TypeLike) -> str:
        ps = ", ".join(str(p) for p in params)
        return f"({ps}) -> {ret}"
    
    
    def exitSwitchCase(self, ctx):
       
        if not self._switch_expr_nodes:
            return

        
        sw_t = self._switch_types[-1] if self._switch_types else UNKNOWN
        if sw_t == UNKNOWN:
            sw_node = self._switch_expr_nodes[-1]
            tmp = self.t(sw_node) if sw_node is not None else UNKNOWN
            if tmp != UNKNOWN:
                sw_t = tmp
            else:
                try:
                    txt = sw_node.getText() if sw_node is not None else ""
                    info = self.scopes.resolve(txt) if txt.isidentifier() else None
                    if info is not None:
                        sw_t = info.type
                    elif txt.isdigit():
                        sw_t = INT
                    elif len(txt) > 0 and txt[0] == '"':
                        sw_t = STR
                except Exception:
                    pass

        
        ce = ctx.expression() if callable(getattr(ctx, "expression", None)) else None
        if isinstance(ce, list):
            ce = ce[0] if ce else None
        ct = self.t(ce) if ce is not None else UNKNOWN

        
        if ct == UNKNOWN:
            try:
                lit = ctx.getChild(1).getText() 
                if lit and len(lit) > 0 and lit[0] == '"':
                    ct = STR
                elif lit.isdigit():
                    ct = INT
            except Exception:
                pass

        if not are_eq_comparable(sw_t, ct):
            self._err(ce or ctx, f"Tipo de 'case' incompatible con 'switch' ({sw_t} vs {ct})")

    def _maybe_mark_capture(self, name: str):
        
        if not self.func_key_stack:
            return
        cur_key = self.func_key_stack[-1]
        
        if name in self.func_locals.get(cur_key, set()):
            return
        
        for outer_key in reversed(self.func_key_stack[:-1]):
            if name in self.func_locals.get(outer_key, set()):
                self.func_captures.setdefault(cur_key, set()).add(name)
                return
      
    def _lhs_expected_array_elem(self, lhs_ctx):
        curr = self._type_of_primary_atom(lhs_ctx.primaryAtom())
        i = 1
        while i < lhs_ctx.getChildCount():
            ch = lhs_ctx.getChild(i)
            nm = ch.__class__.__name__
            if nm == "PropertyAccessExprContext":
                member = ch.getText()[1:]
                if isinstance(curr, Type):
                    ftype = self._lookup_field(curr.name, member)
                    if ftype is not None:
                        curr = ftype
                    else:
                        sig = self._find_method_sig(curr.name, member)
                        curr = sig[1] if sig else UNKNOWN
                else:
                    curr = UNKNOWN
            elif nm == "IndexExprContext":
                if isinstance(curr, ArrayType):
                    return curr.elem
                else:
                    return None
            elif nm == "CallExprContext":
                curr = UNKNOWN
            i += 1
        return None