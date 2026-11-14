"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ast_nodes import (
    Block, VarDecl, Assignment, CallStmt, IfStmt,
    WhileStmt, ReturnStmt, PrintStmt, StringLiteral, TypeName,
)
from ir import (
    Move, Return, Jump, LabelInstr,
    PrintInt, PrintBool, PrintString,
    ProgramIR, FunctionIR, Context, Param
)
from patterns import REG, COND, EFFECT

class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        program_ir = ProgramIR()

        for function in program.functions:
            symbol = function.metadata["symbol"] # simbolo anotado antes

            function_ir = FunctionIR(symbol)
            program_ir.functions.append(function_ir)

            self.ctx = Context(function_ir,program_ir) # contexto que vai pra stat. e expr.

            for index, param in enumerate(function.parameters):
                virtualReg = self.ctx.variable(param.metadata["symbol"])
                self.ctx.emit(Param(virtualReg,index,origin=param.span))
            
            self.statement(function.body)


        raise NotImplementedError("implemente CodeGenerator.generate")

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        raise NotImplementedError("implemente seleção e emissão")

    def statement(self, node):
        """Traduza um comando ad hoc."""
        ctx = self.ctx

        if isinstance(node, Block):
            for stmt in node.statements:
                self.statement(stmt)

        #int x = algo;
        elif isinstance(node, VarDecl):
            if node.initializer is not None: #só int x;?
                value = self.expression(node.initializer, REG)
                var = ctx.variable(node.metadata["symbol"])
                ctx.emit(Move(var,value,origin=node.span)) # linha no assembly mv var, value

        # x = algo;
        elif isinstance(node,Assignment):
            value = self.expression(node.value, REG)
            var = ctx.variable(node.target.metadata["symbol"])
            ctx.emit(Move(var, value, origin=node.span)) # linha no assembly mv var, value

        # função(algo);
        elif isinstance(node, CallStmt):
            self.expression(node.call, EFFECT)

        # if (algo) {} else {}
        elif isinstance(node, IfStmt):
            l_then = ctx.label()
            l_end = ctx.label()
            if node.else_block is not None: # tem é if {} else {}
                l_else = ctx.label()
                self.expression(node.condition, COND, true_label=l_then, false_label=l_else)

                ctx.emit(LabelInstr(l_then)) # label do if no assembly
                self.statement(node.then_block)
                ctx.emit(Jump(l_end)) # jump para não else

                ctx.emit(LabelInstr(l_else)) # label do else no assembly
                self.statement(node.else_block)
            else: #é só if {}
                self.expression(node.condition, COND, true_label=l_then, false_label=l_end)

                ctx.emit(LabelInstr(l_then)) # label do if no assembly
                self.statement(node.then_block)

            ctx.emit(LabelInstr(l_end)) # label do fim do if no assembly

        # while (algo) {}
        elif isinstance(node, WhileStmt):
            l_test = ctx.label()
            l_body = ctx.label()
            l_end = ctx.label()

            ctx.emit(LabelInstr(l_test)) # label do while no assembly
            self.expression(node.condition, COND, true_label=l_body, false_label=l_end)

            ctx.emit(LabelInstr(l_body)) # label do body do while no assembly
            self.statement(node.body)
            ctx.emit(Jump(l_test)) # jump para o teste do while

            ctx.emit(LabelInstr(l_end)) # label do fim do while no assembly

        # return;
        elif isinstance(node, ReturnStmt):
            if node.value is None:
                ctx.emit(Return(None, origin=node.span)) 
            else: # return expr;
                value = self.expression(node.value, REG)
                ctx.emit(Return(value, origin=node.span)) 

        # print(algo, algo, ...);
        elif isinstance(node, PrintStmt):
            for item in node.items:                      
                if isinstance(item, StringLiteral):
                    ctx.emit(PrintString(ctx.string(item.value), origin=item.span)) # linha do assembly para o print (string)
                else:
                    value = self.expression(item, REG)
                    if item.metadata["type"] == TypeName.BOOL:
                        ctx.emit(PrintBool(value, origin=item.span)) # linha do assembly para o print (bool)
                    else:
                        ctx.emit(PrintInt(value, origin=item.span)) # linha do assembly para o print (int)
            ctx.emit(PrintString(ctx.string("\n")))      # precisa quebrar a string

        else:
            raise TypeError(f"comando desconhecido: {type(node).__name__}")