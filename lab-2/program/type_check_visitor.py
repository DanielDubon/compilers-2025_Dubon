from SimpleLangParser import SimpleLangParser
from SimpleLangVisitor import SimpleLangVisitor
from custom_types import IntType, FloatType, StringType, BoolType

class TypeCheckVisitor(SimpleLangVisitor):

  def visitMulDiv(self, ctx: SimpleLangParser.MulDivContext):
    left_type = self.visit(ctx.expr(0))
    right_type = self.visit(ctx.expr(1))
    
    if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
        return FloatType() if isinstance(left_type, FloatType) or isinstance(right_type, FloatType) else IntType()
    else:
        raise TypeError("Unsupported operand types for * or /: {} and {}".format(left_type, right_type))

  def visitAddSub(self, ctx: SimpleLangParser.AddSubContext):
    print("TEST Add")
    left_type = self.visit(ctx.expr(0))
    right_type = self.visit(ctx.expr(1))
    
    if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type, (IntType, FloatType)):
        return FloatType() if isinstance(left_type, FloatType) or isinstance(right_type, FloatType) else IntType()
    else:
        raise TypeError("Unsupported operand types for + or -: {} and {}".format(left_type, right_type))
      
# Added for comparision < >
  def visitComp(self, ctx: SimpleLangParser.CompContext):
    print("TEST")
    left_type = self.visit(ctx.expr(0))
    right_type = self.visit(ctx.expr(1))
    
    if isinstance(left_type, (IntType, FloatType)) and isinstance(right_type,(IntType, FloatType)):
      return BoolType() if isinstance(left_type, FloatType) or isinstance(right_type, FloatType) else BoolType()
    else: 
        raise TypeError("Unsupported operand types for < or >: {} and {}".format(left_type, right_type))
    
# Added for Mod %
  def visitMod(self, ctx: SimpleLangParser.ModContext):
    print("TEST VISITOR")
    left_type = self.visit(ctx.expr(0))
    right_type = self.visit(ctx.expr(1))
    
    if isinstance(left_type, IntType) and isinstance(right_type,IntType):
      return IntType() if isinstance(left_type, IntType) or isinstance(right_type, IntType) else IntType()
    else: 
        raise TypeError("Unsupported operand types for % : {} and {}".format(left_type, right_type))
  
  def visitInt(self, ctx: SimpleLangParser.IntContext):
    return IntType()

  def visitFloat(self, ctx: SimpleLangParser.FloatContext):
    return FloatType()

  def visitString(self, ctx: SimpleLangParser.StringContext):
    return StringType()

  def visitBool(self, ctx: SimpleLangParser.BoolContext):
    return BoolType()

  def visitParens(self, ctx: SimpleLangParser.ParensContext):
    return self.visit(ctx.expr())
  

  def visitProg(self, ctx: SimpleLangParser.ProgContext):
    for stat in ctx.stat():
        self.visit(stat)

  def visitStat(self, ctx: SimpleLangParser.StatContext):
    return self.visit(ctx.expr())
