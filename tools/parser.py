#!/usr/bin/env python3

import sys
from lexer import Lexer

class Node:
    def __init__(self, tp, var, *children):
        self.type = tp
        self.variant = var
        self.children = children

    def print(self, indent=0):
        content = ' ' * indent + self.type
        if self.variant:
            content += ' {}'.format(self.variant)
        print(content)
        for c in self.children:
            c.print(indent + 2)


class Parser:
    def __init__(self, lexer):
        self.lexer = lexer

    def parse(self, src):
        self._src = self.lexer.read(src)
        self._putback = None
        return self._stmts()

    def _next(self):
        if self._putback:
            val = self._putback
            self._putback = None
            return val
        else:
            return next(self._src)

    def _peek(self):
        if not self._putback:
            self._putback = next(self._src)
        return self._putback

    def _expect(self, tp):
        t = self._next()
        if t.type != tp:
            self._error('expected {}, but got {}'.format(tp, t.type))
        return t

    def _error(self, msg):
        raise SyntaxError(msg)

    def _empty(self):
        return Node('STMTS', None)

    def _stmts(self):
        stmts = []
        while self._peek().type not in ['EOF', 'DEDENT']:
            stmts.append(self._stmt())
        return Node('STMTS', None, *stmts)

    def _stmt(self):
        t = self._peek()
        if t.type == 'IF':
            self._next()
            cond = self._test()
            self._expect('EOL')
            succ = self._block()
            t = self._peek()
            if t.type == 'ELSE':
                self._next()
                self._expect('EOL')
                fail = self._block()
            else:
                fail = self._empty()
            return Node('IF', None, cond, succ, fail)
        elif t.type == 'WHILE':
            self._next()
            cond = self._test()
            self._expect('EOL')
            cont = self._block()
            t = self._peek()
            if t.type == 'ELSE':
                self._next()
                self._expect('EOL')
                fail = self._block()
            else:
                fail = self._empty()
            return Node('WHILE', None, cond, cont, fail)
        else:
            t = self._expr()
            if self._peek().type in ['ASSN', 'PLUS_ASSN', 'MINUS_ASSN',
                    'MULT_ASSN', 'DIV_ASSN']:
                op = self._next()
                r = self._expr()
                t = Node('ASSN', op.type, t, r)
            else:
                t = Node('EXPR', None, t)
            self._expect('EOL')
            return t

    def _block(self):
        t = self._peek()
        if t.type == 'INDENT':
            self._next()
            stmts = self._stmts()
            self._expect('DEDENT')
            return stmts
        else:
            return self._empty()

    def _test(self):
        return self._comp()

    def _comp(self):
        t = self._expr()
        if self._peek().type in ['EQ', 'NE', 'LT', 'GT', 'LE', 'GE']:
            op = self._next()
            r = self._expr()
            t = Node('COMP', op.type, t, r)
        return t

    def _expr(self):
        t = self._term()
        while self._peek().type in ['PLUS', 'MINUS']:
            op = self._next()
            r = self._term()
            t = Node('BIN', op.type, t, r)
        return t

    def _term(self):
        t = self._factor()
        while self._peek().type in ['MULT', 'DIV']:
            op = self._next()
            r = self._factor()
            t = Node('BIN', op.type, t, r)
        return t

    def _factor(self):
        t = self._next()
        if t.type in ['ID', 'NUM']:
            return t
        elif t.type == 'LPAREN':
            t = self._test()
            self._expect('RPAREN')
            return t
        else:
            self._error('unexpected token {}'.format(t.type))


if __name__ == '__main__':
    with open('meta/lex') as f:
        lexer = Lexer(f)
    parser = Parser(lexer)
    parser.parse(sys.stdin).print()
