"""
frontend/lexer.py
=================
Лексический анализатор — конечный автомат.
Текст -> поток токенов. Комментарий: апостроф до конца строки.
"""

from core.tokens import Token, TokenType, KEYWORDS


class LexerError(Exception):
    def __init__(self, msg, line, col):
        super().__init__(f"[Lexer] {line}:{col}: {msg}")
        self.line, self.col = line, col


class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.line = 1
        self.col = 1
        self.tokens = []

    def _peek(self, k=0):
        i = self.pos + k
        return self.src[i] if i < len(self.src) else ''

    def _advance(self):
        ch = self.src[self.pos]
        self.pos += 1
        if ch == '\n':
            self.line += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def tokenize(self):
        while self.pos < len(self.src):
            ch = self._peek()
            if ch in ' \t\r':
                self._advance()
                continue
            if ch == "'":
                while self.pos < len(self.src) and self._peek() != '\n':
                    self._advance()
                continue
            if ch == '\n':
                self.tokens.append(
                    Token(TokenType.EOL, '\n', self.line, self.col))
                self._advance()
                continue
            if ch.isalpha() or ch == '_':
                self._ident()
                continue
            if ch.isdigit():
                self._number()
                continue
            if ch == '"':
                self._string()
                continue
            self._operator()
        self.tokens.append(Token(TokenType.EOF, None, self.line, self.col))
        return self.tokens

    def _ident(self):
        line, col = self.line, self.col
        buf = []
        while self._peek().isalnum() or self._peek() == '_':
            buf.append(self._advance())
        name = ''.join(buf)
        ttype = KEYWORDS.get(name.upper(), TokenType.IDENT)
        self.tokens.append(Token(ttype, name, line, col))

    def _number(self):
        line, col = self.line, self.col
        buf = []
        while self._peek().isdigit():
            buf.append(self._advance())
        if self._peek() == '.' and self._peek(1).isdigit():
            buf.append(self._advance())
            while self._peek().isdigit():
                buf.append(self._advance())
            self.tokens.append(
                Token(TokenType.REAL, float(''.join(buf)), line, col))
        else:
            self.tokens.append(
                Token(TokenType.INT, int(''.join(buf)), line, col))

    def _string(self):
        line, col = self.line, self.col
        self._advance()
        buf = []
        while True:
            ch = self._peek()
            if ch == '':
                raise LexerError("незакрытая строка", line, col)
            if ch == '"':
                if self._peek(1) == '"':
                    self._advance()
                    buf.append('"')
                    self._advance()
                else:
                    self._advance()
                    break
            else:
                buf.append(self._advance())
        self.tokens.append(Token(TokenType.STRING, ''.join(buf), line, col))

    def _operator(self):
        line, col = self.line, self.col
        two = self._peek() + self._peek(1)
        two_map = {'>=': TokenType.GE, '<=': TokenType.LE,
                   '<>': TokenType.NE, ':=': TokenType.ASSIGN}
        if two in two_map:
            self._advance()
            self._advance()
            self.tokens.append(Token(two_map[two], two, line, col))
            return
        one_map = {
            '+': TokenType.PLUS, '-': TokenType.MINUS,
            '*': TokenType.MUL,  '/': TokenType.DIV,
            '>': TokenType.GT,   '<': TokenType.LT, '=': TokenType.EQ,
            '(': TokenType.LPAREN, ')': TokenType.RPAREN,
            ',': TokenType.COMMA,  ':': TokenType.COLON,
        }
        ch = self._peek()
        if ch in one_map:
            self._advance()
            self.tokens.append(Token(one_map[ch], ch, line, col))
            return
        raise LexerError(f"неизвестный символ {ch!r}", line, col)
