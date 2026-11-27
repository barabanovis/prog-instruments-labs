"""
backend/interpreter.py
======================
Стековая машина, исполняющая ПОЛИЗ.
"""

from core.poliz import Op
from core.symbol_table import VarType


class InterpreterError(Exception):
    def __init__(self, msg, pc):
        super().__init__(f"[Interpreter] pc={pc}: {msg}")
        self.pc = pc


class Interpreter:
    def __init__(self, poliz, symtab):
        self.poliz = poliz
        self.symtab = symtab
        self.pc = 0
        self.stack = []
        self.call_stack = []
        self.output = []
        self.finished = False

    def _push(self, v):
        self.stack.append(v)

    def _pop(self):
        if not self.stack:
            raise InterpreterError("стек пуст", self.pc)
        return self.stack.pop()

    def _coerce(self, v, vtype):
        if vtype == VarType.INT:
            return int(v)
        if vtype == VarType.REAL:
            return float(v)
        if vtype == VarType.STRING and not isinstance(v, str):
            raise InterpreterError(
                f"ожидалась строка, получено {type(v).__name__}", self.pc)
        return v

    def step(self):
        if self.finished or self.pc >= len(self.poliz):
            self.finished = True
            return True

        ins = self.poliz[self.pc]
        op = ins[0]

        if op == Op.PUSH_CONST:
            self._push(ins[1])
            self.pc += 1
        elif op == Op.PUSH_VAR:
            sym = self.symtab.get(ins[1])
            self._push(sym.value if sym.value is not None else 0)
            self.pc += 1
        elif op == Op.POP_VAR:
            sym = self.symtab.get(ins[1])
            v = self._pop()
            sym.value = self._coerce(v, sym.vtype)
            self.pc += 1
        elif op == Op.SET:
            v = self._pop()
            sym = self.symtab.get(ins[1])
            sym.value = self._coerce(v, sym.vtype)
            self.pc += 1
        elif op == Op.ADD:
            b = self._pop()
            a = self._pop()
            self._push(a + b)
            self.pc += 1
        elif op == Op.SUB:
            b = self._pop()
            a = self._pop()
            self._push(a - b)
            self.pc += 1
        elif op == Op.MUL:
            b = self._pop()
            a = self._pop()
            self._push(a * b)
            self.pc += 1
        elif op == Op.DIV:
            b = self._pop()
            a = self._pop()
            if b == 0:
                raise InterpreterError("деление на ноль", self.pc)
            self._push(a / b)
            self.pc += 1
        elif op == Op.NEG:
            a = self._pop()
            self._push(-a)
            self.pc += 1
        elif op == Op.AND:
            b = self._pop()
            a = self._pop()
            self._push(int(bool(a) and bool(b)))
            self.pc += 1
        elif op == Op.OR:
            b = self._pop()
            a = self._pop()
            self._push(int(bool(a) or bool(b)))
            self.pc += 1
        elif op == Op.NOT:
            a = self._pop()
            self._push(int(not bool(a)))
            self.pc += 1
        elif op == Op.CMPE:
            b = self._pop()
            a = self._pop()
            self._push(int(a == b))
            self.pc += 1
        elif op == Op.CMPL:
            b = self._pop()
            a = self._pop()
            self._push(int(a < b))
            self.pc += 1
        elif op == Op.CMPG:
            b = self._pop()
            a = self._pop()
            self._push(int(a > b))
            self.pc += 1
        elif op == Op.CMPLE:
            b = self._pop()
            a = self._pop()
            self._push(int(a <= b))
            self.pc += 1
        elif op == Op.CMPGE:
            b = self._pop()
            a = self._pop()
            self._push(int(a >= b))
            self.pc += 1
        elif op == Op.CMPNE:
            b = self._pop()
            a = self._pop()
            self._push(int(a != b))
            self.pc += 1
        elif op == Op.JMP:
            self.pc = ins[1]
        elif op == Op.JZ:
            v = self._pop()
            self.pc = ins[1] if not v else self.pc + 1
        elif op == Op.IN:
            raw = input(f"INPUT ({ins[1]}): ")
            try:
                if ins[1] == VarType.INT.value:
                    v = int(raw)
                elif ins[1] == VarType.REAL.value:
                    v = float(raw)
                else:
                    v = raw
            except ValueError:
                raise InterpreterError(f"неверный ввод для {ins[1]}", self.pc)
            self._push(v)
            self.pc += 1
        elif op == Op.OUT:
            v = self._pop()
            self.output.append(str(v))
            self.pc += 1
        elif op == Op.OUTSTR:
            self.output.append(ins[1])
            self.pc += 1
        elif op == Op.CALL:
            entry, argc = ins[1], ins[2]
            args = [self._pop() for _ in range(argc)][::-1]
            self.call_stack.append((self.pc + 1, self.stack.copy(), argc))
            for a in args:
                self._push(a)
            self.pc = entry
        elif op == Op.RET:
            if self.call_stack:
                ret_pc, saved_stack, argc = self.call_stack.pop()
                ret_val = self._pop() if self.stack else None
                self.stack = saved_stack
                if ret_val is not None:
                    self._push(ret_val)
                self.pc = ret_pc
            else:
                self.finished = True
        else:
            raise InterpreterError(f"неизвестная операция {op}", self.pc)
        return self.finished

    def run(self):
        while not self.finished:
            self.step()
        return self.output
