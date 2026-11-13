"""Ponto de implementação das regras declarativas do enunciado."""
import load_previous
from patterns import (
    Pattern, Rule, Need, Args,
    REG, COND, IMM12, POW2, EFFECT,
    signed_literal, imm12, pow2, neg_imm12,
)
from ast_nodes import (
    BinaryExpr, BinaryOperator, UnaryExpr, UnaryOperator,
    BoolLiteral, IdentifierExpr, CallExpr, TypeName,
)


def li_int(node):
    return signed_literal(node) is not None


def is_bool(node):
    return node.metadata.get("type") == TypeName.BOOL


def has_value(node):
    # Chamadas void não recebem anotação de tipo na semântica.
    return node.metadata.get("type") in (TypeName.INT, TypeName.BOOL)


def catalogue():
    """Codifique o catálogo do enunciado com Rule e Pattern."""

    return [
        # Literal inteiro com sinal ou bool para REG, com Li 1
        Rule(
            name="li_int",
            result=REG,
            pattern=Pattern(predicate=li_int),
            cost=1,
            action="emit_li_inteiro",
        ),
        Rule(
            name="li_bool",
            result=REG,
            pattern=Pattern(BoolLiteral),
            cost=1,
            action="emit_li_bool",
        ),

        # Identificador para REG, reutilizando o VReg do símbolo. 0
        Rule(
            name="ID",
            result=REG,
            pattern=Pattern(IdentifierExpr),
            cost=0,
            action="emit_id",
        ),

        # Literal elegível para IMM12 ou POW2, sem instrução. 0
        Rule(
            name="ID_imm12",
            result=IMM12,
            pattern=Pattern(predicate=imm12),
            cost=0,
            action="emit_imm12",
        ),

        # Literal elegível para IMM12 ou POW2, sem instrução. 0
        Rule(
            name="ID_pow2",
            result=POW2,
            pattern=Pattern(predicate=pow2),
            cost=0,
            action="emit_pow2",
        ),

        # Negação aritmética de REG para REG, com Neg. 1
        Rule(
            name="neg_reg",
            result=REG,
            pattern=Pattern(UnaryExpr, UnaryOperator.NEGATE, (Need(REG),)),
            cost=1,
            action="emit_neg",
        ),

        # Aritmética geral de dois REG para REG 1
        Rule(
            name="soma_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.ADD, (Need(REG), Need(REG))),
            cost=1,
            action="emit_arit_reg",
        ),
        Rule(
            name="sub_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.SUBTRACT, (Need(REG), Need(REG))),
            cost=1,
            action="emit_arit_reg",
        ),
        Rule(
            name="mul_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.MULTIPLY, (Need(REG), Need(REG))),
            cost=1,
            action="emit_arit_reg",
        ),
        Rule(
            name="div_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.DIVIDE, (Need(REG), Need(REG))),
            cost=1,
            action="emit_arit_reg",
        ),
        Rule(
            name="rem_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.REMAINDER, (Need(REG), Need(REG))),
            cost=1,
            action="emit_arit_reg",
        ),

        # Soma REG/IMM12 ou IMM12/REG, com Addi. 1
        Rule(
            name="soma_imediato_direita",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.ADD, (Need(REG), Need(IMM12))),
            cost=1,
            action="emit_soma_imediato_direita",
        ),
        Rule(
            name="soma_imediato_esquerda",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.ADD, (Need(IMM12), Need(REG))),
            cost=1,
            action="emit_soma_imediato_esquerda",
        ),

        # Subtração REG menos literal cujo oposto cabe no imediato, com Addi. 1
        Rule(
            name="sub_imediato",
            result=REG,
            pattern=Pattern(
                BinaryExpr,
                BinaryOperator.SUBTRACT,
                (Need(REG), Pattern(predicate=neg_imm12)),
            ),
            cost=1,
            action="emit_sub_imediato",
        ),

        # Multiplicação REG/POW2 ou POW2/REG, com Slli. 1
        Rule(
            name="mul_pow2_direita",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.MULTIPLY, (Need(REG), Need(POW2))),
            cost=1,
            action="emit_mul_pow2_direita",
        ),
        Rule(
            name="mul_pow2_esquerda",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.MULTIPLY, (Need(POW2), Need(REG))),
            cost=1,
            action="emit_mul_pow2_esquerda",
        ),

        # Menor ou maior de dois REG para REG, com Slt. 1
        Rule(
            name="menor_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.LESS, (Need(REG), Need(REG))),
            cost=1,
            action="emit_comp_reg",
        ),
        Rule(
            name="maior_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.GREATER, (Need(REG), Need(REG))),
            cost=1,
            action="emit_comp_reg",
        ),

        # Menor ou igual, maior ou igual para REG, com Slt e Seqz. 2
        Rule(
            name="menor_igual_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.LESS_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_reg",
        ),
        Rule(
            name="maior_igual_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.GREATER_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_reg",
        ),

        # Igualdade/desigualdade para REG, com Xor e Seqz/Snez. 2
        Rule(
            name="igual_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_reg",
        ),
        Rule(
            name="diferente_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.NOT_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_reg",
        ),

        # Comparação de dois REG para COND, branch direto e Jump. 2
        Rule(
            name="menor_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.LESS, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),
        Rule(
            name="menor_igual_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.LESS_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),
        Rule(
            name="maior_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.GREATER, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),
        Rule(
            name="maior_igual_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.GREATER_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),
        Rule(
            name="igual_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),
        Rule(
            name="diferente_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.NOT_EQUAL, (Need(REG), Need(REG))),
            cost=2,
            action="emit_comp_cond",
        ),

        # Negação lógica de REG para REG, com Seqz. 1
        Rule(
            name="not_reg",
            result=REG,
            pattern=Pattern(UnaryExpr, UnaryOperator.NOT, (Need(REG),)),
            cost=1,
            action="emit_not_reg",
        ),

        # Negação lógica de COND para COND, invertendo destinos. 0
        Rule(
            name="not_cond",
            result=COND,
            pattern=Pattern(UnaryExpr, UnaryOperator.NOT, (Need(COND),)),
            cost=0,
            action="emit_not_cond",
        ),

        # &&/|| de dois COND para COND. 0
        Rule(
            name="and_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.LOGICAL_AND, (Need(COND), Need(COND))),
            cost=0,
            action="emit_and_cond",
        ),
        Rule(
            name="or_cond",
            result=COND,
            pattern=Pattern(BinaryExpr, BinaryOperator.LOGICAL_OR, (Need(COND), Need(COND))),
            cost=0,
            action="emit_or_cond",
        ),

        # &&/|| de dois COND para REG, com duas Li e um Jump. 3
        Rule(
            name="and_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.LOGICAL_AND, (Need(COND), Need(COND))),
            cost=3,
            action="emit_logico_reg",
        ),
        Rule(
            name="or_reg",
            result=REG,
            pattern=Pattern(BinaryExpr, BinaryOperator.LOGICAL_OR, (Need(COND), Need(COND))),
            cost=3,
            action="emit_logico_reg",
        ),

        # Literal bool para COND, com Jump. 1
        Rule(
            name="bool_cond",
            result=COND,
            pattern=Pattern(BoolLiteral),
            cost=1,
            action="emit_bool_cond",
        ),

        # Identificador bool para COND, com branch e Jump. 2
        Rule(
            name="ID_cond",
            result=COND,
            pattern=Pattern(IdentifierExpr, predicate=is_bool),
            cost=2,
            action="emit_id_cond",
        ),

        # Chamada com argumentos REG para REG ou EFFECT, com Call. 1
        Rule(
            name="call_reg",
            result=REG,
            pattern=Pattern(CallExpr, children=(Args(REG),), predicate=has_value),
            cost=1,
            action="emit_call_reg",
        ),
        Rule(
            name="call_effect",
            result=EFFECT,
            pattern=Pattern(CallExpr, children=(Args(REG),)),
            cost=1,
            action="emit_call_effect",
        ),

        # Chamada bool com argumentos REG para COND, com chamada e desvios. 3
        Rule(
            name="call_cond",
            result=COND,
            pattern=Pattern(CallExpr, children=(Args(REG),), predicate=is_bool),
            cost=3,
            action="emit_call_cond",
        ),
    ]
