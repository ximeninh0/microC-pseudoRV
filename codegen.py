"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ir import Context, ProgramIR, FunctionIR, Param


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
            
        # chamar statement?
        
        raise NotImplementedError("implemente CodeGenerator.generate")

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        raise NotImplementedError("implemente seleção e emissão")

    def statement(self, node):
        """Traduza um comando ad hoc."""
        raise NotImplementedError("implemente comandos")
