from tokens import TokenType, Token
from symbol_table import SymbolTable, Symbol, VarType
from poliz import Op


class ParseError(Exception):
    def __init__(self, msg, tok):
        super().__init__(
            f"[Parser] {tok.line}:{tok.col}: {msg} (получено {tok.type.name} {tok.value!r})")
        self.line, self.col = tok.line, tok.col


class Parser:
    """
    Рекурсивный спуск с семантическими процедурами,
    генерирующими фрагменты ПОЛИЗа.
    """

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0
        self.poliz = []
        self.symtab = SymbolTable()
        self.labels = {}           # label -> pc
        self.pending_gotos = []    # (pc, label)
        self.current_func = None

    # ---------- утилиты ----------
    def _cur(self): return self.tokens[self.pos]
    def _advance(self): self.pos += 1; return self.tokens[self.pos-1]
    def _check(self, t): return self._cur().type == t

    def _match(self, t):
        if self._check(t):
            return self._advance()
        raise ParseError(f"ожидалось {t.name}", self._cur())

    def _skip_eol(self):
        while self._check(TokenType.EOL):
            self._advance()

    # ---------- точка входа ----------
    def parse(self):
        self._skip_eol()
        while not self._check(TokenType.EOF):
            if self._check(TokenType.FUNCTION):
                self._function()
            else:
                self._statement()
            self._skip_eol()
        # разрешение отложенных переходов
        for pc, label in self.pending_gotos:
            if label not in self.labels:
                raise ParseError(f"неизвестная метка {label!r}", self._cur())
            self.poliz[pc] = (Op.JMP, self.labels[label])
        return self.poliz, self.symtab

    # ---------- функции ----------
    def _function(self):
        self._match(TokenType.FUNCTION)
        name_tok = self._match(TokenType.IDENT)
        fname = name_tok.value
        self._match(TokenType.LPAREN)
        params = []
        if not self._check(TokenType.RPAREN):
            params.append(self._param())
            while self._check(TokenType.COMMA):
                self._advance()
                params.append(self._param())
        self._match(TokenType.RPAREN)
        # возвращаемый тип — по имени (в BASIC-подобном: суффикс не используем, тип задаётся AS)
        ftype = VarType.INT  # упрощение: по умолчанию INTEGER; можно расширить
        sym = Symbol(fname, ftype, is_function=True,
                     params=[(p[0], p[1]) for p in params],
                     return_type=ftype)
        self.symtab.add(sym)
        entry = len(self.poliz)
        sym.func_index = entry
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
        return (name, t)

    # ---------- операторы ----------
    def _statement(self):
        t = self._cur().type
        if t == TokenType.DIM:
            self._var_decl()
        elif t == TokenType.PRINT:
            self._print()
        elif t == TokenType.INPUT:
            self._input()
        elif t == TokenType.IF:
            self._if()
        elif t == TokenType.DO:
            self._do()
        elif t == TokenType.FOR:
            self._for()
        elif t == TokenType.SELECT:
            self._select()
        elif t == TokenType.GOTO:
            self._goto()
        elif t == TokenType.RETURN:
            self._return()
        elif t == TokenType.CALL:
            self._call()
        elif t == TokenType.IDENT:
            # метка или присваивание
            if self.tokens[self.pos+1].type == TokenType.COLON:
                self._label()
            else:
                self._assign()
        else:
            raise ParseError("ожидался оператор", self._cur())

    def _type(self):
        t = self._cur().type
        if t == TokenType.INTEGER:
            self._advance()
            return VarType.INT
        if t == TokenType.REAL_T:
            self._advance()
            return VarType.REAL
        if t == TokenType.STRING_T:
            self._advance()
            return VarType.STRING
        raise ParseError("ожидался тип", self._cur())

    def _var_decl(self):
        self._match(TokenType.DIM)
        while True:
            name = self._match(TokenType.IDENT).value
            self._match(TokenType.AS)
            t = self._type()
            self.symtab.add(Symbol(name, t))
            if not self._check(TokenType.COMMA):
                break
            self._advance()

    def _assign(self):
        name = self._match(TokenType.IDENT).value
        sym = self.symtab.get(name)
        self._match(TokenType.ASSIGN)
        t = self._expression()
        self._check_assign_types(sym, t)
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
        """DO ... LOOP WHILE cond  (цикл с постусловием)"""
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
            self.poliz.append((Op.JZ, len(self.poliz)+2))  # выход
            self.poliz.append((Op.JMP, start))
        elif self._check(TokenType.UNTIL):
            self._advance()
            self._expression()
            self.poliz.append((Op.NOT,))
            self.poliz.append((Op.JZ, start))
        else:
            self.poliz.append((Op.JMP, start))

    def _for(self):
        self._match(TokenType.FOR)
        name = self._match(TokenType.IDENT).value
        sym = self.symtab.get(name)
        self._match(TokenType.EQ)
        self._expression()
        self.poliz.append((Op.POP_VAR, name))
        self._match(TokenType.TO)
        self._expression()
        # предел? упрощение: предел в переменной цикла не храним
        self.poliz.append((Op.PUSH_VAR, name))
        # Для простоты: for реализуется как while с переменной счётчиком
        # (полноценная реализация с limit/step — в расширении)
        self._match(TokenType.TO)
        # ... (см. примечание в конце; здесь — упрощённая версия)
        self._skip_eol()
        while not self._check(TokenType.NEXT):
            self._statement()
            self._skip_eol()
        self._match(TokenType.NEXT)

    def _select(self):
        self._match(TokenType.SELECT)
        self._match(TokenType.CASE)
        self._expression()                      # значение в стеке
        end_jumps = []
        self._skip_eol()
        while self._check(TokenType.CASE):
            self._advance()
            if self._check(TokenType.ELSE):
                self._advance()
                self._match(TokenType.COLON)
                self._skip_eol()
                while not self._check(TokenType.CASE) and not self._check(TokenType.ENDSELECT):
                    self._statement()
                    self._skip_eol()
                continue
            # метки case: const [TO const]
            labels = []
            labels.append(self._const())
            while self._check(TokenType.COMMA):
                self._advance()
                labels.append(self._const())
            self._match(TokenType.COLON)
            self._skip_eol()
            # генерируем сравнения: для простоты — цепочка CMPE + JZ на следующий case
            # (полноценный SELECT — в расширении; здесь демонстрация идеи)
            body_start = len(self.poliz)
            while not self._check(TokenType.CASE) and not self._check(TokenType.ENDSELECT):
                self._statement()
                self._skip_eol()
            j = len(self.poliz)
            self.poliz.append((Op.JMP, None))
            end_jumps.append(j)
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

    # ---------- выражения ----------
    def _expression(self): return self._logic_or()

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
            self._multiplicative()
            self.poliz.append((op,))
            t = VarType.REAL if VarType.REAL in (t,) else t
        return t

    def _multiplicative(self):
        t = self._unary()
        while self._cur().type in (TokenType.MUL, TokenType.DIV):
            op = Op.MUL if self._cur().type == TokenType.MUL else Op.DIV
            self._advance()
            self._unary()
            self.poliz.append((op,))
            t = VarType.REAL if op == Op.DIV else t
        return t

    def _unary(self):
        if self._check(TokenType.MINUS):
            self._advance()
            self._unary()
            self.poliz.append((Op.SUB,))    # 0 - x; см. примечание
            return VarType.INT
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
            if self._check(TokenType.LPAREN):        # вызов функции в выражении
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
        t = self._cur().type
        if t == TokenType.INT:
            return self._advance().value
        if t == TokenType.REAL:
            return self._advance().value
        if t == TokenType.STRING:
            return self._advance().value
        raise ParseError("ожидалась константа", self._cur())

    def _check_assign_types(self, sym, rhs_type):
        if sym.vtype == VarType.INT and rhs_type == VarType.REAL:
            raise ParseError(
                f"нельзя присвоить REAL в INTEGER-переменную {sym.name!r}",
                self._cur())
        if sym.vtype == VarType.STRING and rhs_type != VarType.STRING:
            raise ParseError(
                f"в STRING-переменную {sym.name!r} нельзя присвоить {rhs_type.value}",
                self._cur())
        if sym.vtype in (VarType.INT, VarType.REAL) and rhs_type == VarType.STRING:
            raise ParseError(
                f"в числовую переменную {sym.name!r} нельзя присвоить STRING",
                self._cur())
