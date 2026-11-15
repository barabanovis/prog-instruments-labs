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
    INT2REAL = 'INT2REAL'

# Базовый набор из задания: JMP, JZ, SET, ADD, SUB, AND, OR, CMPE, CMPL
# + расширения под вариант: MUL, DIV, CMPG, CMPLE, CMPGE, CMPNE, NOT, IO, CALL/RET


def disassemble(poliz, current_pc=None):
    """Текстовый дамп ПОЛИЗа с подсветкой текущей инструкции."""
    lines = []
    for i, ins in enumerate(poliz):
        op = ins[0]
        args = ins[1:]
        mark = '>>' if i == current_pc else '  '
        lines.append(f"{mark} {i:04d}  {op:<10} {' '.join(map(str, args))}")
    return '\n'.join(lines)
