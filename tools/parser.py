#!/usr/bin/env python3

import sys
from lexer import Lexer
from node import Node

class Parser:
    def parse(self, src):
        self._src = iter(src)
        self._next()
        return self._file()

    def _next(self):
        self._lookahead = next(self._src)

    def _expect(self, *types):
        t = self._lookahead
        if t.type not in types:
            self._error('expected {}, but got {}'.format(
                ' or '.join(types),
                t.type))
        self._next()
        return t

    def _error(self, msg):
        raise SyntaxError(msg
                + '\nat line {0.line}, col {0.column}'.format(self._lookahead))

    def _empty(self):
        return Node('STMTS', ())

    def _file(self):
        children = []
        while self._lookahead.type != 'EOF':
            if self._lookahead.type == 'IMPORT':
                children.append(self._import())
            elif self._lookahead.type == 'CLASS':
                pass # TODO
            elif self._lookahead.type == 'DEF':
                pass # TODO
            else:
                children.append(self._stmt())
        return Node('FILE', children)

    def _import(self):
        self._expect('IMPORT')
        name = self._id()
        self._expect('EOL')
        return Node('IMPORT', (name,))

    def _stmt(self):
        if self._lookahead.type == 'LET':
            return self._let()
        elif self._lookahead.type == 'IF':
            return self._if()
        elif self._lookahead.type == 'WHILE':
            return self._while()
        else:
            node = self._test()
            if self._lookahead.type in ['ASSN', 'PLUS_ASSN', 'MINUS_ASSN',
                    'MULT_ASSN', 'DIV_ASSN', 'COLON']:
                lvl = 0
                while self._lookahead.type == 'COLON':
                    self._next()
                    lvl += 1
                op = self._lookahead.type
                self._next()
                r = self._test()
                node = Node('ASSN', (node, r), op, lvl)
            else:
                node = Node('EXPR', (node,))
            self._expect('EOL')
            return node

    def _let(self):
        self._expect('LET')
        name = self._id()
        tp = self._type()
        self._expect('EOL')
        return Node('LET', (name, tp))

    def _if(self):
        self._expect('IF')
        cond = self._test()
        self._expect('EOL')
        succ = self._block()
        if self._lookahead.type == 'ELSE':
            self._next()
            self._expect('EOL')
            fail = self._block()
        else:
            fail = self._empty()
        return Node('IF', (cond, succ, fail))

    def _while(self):
        self._expect('WHILE')
        cond = self._test()
        self._expect('EOL')
        cont = self._block()
        if self._lookahead.type == 'ELSE':
            self._next()
            self._expect('EOL')
            fail = self._block()
        else:
            fail = self._empty()
        return Node('WHILE', (cond, cont, fail))

    def _type(self):
        children = [self._id()]
        while self._lookahead.type == 'AMP':
            self._next()
            children.append(Node('AMP', ()))
        return Node('TYPE', children)

    def _block(self):
        stmts = []
        self._expect('INDENT')
        while self._lookahead.type != 'DEDENT':
            stmts.append(self._stmt())
        self._next()
        return Node('STMTS', stmts)

    def _args(self):
        args = []
        self._expect('LPAREN')
        if self._lookahead.type == 'RPAREN':
            self._next()
        else:
            while True:
                args.append(self._test())

                t = self._expect('COMMA', 'RPAREN')
                if t.type == 'RPAREN':
                    break
        return Node('ARGS', args)

    def _test(self):
        return self._comp()

    def _comp(self):
        node = self._expr()
        if self._lookahead.type in ['EQ', 'NE', 'LT', 'GT', 'LE', 'GE']:
            op = self._lookahead.type
            self._next()
            r = self._expr()
            node = Node('COMP', (node, r), op)
        return node

    def _expr(self):
        node = self._term()
        while self._lookahead.type in ['PLUS', 'MINUS']:
            op = self._lookahead.type
            self._next()
            r = self._term()
            node = Node('BIN', (node, r), op)
        return node

    def _term(self):
        node = self._factor()
        while self._lookahead.type in ['MULT', 'DIV']:
            op = self._lookahead.type
            self._next()
            r = self._factor()
            node = Node('BIN', (node, r), op)
        return node

    def _factor(self):
        if self._lookahead.type == 'ID':
            node = self._id()
            if self._lookahead.type != 'LPAREN':
                return node

            args = self._args()
            return Node('CALL', (node, args))

        elif self._lookahead.type == 'NUM':
            val = self._lookahead.value
            self._next()
            return Node('NUM', (), val)

        elif self._lookahead.type == 'LPAREN':
            self._next()
            test = self._test()
            self._expect('RPAREN')
            return test

        else:
            # this will always raise an error
            self._expect('ID', 'NUM', 'LPAREN')

    def _id(self):
        name = self._expect('ID').value
        return Node('ID', (), name)


if __name__ == '__main__':
    with open('meta/lex') as f:
        lexer = Lexer(f)
    parser = Parser()
    root = parser.parse(lexer.read(sys.stdin))
    root.analyze()
    root.print()
