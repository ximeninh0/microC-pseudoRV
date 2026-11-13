"""Ponto de implementação do reconhecimento de padrões e custos mínimos."""

from patterns import *


def match_pattern(node, pattern, table):
    # verifica se o tipo do no eh compativel com o padrao
    if pattern.kind is not None and not isinstance(node, pattern.kind):
        return None

    # verifica se o operador do no bate com o esperado
    if pattern.operator is not None and getattr(node, "operator", None) is not pattern.operator:
        return None

    # avalia o predicado do padrao caso exista
    if pattern.predicate is not None and not pattern.predicate(node):
        return None

    # predicado sem filhos reconhece a subarvore inteira diretamente
    if pattern.predicate is not None and len(pattern.children) == 0:
        return (), 0

    subproblems = []
    subproblems_cost = 0

    # caso de args em chamada que exige a classe para cada argumento
    if len(pattern.children) == 1 and isinstance(pattern.children[0], Args):
        needed_class = pattern.children[0].result
        args = getattr(node, "arguments", ())
        for arg in args:
            choice = table.lookup(arg, needed_class)
            if choice is None:
                return None
            subproblems.append((arg, needed_class))
            subproblems_cost += choice.cost
        return tuple(subproblems), subproblems_cost

    # nos outros casos a quantidade de filhos deve coincidir
    node_children = children(node)
    if len(node_children) != len(pattern.children):
        return None

    # percorre os filhos do padrao e da ast
    for pat_child, ast_child in zip(pattern.children, node_children):
        if isinstance(pat_child, Need):
            # subproblema need exige cobertura registrada na tabela
            choice = table.lookup(ast_child, pat_child.result)
            if choice is None:
                return None
            subproblems.append((ast_child, pat_child.result))
            subproblems_cost += choice.cost
        elif isinstance(pat_child, Pattern):
            # padrao aninhado validado recursivamente
            matched = match_pattern(ast_child, pat_child, table)
            if matched is None:
                return None
            nested_subproblems, nested_cost = matched
            subproblems.extend(nested_subproblems)
            subproblems_cost += nested_cost
        else:
            return None

    return tuple(subproblems), subproblems_cost


def match_rule(node, rule, table):
    # tenta casar o padrao da regra no no
    matched = match_pattern(node, rule.pattern, table)
    if matched is None:
        return None

    subproblems, sub_cost = matched
    # soma o custo proprio da regra com o custo dos subproblemas
    total_cost = rule.cost + sub_cost
    return Choice(cost=total_cost, rule=rule, subproblems=subproblems)


class Selector:
    """Selecione coberturas sem executar expressões ou emitir instruções."""

    def __init__(self, rules):
        self.rules = tuple(rules)

    def analyze(self, expr):
        """Calcule mínimos por nó/classe sem emitir instruções."""
        table = SelectionTable()

        # percurso em pos-ordem sobre a arvore de expressao
        def post_order(node):
            if node is None:
                return

            # primeiro visita todos os filhos
            for child in children(node):
                post_order(child)

            # avalia cada regra declarada para o no
            for rule in self.rules:
                choice = match_rule(node, rule, table)
                if choice is None:
                    continue

                # busca escolha atual para a classe oferecida pela regra
                current = table.lookup(node, rule.result)
                # se nao tiver escolha ou se o novo custo for estritamente menor, atualiza
                if current is None or choice.cost < current.cost:
                    table.put(node, rule.result, choice)

        post_order(expr)
        return table
