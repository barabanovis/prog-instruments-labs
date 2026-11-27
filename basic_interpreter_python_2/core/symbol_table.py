"""
core/symbol_table.py
====================
Типы языка, описание символа и хеш-таблица с цепочками.
"""

from enum import Enum
from dataclasses import dataclass, field


class VarType(Enum):
    INT = 'INTEGER'
    REAL = 'REAL'
    STRING = 'STRING'


@dataclass
class Symbol:
    name: str
    vtype: VarType
    value: object = None
    is_function: bool = False
    params: list = field(default_factory=list)
    return_type: VarType = None
    func_index: int = None
    scope: str = 'global'


class SymbolTable:
    """
    Хеш-таблица с разрешением коллизий методом цепочек.
    Размер 211 — простое число, чтобы уменьшить коллизии.
    """

    def __init__(self, size=211):
        self.size = size
        self.buckets = [[] for _ in range(size)]
        self.count = 0

    def _hash(self, key: str) -> int:
        h = 5381
        for ch in key.lower():
            h = ((h << 5) + h) + ord(ch)
        return h % self.size

    def add(self, sym: Symbol) -> Symbol:
        idx = self._hash(sym.name)
        if any(s.name.lower() == sym.name.lower() for s in self.buckets[idx]):
            raise ValueError(f"идентификатор {sym.name!r} уже объявлен")
        self.buckets[idx].append(sym)
        self.count += 1
        return sym

    def lookup(self, name: str):
        idx = self._hash(name)
        for s in self.buckets[idx]:
            if s.name.lower() == name.lower():
                return s
        return None

    def get(self, name: str) -> Symbol:
        s = self.lookup(name)
        if s is None:
            raise KeyError(f"необъявленный идентификатор {name!r}")
        return s

    def dump(self):
        return [(i, b) for i, b in enumerate(self.buckets) if b]
