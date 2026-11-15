from enum import Enum, auto
from dataclasses import dataclass


class TokenType(Enum):
    # литералы
    INT = auto()
    REAL = auto()
    STRING = auto()
    # идентификаторы и ключевые слова
    IDENT = auto()
    DIM = auto()
    AS = auto()
    INTEGER = auto()
    REAL_T = auto()
    STRING_T = auto()
    IF = auto()
    THEN = auto()
    ELSE = auto()
    ENDIF = auto()
    DO = auto()
    LOOP = auto()
    WHILE = auto()
    UNTIL = auto()
    FOR = auto()
    TO = auto()
    STEP = auto()
    NEXT = auto()
    SELECT = auto()
    CASE = auto()
    ENDSELECT = auto()
    GOTO = auto()
    RETURN = auto()
    FUNCTION = auto()
    ENDFUNCTION = auto()
    PRINT = auto()
    INPUT = auto()
    CALL = auto()
    AND = auto()
    OR = auto()
    NOT = auto()
    # операторы
    PLUS = auto()
    MINUS = auto()
    MUL = auto()
    DIV = auto()
    GT = auto()
    LT = auto()
    GE = auto()
    LE = auto()
    EQ = auto()
    NE = auto()
    ASSIGN = auto()          # :=
    # разделители
    LPAREN = auto()
    RPAREN = auto()
    COMMA = auto()
    COLON = auto()
    EOL = auto()             # конец строки
    EOF = auto()


KEYWORDS = {
    'DIM': TokenType.DIM, 'AS': TokenType.AS,
    'INTEGER': TokenType.INTEGER, 'REAL': TokenType.REAL_T,
    'STRING': TokenType.STRING_T,
    'IF': TokenType.IF, 'THEN': TokenType.THEN, 'ELSE': TokenType.ELSE,
    'ENDIF': TokenType.ENDIF,
    'DO': TokenType.DO, 'LOOP': TokenType.LOOP,
    'WHILE': TokenType.WHILE, 'UNTIL': TokenType.UNTIL,
    'FOR': TokenType.FOR, 'TO': TokenType.TO, 'STEP': TokenType.STEP,
    'NEXT': TokenType.NEXT,
    'SELECT': TokenType.SELECT, 'CASE': TokenType.CASE,
    'ENDSELECT': TokenType.ENDSELECT,
    'GOTO': TokenType.GOTO, 'RETURN': TokenType.RETURN,
    'FUNCTION': TokenType.FUNCTION, 'ENDFUNCTION': TokenType.ENDFUNCTION,
    'PRINT': TokenType.PRINT, 'INPUT': TokenType.INPUT, 'CALL': TokenType.CALL,
    'AND': TokenType.AND, 'OR': TokenType.OR, 'NOT': TokenType.NOT,
}


@dataclass
class Token:
    type: TokenType
    value: object
    line: int
    col: int

    def __repr__(self):
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.col})"
