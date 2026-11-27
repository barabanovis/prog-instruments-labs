"""
frontend/ast_hooks.py
=====================
Семантические проверки, вынесенные из парсера.
Пока — только проверка совместимости типов в присваивании.
"""

from core.tokens import Token
from core.symbol_table import VarType


class SemanticError(Exception):
    def __init__(self, msg, tok: Token):
        super().__init__(f"[Semantic] {tok.line}:{tok.col}: {msg}")
        self.line, self.col = tok.line, tok.col


def check_assign_types(sym, rhs_type, tok: Token):
    """Проверить, можно ли присвоить значение типа rhs_type переменной sym."""
    if sym.vtype == VarType.INT and rhs_type == VarType.REAL:
        raise SemanticError(
            f"нельзя присвоить REAL в INTEGER-переменную {sym.name!r}", tok)
    if sym.vtype == VarType.STRING and rhs_type != VarType.STRING:
        raise SemanticError(
            f"в STRING-переменную {sym.name!r} нельзя присвоить "
            f"{rhs_type.value}", tok)
    if sym.vtype in (VarType.INT, VarType.REAL) and rhs_type == VarType.STRING:
        raise SemanticError(
            f"в числовую переменную {sym.name!r} нельзя присвоить STRING", tok)
