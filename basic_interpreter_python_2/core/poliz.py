"""
core/poliz.py
=============
Коды операций ПОЛИЗа и дизассемблер для GUI.
"""


class Op:
    JMP = 'JMP'
    JZ = 'JZ'
    SET = 'SET'
    ADD = 'ADD'
    SUB = 'SUB'
    MUL = 'MUL'
    DIV = 'DIV'
    AND = 'AND'
    OR = 'OR'
    NOT = 'NOT'
    CMPE = 'CMPE'
    CMPL = 'CMPL'
    CMPG = 'CMPG'
    CMPLE = 'CMPLE'
    CMPGE = 'CMPGE'
    CMPNE = 'CMPNE'
    IN = 'IN'
    OUT = 'OUT'
    OUTSTR = 'OUTSTR'
    CALL = 'CALL'
    RET = 'RET'
    PUSH_CONST = 'PUSH_CONST'
    PUSH_VAR = 'PUSH_VAR'
    POP_VAR = 'POP_VAR'
    NEG = 'NEG'


def disassemble(poliz, current_pc=None):
    """Текстовый дамп ПОЛИЗа; текущая инструкция помечается '>>'."""
    lines = []
    for i, ins in enumerate(poliz):
        mark = '>>' if i == current_pc else '  '
        args = ' '.join(map(str, ins[1:]))
        lines.append(f"{mark} {i:04d}  {ins[0]:<10} {args}")
    return '\n'.join(lines)
