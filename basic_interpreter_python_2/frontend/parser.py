"""
frontend/parser.py
==================
Рекурсивный спуск + генерация ПОЛИЗа за один проход.
Семантические проверки вынесены в ast_hooks.py.

Структура:
  1) утилиты;
  2) точка входа;
  3) функции;
  4) операторы;
  5) выражения (лестница приоритетов).
"""

from core.tokens import TokenType
from core.symbol_table import SymbolTable, Symbol, VarType
from core.poliz import Op
from frontend.ast_hooks import check_assign_types, SemanticError


class ParseError(Exception):
    def __init__(self, msg, tok):
        super().__init__(f"[Parser] {tok.line}:{tok.col}: {msg} "
                         f"(получено {tok.type.name} {tok.value!r})")
        self.line, self.col = tok.line, tok.col


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.poliz = []
        self.symtab = SymbolTable()
        self.labels = {}
        self.pending_gotos = []
        self.current_func = None

    # ============================================================
    # 1. УТИЛИТЫ
    # ============================================================

    def _cur(self):
        return self.tokens[self.pos]

    def _advance(self):
        self.pos += 1
        return self.tokens[self.pos - 1]

    def _check(self, t):
        return self._cur().type == t

    def _match(self, t):
        if self._check(t):
            return self._advance()
        raise ParseError(f"ожидалось {t.name}", self._cur())

    def _skip_eol(self):
        while self._check(TokenType.EOL):
            self._advance()

    # ============================================================
    # 2. ТОЧКА ВХОДА
    # ============================================================

    def parse(self):
        self._skip_eol()
        while not self._check(TokenType.EOF):
            if self._check(TokenType.FUNCTION):
                self._function()
            else:
                self._statement()
            self._skip_eol()
        for pc, label in self.pending_gotos:
            if label not in self.labels:
                raise ParseError(f"неизвестная метка {label!r}", self._cur())
            self.poliz[pc] = (Op.JMP, self.labels[label])
        return self.poliz, self.symtab

    # ============================================================
    # 3. ФУНКЦИИ
    # ============================================================

    def _function(self):
        self._match(TokenType.FUNCTION)
        fname = self._match(TokenType.IDENT).value
        self._match(TokenType.LPAREN)
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._param())
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self._param())
        self._match(TokenType.RPAREN)

        ftype = VarType.INT
        sym = Symbol(fname, ftype, is_function=True,
                     params=params, return_type=ftype)
        self.symtab.add(sym)
        sym.func_index = len(self.poliz)
        self.current_func = fname

        self._skip_eol()
        while not self._check(TokenType.ENDFUNCTION):
            self._statement()
            self._skip_eol()
        self._match(TokenType.ENDFUNCTION)
        self.poliz.append((Op.RET,))
        self.current_func = None

    def _param(self):
        name = self._match(TokenType.IDENT).value
        self._match(TokenType.AS)
        t = self._type()
        self.symtab.add(Symbol(name, t))
        return name, t

    # ============================================================
    # 4. ОПЕРАТОРЫ
    # ============================================================

    def _statement(self):
        t = self._cur().type
        dispatch = {
            TokenType.DIM: self._var_decl,
            TokenType.PRINT: self._print,
            TokenType.INPUT: self._input,
            TokenType.IF: self._if,
            TokenType.DO: self._do,
            TokenType.FOR: self._for,
            TokenType.SELECT: self._select,
            TokenType.GOTO: self._goto,
            TokenType.RETURN: self._return,
            TokenType.CALL: self._call,
        }
        if t in dispatch:
            dispatch[t]()
        elif t == TokenType.IDENT:
            if self.tokens[self.pos + 1].type == TokenType.COLON:
                self._label()
            else:
                self._assign()
        else:
            raise ParseError("ожидался оператор", self._cur())

    def _type(self):
        for tok, vt in ((TokenType.INTEGER, VarType.INT),
                        (TokenType.REAL_T, VarType.REAL),
                        (TokenType.STRING_T, VarType.STRING)):
            if self._check(tok):
                self._advance()
                return vt
        raise ParseError("ожидался тип", self._cur())

    def _var_decl(self):
        self._match(TokenType.DIM)
        while True:
            name = self._match(TokenType.IDENT).value
            self._match(TokenType.AS)
            self.symtab.add(Symbol(name, self._type()))
            if not self._check(TokenType.COMMA):
                break
            self._advance()

    def _assign(self):
        name = self._match(TokenType.IDENT).value
        sym = self.symtab.get(name)
        self._match(TokenType.ASSIGN)
        rhs_type = self._expression()
        try:
            check_assign_types(sym, rhs_type, self._cur())
        except SemanticError as e:
            raise ParseError(str(e), self._cur())
        self.poliz.append((Op.POP_VAR, name))

    def _print(self):
        self._match(TokenType.PRINT)
        if self._check(TokenType.EOL) or self._check(TokenType.EOF):
            self.poliz.append((Op.OUTSTR, ''))
            return
        self._expression()
        self.poliz.append((Op.OUT,))
        while self._check(TokenType.COMMA):
            self._advance()
            self._expression()
            self.poliz.append((Op.OUT,))

    def _input(self):
        self._match(TokenType.INPUT)
        while True:
            name = self._match(TokenType.IDENT).value
            sym = self.symtab.get(name)
            self.poliz.append((Op.IN, sym.vtype.value))
            self.poliz.append((Op.POP_VAR, name))
            if not self._check(TokenType.COMMA):
                break
            self._advance()

    def _if(self):
        self._match(TokenType.IF)
        self._expression()
        jz = len(self.poliz)
        self.poliz.append((Op.JZ, None))
        self._match(TokenType.THEN)
        self._skip_eol()

        while not (self._check(TokenType.ELSE) or self._check(TokenType.ENDIF)):
            self._statement()
            self._skip_eol()

        if self._check(TokenType.ELSE):
            jmp = len(self.poliz)
            self.poliz.append((Op.JMP, None))
            self.poliz[jz] = (Op.JZ, len(self.poliz))
            self._advance()
            self._skip_eol()
            while not self._check(TokenType.ENDIF):
                self._statement()
                self._skip_eol()
            self.poliz[jmp] = (Op.JMP, len(self.poliz))
        else:
            self.poliz[jz] = (Op.JZ, len(self.poliz))
        self._match(TokenType.ENDIF)

    def _do(self):
        """DO ... LOOP [WHILE cond | UNTIL cond]."""
        self._match(TokenType.DO)
        start = len(self.poliz)
        self._skip_eol()
        while not self._check(TokenType.LOOP):
            self._statement()
            self._skip_eol()
        self._match(TokenType.LOOP)

        if self._check(TokenType.WHILE):
            self._advance()
            self._expression()
            jz = len(self.poliz)
            self.poliz.append((Op.JZ, None))
            self.poliz.append((Op.JMP, start))
            self.poliz[jz] = (Op.JZ, len(self.poliz))
        elif self._check(TokenType.UNTIL):
            self._advance()
            self._expression()
            self.poliz.append((Op.NOT,))
            self.poliz.append((Op.JZ, start))
        else:
            self.poliz.append((Op.JMP, start))

    def _for(self):
        """FOR i = a TO b [STEP s] ... NEXT [i] — реализация через while."""
        self._match(TokenType.FOR)
        name = self._match(TokenType.IDENT).value
        self.symtab.get(name)
        self._match(TokenType.EQ)
        self._expression()
        self.poliz.append((Op.POP_VAR, name))

        # Предел и шаг — служебные переменные, чтобы не считать их каждый раз
        uniq = len(self.poliz)
        limit_name = f'__for_limit_{uniq}'
        step_name = f'__for_step_{uniq}'
        self.symtab.add(Symbol(limit_name, VarType.INT))
        self.symtab.add(Symbol(step_name, VarType.INT))

        self._match(TokenType.TO)
        self._expression()
        self.poliz.append((Op.POP_VAR, limit_name))

        if self._check(TokenType.STEP):
            self._advance()
            self._expression()
        else:
            self.poliz.append((Op.PUSH_CONST, 1, VarType.INT.value))
        self.poliz.append((Op.POP_VAR, step_name))

        self._skip_eol()
        loop_start = len(self.poliz)
        self.poliz.append((Op.PUSH_VAR, name))
        self.poliz.append((Op.PUSH_VAR, limit_name))
        self.poliz.append((Op.CMPLE,))
        exit_jz = len(self.poliz)
        self.poliz.append((Op.JZ, None))

        while not self._check(TokenType.NEXT):
            self._statement()
            self._skip_eol()
        self._match(TokenType.NEXT)
        if self._check(TokenType.IDENT):
            self._advance()

        self.poliz.append((Op.PUSH_VAR, name))
        self.poliz.append((Op.PUSH_VAR, step_name))
        self.poliz.append((Op.ADD,))
        self.poliz.append((Op.POP_VAR, name))
        self.poliz.append((Op.JMP, loop_start))
        self.poliz[exit_jz] = (Op.JZ, len(self.poliz))

    def _select(self):
        """SELECT CASE — селектор в служебной переменной, каждый case — цепочка CMPE."""
        self._match(TokenType.SELECT)
        self._match(TokenType.CASE)
        self._expression()
        selector_name = f'__select_{len(self.poliz)}'
        self.symtab.add(Symbol(selector_name, VarType.INT))
        self.poliz.append((Op.POP_VAR, selector_name))

        end_jumps = []
        self._skip_eol()

        while self._check(TokenType.CASE):
            self._advance()
            if self._check(TokenType.ELSE):
                self._advance()
                self._match(TokenType.COLON)
                self._skip_eol()
                while not (self._check(TokenType.CASE)
                           or self._check(TokenType.ENDSELECT)):
                    self._statement()
                    self._skip_eol()
                continue

            labels = [self._const()]
            while self._check(TokenType.COMMA):
                self._advance()
                labels.append(self._const())
            self._match(TokenType.COLON)
            self._skip_eol()

            body_jumps, next_case_jumps = [], []
            for lab in labels:
                self.poliz.append((Op.PUSH_VAR, selector_name))
                self.poliz.append((Op.PUSH_CONST, lab, VarType.INT.value))
                self.poliz.append((Op.CMPE,))
                jz = len(self.poliz)
                self.poliz.append((Op.JZ, None))
                jmp_body = len(self.poliz)
                self.poliz.append((Op.JMP, None))
                body_jumps.append(jmp_body)
                next_case_jumps.append(jz)

            skip_body = len(self.poliz)
            self.poliz.append((Op.JMP, None))

            body_start = len(self.poliz)
            for j in body_jumps:
                self.poliz[j] = (Op.JMP, body_start)
            for j in next_case_jumps:
                self.poliz[j] = (Op.JZ, skip_body + 1)

            while not (self._check(TokenType.CASE)
                       or self._check(TokenType.ENDSELECT)):
                self._statement()
                self._skip_eol()

            j_end = len(self.poliz)
            self.poliz.append((Op.JMP, None))
            end_jumps.append(j_end)
            self.poliz[skip_body] = (Op.JMP, len(self.poliz))

        self._match(TokenType.ENDSELECT)
        for j in end_jumps:
            self.poliz[j] = (Op.JMP, len(self.poliz))

    def _goto(self):
        self._match(TokenType.GOTO)
        label = self._match(TokenType.IDENT).value
        pc = len(self.poliz)
        self.poliz.append((Op.JMP, None))
        self.pending_gotos.append((pc, label))

    def _label(self):
        name = self._match(TokenType.IDENT).value
        self._match(TokenType.COLON)
        if name in self.labels:
            raise ParseError(f"метка {name!r} уже определена", self._cur())
        self.labels[name] = len(self.poliz)

    def _return(self):
        self._match(TokenType.RETURN)
        if not (self._check(TokenType.EOL) or self._check(TokenType.EOF)
                or self._check(TokenType.ENDFUNCTION)):
            self._expression()
        self.poliz.append((Op.RET,))

    def _call(self):
        self._match(TokenType.CALL)
        name = self._match(TokenType.IDENT).value
        sym = self.symtab.get(name)
        if not sym.is_function:
            raise ParseError(f"{name!r} не является функцией", self._cur())
        self._match(TokenType.LPAREN)
        if not self._check(TokenType.RPAREN):
            self._expression()
            while self._check(TokenType.COMMA):
                self._advance()
                self._expression()
        self._match(TokenType.RPAREN)
        self.poliz.append((Op.CALL, sym.func_index, len(sym.params)))

    # ============================================================
    # 5. ВЫРАЖЕНИЯ
    # ============================================================

    def _expression(self):
        return self._logic_or()

    def _logic_or(self):
        t = self._logic_and()
        while self._check(TokenType.OR):
            self._advance()
            self._logic_and()
            self.poliz.append((Op.OR,))
            t = VarType.INT
        return t

    def _logic_and(self):
        t = self._logic_not()
        while self._check(TokenType.AND):
            self._advance()
            self._logic_not()
            self.poliz.append((Op.AND,))
            t = VarType.INT
        return t

    def _logic_not(self):
        if self._check(TokenType.NOT):
            self._advance()
            self._logic_not()
            self.poliz.append((Op.NOT,))
            return VarType.INT
        return self._comparison()

    def _comparison(self):
        t = self._additive()
        op_map = {
            TokenType.GT: Op.CMPG, TokenType.LT: Op.CMPL,
            TokenType.GE: Op.CMPGE, TokenType.LE: Op.CMPLE,
            TokenType.EQ: Op.CMPE, TokenType.NE: Op.CMPNE,
        }
        while self._cur().type in op_map:
            op = op_map[self._cur().type]
            self._advance()
            self._additive()
            self.poliz.append((op,))
            t = VarType.INT
        return t

    def _additive(self):
        t = self._multiplicative()
        while self._cur().type in (TokenType.PLUS, TokenType.MINUS):
            op = Op.ADD if self._cur().type == TokenType.PLUS else Op.SUB
            self._advance()
            rt = self._multiplicative()
            self.poliz.append((op,))
            t = VarType.REAL if (
                t == VarType.REAL or rt == VarType.REAL) else t
        return t

    def _multiplicative(self):
        t = self._unary()
        while self._cur().type in (TokenType.MUL, TokenType.DIV):
            op = Op.MUL if self._cur().type == TokenType.MUL else Op.DIV
            self._advance()
            rt = self._unary()
            self.poliz.append((op,))
            if op == Op.DIV:
                t = VarType.REAL
            else:
                t = VarType.REAL if (
                    t == VarType.REAL or rt == VarType.REAL) else t
        return t

    def _unary(self):
        if self._check(TokenType.MINUS):
            self._advance()
            t = self._unary()
            self.poliz.append((Op.NEG,))
            return t
        return self._primary()

    def _primary(self):
        t = self._cur().type
        if t == TokenType.INT:
            v = self._advance().value
            self.poliz.append((Op.PUSH_CONST, v, VarType.INT.value))
            return VarType.INT
        if t == TokenType.REAL:
            v = self._advance().value
            self.poliz.append((Op.PUSH_CONST, v, VarType.REAL.value))
            return VarType.REAL
        if t == TokenType.STRING:
            v = self._advance().value
            self.poliz.append((Op.PUSH_CONST, v, VarType.STRING.value))
            return VarType.STRING
        if t == TokenType.IDENT:
            name = self._advance().value
            sym = self.symtab.get(name)
            if self._check(TokenType.LPAREN):
                self._match(TokenType.LPAREN)
                argc = 0
                if not self._check(TokenType.RPAREN):
                    self._expression()
                    argc += 1
                    while self._check(TokenType.COMMA):
                        self._advance()
                        self._expression()
                        argc += 1
                self._match(TokenType.RPAREN)
                self.poliz.append((Op.CALL, sym.func_index, argc))
                return sym.return_type
            self.poliz.append((Op.PUSH_VAR, name))
            return sym.vtype
        if t == TokenType.LPAREN:
            self._advance()
            rt = self._expression()
            self._match(TokenType.RPAREN)
            return rt
        raise ParseError("ожидалось выражение", self._cur())

    def _const(self):
        if self._cur().type in (TokenType.INT, TokenType.REAL, TokenType.STRING):
            return self._advance().value
        raise ParseError("ожидалась константа", self._cur())
