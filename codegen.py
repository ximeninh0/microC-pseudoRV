"""Pontos de implementação da geração de comandos e expressões."""

import load_previous
from ast_nodes import (
    Block, VarDecl, Assignment, CallStmt, IfStmt,
    WhileStmt, ReturnStmt, PrintStmt, StringLiteral, TypeName,
    BinaryOperator,
)
from ir import (
    Move, Return, Jump, LabelInstr,
    PrintInt, PrintBool, PrintString,
    ProgramIR, FunctionIR, Context, Param,
    Add, Sub, Mul, Div, Rem, Neg, Addi, Slli, Call, Li,
)
from patterns import REG, COND, EFFECT, signed_literal
from selector import Selector
from catalogue import catalogue


class CodeGenerator:
    """Coordene comandos ad hoc e seleção de expressões com DP."""

    def __init__(self):
        # instancia o seletor com o catalogo de regras declarativas
        self.selector = Selector(catalogue())

    def generate(self, program):
        """Traduza funções e comandos. Selecione expressões com DP."""
        # cria o container principal da ir do programa
        program_ir = ProgramIR()

        # percorre todas as funcoes definidas no programa
        for function in program.functions:
            symbol = function.metadata["symbol"] # simbolo anotado antes

            # cria a estrutura ir da funcao atual
            function_ir = FunctionIR(symbol)
            program_ir.functions.append(function_ir)

            # contexto que gerencia vregs, labels e pool de strings
            self.ctx = Context(function_ir, program_ir)

            # mapeia cada parametro para seu vreg e emite param
            for index, param in enumerate(function.parameters):
                virtualReg = self.ctx.variable(param.metadata["symbol"])
                self.ctx.emit(Param(virtualReg, index, origin=param.span))
            
            # traduz todos os comandos do corpo da funcao
            self.statement(function.body)

            # garante instrucao de retorno no fim de funcao void caso nao tenha
            if function.return_type == TypeName.VOID:
                if not (function_ir.instructions and isinstance(function_ir.instructions[-1], Return)):
                    self.ctx.emit(Return(None))

        return program_ir

    def expression(self, node, result_class, true_label=None, false_label=None):
        """Selecione e reconstrua uma expressão, preservando curto-circuito."""
        # calcula custos e melhores escolhas por dp bottom-up
        table = self.selector.analyze(node)

        # busca a escolha otima para o no e a classe exigida
        choice = table.lookup(node, result_class)
        if choice is None:
            raise RuntimeError(f"sem cobertura para {result_class} em {node.span}")

        # chama dinamicamente o metodo correspondente a acao da regra
        action = getattr(self, choice.rule.action)
        return action(node, choice, true_label, false_label)

    # acoes emissoras para literais e variaveis
    def emit_li_inteiro(self, node, choice, true_label=None, false_label=None):
        # carrega inteiro ou inteiro com menos unario usando li
        val = signed_literal(node)
        dst = self.ctx.temp()
        self.ctx.emit(Li(dst, val, origin=node.span))
        return dst

    def emit_li_bool(self, node, choice, true_label=None, false_label=None):
        # converte booleano para valor numerico 0 ou 1 e carrega com li
        val = 1 if node.value else 0
        dst = self.ctx.temp()
        self.ctx.emit(Li(dst, val, origin=node.span))
        return dst

    def emit_id(self, node, choice, true_label=None, false_label=None):
        # reutiliza o vreg ja associado a variavel sem emitir instrucoes
        return self.ctx.variable(node.metadata["symbol"])

    def emit_imm12(self, node, choice, true_label=None, false_label=None):
        # reconhece literal imediato sem emitir instrucoes
        return signed_literal(node)

    def emit_pow2(self, node, choice, true_label=None, false_label=None):
        # calcula o expoente k de deslocamento para potencias de dois
        val = signed_literal(node)
        return val.bit_length() - 1

    # acoes emissoras para operacoes aritmeticas em reg
    def emit_neg(self, node, choice, true_label=None, false_label=None):
        # nega o valor do registrador preservando 64 bits
        src = self.expression(choice.subproblems[0][0], REG)
        dst = self.ctx.temp()
        self.ctx.emit(Neg(dst, src, origin=node.span))
        return dst

    def emit_arit_reg(self, node, choice, true_label=None, false_label=None):
        # avalia ambos os operandos em reg na ordem da fonte
        lhs = self.expression(choice.subproblems[0][0], REG)
        rhs = self.expression(choice.subproblems[1][0], REG)
        dst = self.ctx.temp()

        # mapa de operadores aritmeticos para instrucoes da ir
        op_map = {
            BinaryOperator.ADD: Add,
            BinaryOperator.SUBTRACT: Sub,
            BinaryOperator.MULTIPLY: Mul,
            BinaryOperator.DIVIDE: Div,
            BinaryOperator.REMAINDER: Rem,
        }
        instr_cls = op_map[node.operator]
        self.ctx.emit(instr_cls(dst, lhs, rhs, origin=node.span))
        return dst

    def emit_soma_imediato_direita(self, node, choice, true_label=None, false_label=None):
        # soma registrador com literal imediato a direita
        src = self.expression(choice.subproblems[0][0], REG)
        imm = signed_literal(choice.subproblems[1][0])
        dst = self.ctx.temp()
        self.ctx.emit(Addi(dst, src, imm, origin=node.span))
        return dst

    def emit_soma_imediato_esquerda(self, node, choice, true_label=None, false_label=None):
        # soma literal imediato a esquerda com registrador
        imm = signed_literal(choice.subproblems[0][0])
        src = self.expression(choice.subproblems[1][0], REG)
        dst = self.ctx.temp()
        self.ctx.emit(Addi(dst, src, imm, origin=node.span))
        return dst

    def emit_sub_imediato(self, node, choice, true_label=None, false_label=None):
        # subtracao x - c eh convertida em soma com o oposto -c usando addi
        src = self.expression(node.left, REG)
        c = signed_literal(node.right)
        dst = self.ctx.temp()
        self.ctx.emit(Addi(dst, src, -c, origin=node.span))
        return dst

    def emit_mul_pow2_direita(self, node, choice, true_label=None, false_label=None):
        # multiplicacao por potencia de dois a direita vira deslocamento a esquerda
        src = self.expression(choice.subproblems[0][0], REG)
        k = signed_literal(choice.subproblems[1][0]).bit_length() - 1
        dst = self.ctx.temp()
        self.ctx.emit(Slli(dst, src, k, origin=node.span))
        return dst

    def emit_mul_pow2_esquerda(self, node, choice, true_label=None, false_label=None):
        # multiplicacao por potencia de dois a esquerda vira deslocamento a esquerda
        k = signed_literal(choice.subproblems[0][0]).bit_length() - 1
        src = self.expression(choice.subproblems[1][0], REG)
        dst = self.ctx.temp()
        self.ctx.emit(Slli(dst, src, k, origin=node.span))
        return dst

    # acoes emissoras para chamadas de funcao
    def emit_call_reg(self, node, choice, true_label=None, false_label=None):
        # avalia argumentos da esquerda para a direita em reg
        func_sym = node.metadata["symbol"]
        args = [self.expression(arg, REG) for arg in node.arguments]
        dst = self.ctx.temp()
        self.ctx.emit(Call(dst, func_sym, args, origin=node.span))
        return dst

    def emit_call_effect(self, node, choice, true_label=None, false_label=None):
        # chamada executada apenas por seus efeitos colaterais
        func_sym = node.metadata["symbol"]
        args = [self.expression(arg, REG) for arg in node.arguments]
        self.ctx.emit(Call(None, func_sym, args, origin=node.span))
        return None

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
