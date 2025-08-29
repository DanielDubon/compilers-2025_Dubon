from CompiscriptVisitor import CompiscriptVisitor
from CompiscriptParser import CompiscriptParser
from antlr4 import ParserRuleContext
from typing import List, Optional
import ast_nodes as A

def pos(ctx: ParserRuleContext):
    t = ctx.start if hasattr(ctx, "start") else None
    line = getattr(t, "line", 0) or 0
    col  = getattr(t, "column", 0) or 0
    return line, col

class AstBuilder(CompiscriptVisitor):

  
    def visitProgram(self, ctx: CompiscriptParser.ProgramContext) -> A.Program:
        line, col = pos(ctx)
        decls: List[A.Decl] = []
        for ch in ctx.children[:-1]:  
            node = self.visit(ch)
            if node is None: 
                continue
            if isinstance(node, list): 
                decls.extend(d for d in node if isinstance(d, A.Decl))
            elif isinstance(node, A.Decl):
                decls.append(node)
        return A.Program(line, col, decls)

  
    def visitVariableDeclaration(self, ctx):
        line, col = pos(ctx)
        kind = "let" if ctx.getChild(0).getText() == "let" else "var"
        name = ctx.Identifier().getText()
        type_ref = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
        init = self.visit(ctx.initializer().expression()) if ctx.initializer() else None
        return A.VarDecl(line, col, name, type_ref, init, kind)


    def visitConstantDeclaration(self, ctx):
        line, col = pos(ctx)
        name = ctx.Identifier().getText()
        type_ref = self.visit(ctx.typeAnnotation().type_()) if ctx.typeAnnotation() else None
        init = self.visit(ctx.initializer().expression()) if ctx.initializer() else None
        return A.VarDecl(line, col, name, type_ref, init, "const")


    def visitType_(self, ctx):
        base = self.visit(ctx.baseType())
        dims = sum(1 for i in range(1, ctx.getChildCount()) if ctx.getChild(i).getText() == "[")
        line, col = pos(ctx)
        t: A.TypeRef = base
        for _ in range(dims):
            t = A.ArrayTypeRef(line, col, t)
        return t

    def visitBaseType(self, ctx):
        line, col = pos(ctx)
        return A.SimpleType(line, col, ctx.getText())


    def visitFunctionDeclaration(self, ctx):
        line, col = pos(ctx)
        name = ctx.Identifier().getText()
        params_ctx = ctx.parameters().parameter() if ctx.parameters() else []
        params = []
        for p in params_ctx:
            pl, pc = pos(p)
            pname = p.Identifier().getText()
            ptype = self.visit(p.type_()) if p.type_() else None
            params.append(A.Param(pl, pc, pname, ptype))
        ret = self.visit(ctx.type_()) if ctx.type_() else None
        body = self.visit(ctx.block())
        return A.FunctionDecl(line, col, name, params, ret, body)


    def visitClassDeclaration(self, ctx):
        line, col = pos(ctx)
        name = ctx.Identifier(0).getText()
        base = ctx.Identifier(1).getText() if len(ctx.Identifier()) > 1 else None
        fields: List[A.VarDecl] = []
        methods: List[A.FunctionDecl] = []
        for m in ctx.classMember():
            node = self.visit(m)
            if isinstance(node, A.VarDecl):
                fields.append(node)
            elif isinstance(node, A.FunctionDecl):
                node.is_method = True
                node.is_constructor = (node.name == "constructor")
                methods.append(node)
        return A.ClassDecl(line, col, name, base, fields, methods)


    def visitClassMember(self, ctx):
        for ch in ctx.getChildren():
            n = self.visit(ch)
            if n: return n


    def visitBlock(self, ctx):
        line, col = pos(ctx)
        stmts = []
        for s in ctx.statement():
            n = self.visit(s)
            if n is not None:
                if isinstance(n, list):
                    stmts.extend(n)
                else:
                    stmts.append(n)
        return A.Block(line, col, stmts)

    def visitStatement(self, ctx):
        for getter in (
            ctx.returnStatement, ctx.ifStatement, ctx.whileStatement, ctx.doWhileStatement,
            ctx.forStatement, ctx.foreachStatement, ctx.switchStatement, ctx.tryCatchStatement,
            ctx.breakStatement, ctx.continueStatement, ctx.block, ctx.expressionStatement,
            ctx.assignment, ctx.variableDeclaration, ctx.constantDeclaration, ctx.functionDeclaration,
            ctx.classDeclaration,
        ):
            if getter():
                return self.visit(getter())


    def visitIfStatement(self, ctx):
        line, col = pos(ctx)
        cond = self.visit(ctx.expression())
        blocks = ctx.block()
        then_b = self.visit(blocks[0] if isinstance(blocks, list) else blocks)
        else_b = self.visit(blocks[1]) if isinstance(blocks, list) and len(blocks) > 1 else None
        return A.If(line, col, cond, then_b, else_b)


    def visitWhileStatement(self, ctx):
        line, col = pos(ctx)
        return A.While(line, col, self.visit(ctx.expression()), self.visit(ctx.block()))

    def visitDoWhileStatement(self, ctx):
        line, col = pos(ctx)
        return A.DoWhile(line, col, self.visit(ctx.block()), self.visit(ctx.expression()))

    def visitForStatement(self, ctx):
        line, col = pos(ctx)
       
        init = self.visit(ctx.forInit()) if hasattr(ctx, "forInit") and ctx.forInit() else None
        cond = self.visit(ctx.forCond) if hasattr(ctx, "forCond") else None
        update = self.visit(ctx.forUpdate) if hasattr(ctx, "forUpdate") else None
        body = self.visit(ctx.block())
        return A.For(line, col, init, cond, update, body)

    def visitForeachStatement(self, ctx):
        line, col = pos(ctx)
        name = ctx.Identifier().getText()
        seq = self.visit(ctx.expression())
        body = self.visit(ctx.block())
        return A.Foreach(line, col, name, None, seq, body)


    
    def visitSwitchStatement(self, ctx):
        line, col = pos(ctx)
        expr = self.visit(ctx.expression())
        cases = []
        for c in ctx.switchCase():
            cl, cc = pos(c)
            ce = self.visit(c.expression())
            body_stmts = []
            if hasattr(c, "statement"):
                for s in c.statement():
                    n = self.visit(s)
                    if n is not None:
                        if isinstance(n, list):
                            body_stmts.extend(n)
                        else:
                            body_stmts.append(n)
            cb = A.Block(cl, cc, body_stmts)
            cases.append(A.SwitchCase(cl, cc, ce, cb))
        default_b = None
        if ctx.defaultCase():
            dc = ctx.defaultCase()
            dl, dc_col = pos(dc)
            d_stmts = []
            if hasattr(dc, "statement"):
                for s in dc.statement():
                    n = self.visit(s)
                    if n is not None:
                        if isinstance(n, list):
                            d_stmts.extend(n)
                        else:
                            d_stmts.append(n)
            default_b = A.Block(dl, dc_col, d_stmts)
        return A.Switch(line, col, expr, cases, default_b)


    def visitBreakStatement(self, ctx):
        line, col = pos(ctx)
        return A.Break(line, col)

    def visitContinueStatement(self, ctx):
        line, col = pos(ctx)
        return A.Continue(line, col)

    def visitReturnStatement(self, ctx):
        line, col = pos(ctx)
        e = self.visit(ctx.expression()) if ctx.expression() else None
        return A.Return(line, col, e)

    def visitExpressionStatement(self, ctx):
        e = self.visit(ctx.expression())
        line, col = pos(ctx)
        return A.ExprStmt(line, col, e)

  
    def visitAssignment(self, ctx):
        line, col = pos(ctx)
        exprs = ctx.expression()
        ids = ctx.Identifier()
        if len(exprs) == 2 and ids:
            obj = self.visit(exprs[0])
            member = ids.getText() if hasattr(ids, "getText") else ids[0].getText()
            value = self.visit(exprs[1])
            return A.Assign(line, col, A.Member(line, col, obj, member), value)
        if len(exprs) == 3: 
            arr = self.visit(exprs[0]); idx = self.visit(exprs[1]); val = self.visit(exprs[2])
            return A.Assign(line, col, A.Index(line, col, arr, idx), val)
        if ids:
            name = (ids[0] if isinstance(ids, list) else ids).getText()
            value = self.visit(exprs[-1])
            return A.Assign(line, col, A.Name(line, col, name), value)
       
        return A.ExprStmt(line, col, self.visit(exprs[-1]))

    # ----- expresiones -----

  
    def visitTernaryExpr(self, ctx):
        if ctx.getChildCount() == 1:
            return self.visit(ctx.getChild(0))
        line, col = pos(ctx)
        cond = self.visit(ctx.getChild(0))
        then = self.visit(ctx.getChild(2))
        other = self.visit(ctx.getChild(4))
        return A.Ternary(line, col, cond, then, other)

    def visitAdditiveExpr(self, ctx):
      
        node = self.visit(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            rhs = self.visit(ctx.getChild(i+1))
            l, c = pos(ctx.getChild(i))
            node = A.Binary(l, c, op, node, rhs)
            i += 2
        return node

    def visitMultiplicativeExpr(self, ctx):
        node = self.visit(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            rhs = self.visit(ctx.getChild(i+1))
            l, c = pos(ctx.getChild(i))
            node = A.Binary(l, c, op, node, rhs)
            i += 2
        return node

    def visitLogicalAndExpr(self, ctx):
        node = self.visit(ctx.getChild(0))
        i = 1
        while i < ctx.getChildCount():
            op = ctx.getChild(i).getText()
            rhs = self.visit(ctx.getChild(i+1))
            l, c = pos(ctx.getChild(i))
            node = A.Binary(l, c, op, node, rhs)
            i += 2
        return node

    def visitUnaryExpr(self, ctx):
        if ctx.getChildCount() == 2:
            l, c = pos(ctx.getChild(0))
            op = ctx.getChild(0).getText()
            return A.Unary(l, c, op, self.visit(ctx.getChild(1)))
        return self.visit(ctx.getChild(0))

    def visitPrimaryExpr(self, ctx):
        if ctx.literalExpr():     return self.visit(ctx.literalExpr())
        if ctx.leftHandSide():    return self.visit(ctx.leftHandSide())
        return self.visit(ctx.expression())

    def visitLeftHandSide(self, ctx):
        node = self._visitPrimaryAtom(ctx.primaryAtom())
        i = 1
        while i < ctx.getChildCount():
            ch = ctx.getChild(i)
            nm = ch.__class__.__name__
            l, c = pos(ch)
            if nm == "CallExprContext":
                args = self._visitArgs(ch)
                node = A.Call(l, c, node, args)
            elif nm == "PropertyAccessExprContext":
                name = ch.getText()[1:]
                node = A.Member(l, c, node, name)
            elif nm == "IndexExprContext":
                idx_expr = ch.expression()
                idx = self.visit(idx_expr[0] if isinstance(idx_expr, list) else idx_expr)
                node = A.Index(l, c, node, idx)
            i += 1
        return node

    def _visitPrimaryAtom(self, atom):
        nm = atom.__class__.__name__
        l, c = pos(atom)
        if nm == "ThisExprContext":   return A.Name(l, c, "this")
        if nm == "NewExprContext":
            cname = atom.getChild(1).getText()
            args = self._visitArgs(atom)
            return A.New(l, c, cname, args)
        if atom.getChild(0).getText() == "(":
            return self.visit(atom.getChild(1))
      
        first = atom.getChild(0)
        if first.getText().isidentifier():
            return A.Name(l, c, first.getText())
        return self.visit(first)

    def _visitArgs(self, node):
        args_node = None
        if hasattr(node, "arguments") and node.arguments():
            args_node = node.arguments()
        else:
            for k in range(node.getChildCount()):
                ch = node.getChild(k)
                if ch.__class__.__name__ == "ArgumentsContext":
                    args_node = ch; break
        if not args_node: return []
        exprs = args_node.expression()
        if isinstance(exprs, list):
            return [self.visit(e) for e in exprs]
        return [self.visit(exprs)] if exprs else []

   
    def visitLiteralExpr(self, ctx):
        l, c = pos(ctx)
        t = ctx.getText()
        if ctx.arrayLiteral():
            elems = []
            for e in (ctx.arrayLiteral().expression() or []):
                elems.append(self.visit(e))
            return A.ArrayLiteral(l, c, elems)
        if t == "true":  return A.LiteralBool(l, c, True)
        if t == "false": return A.LiteralBool(l, c, False)
        if t == "null":  return A.LiteralNull(l, c)
        if len(t) > 0 and t[0] == '"': return A.LiteralString(l, c, t[1:-1])
       
        if any(ch in t for ch in ".eE"):
            return A.LiteralFloat(l, c, float(t))
        return A.LiteralInt(l, c, int(t))

    def visitTryCatchStatement(self, ctx):
        line, col = pos(ctx)
        blocks = ctx.block()
        if isinstance(blocks, list):
            try_ctx = blocks[0] if len(blocks) > 0 else None
            catch_ctx = blocks[1] if len(blocks) > 1 else None
        else:
            try_ctx = blocks
            catch_ctx = None
        try_b = self.visit(try_ctx) if try_ctx is not None else A.Block(line, col, [])
        catch_b = self.visit(catch_ctx) if catch_ctx is not None else A.Block(line, col, [])
        err_name = ctx.Identifier().getText() if ctx.Identifier() else "err"
        return A.TryCatch(line, col, try_b, err_name, catch_b)
