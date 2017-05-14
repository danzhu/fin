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
        if self._lookahead.type not in types:
            self._error('expected {}, but got {}'.format(
                ' or '.join(types),
                self._lookahead.type))
        self._next()

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
            elif self._lookahead.type == 'DEF':
                children.append(self._def())
            else:
                children.append(self._stmt())
        return Node('FILE', children)

    def _import(self):
        self._expect('IMPORT')
        name = self._id()
        self._expect('EOL')
        return Node('IMPORT', (name,))

    def _def(self):
        self._expect('DEF')

        name = self._id()
        params = self._params()

        if self._lookahead.type == 'EOL':
            # TODO: should we create this in _type()?
            ret = Node('TYPE', ())
        else:
            ret = self._type()

        self._expect('EOL')

        cont = self._block()
        return Node('DEF', (name, params, ret, cont))

    def _params(self):
        self._expect('LPAREN')
        children = []
        if self._lookahead.type == 'RPAREN':
            self._next()
        else:
            while True:
                children.append(self._param())

                tp = self._lookahead.type
                self._expect('COMMA', 'RPAREN')
                if tp == 'RPAREN':
                    break
        return Node('PARAMS', children)

    def _stmt(self):
        if self._lookahead.type == 'LET':
            return self._let()
        elif self._lookahead.type == 'IF':
            return self._if()
        elif self._lookahead.type == 'WHILE':
            return self._while()
        elif self._lookahead.type == 'RETURN':
            return self._return()
        else:
            node = self._test()
            if self._lookahead.type in ['ASSN', 'ADD_ASSN', 'SUB_ASSN',
                    'MULT_ASSN', 'DIV_ASSN', 'MOD_ASSN', 'COLON']:
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

    def _return(self):
        self._expect('RETURN')
        if self._lookahead.type == 'EOL':
            children = ()
        else:
            children = (self._test(),)
        self._expect('EOL')
        return Node('RETURN', children)

    def _param(self):
        name = self._id()
        tp = self._type()
        return Node('PARAM', (name, tp))

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
        return Node('ARGS', args)

    def _test(self):
        return self._or_test()

    def _or_test(self):
        node = self._and_test()
        while self._lookahead.type == 'OR':
            self._next()
            r = self._and_test()
            node = Node('TEST', (node, r), 'OR')
        return node

    def _and_test(self):
        node = self._comp()
        while self._lookahead.type == 'AND':
            self._next()
            r = self._comp()
            node = Node('TEST', (node, r), 'AND')
        return node

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
        while self._lookahead.type in ['ADD', 'SUB']:
            op = self._lookahead.type
            self._next()
            r = self._term()
            node = Node('BIN', (node, r), op)
        return node

    def _term(self):
        node = self._factor()
        while self._lookahead.type in ['MULT', 'DIV', 'MOD']:
            op = self._lookahead.type
            self._next()
            r = self._factor()
            node = Node('BIN', (node, r), op)
        return node

    def _factor(self):
        if self._lookahead.type == 'ID':
            name = self._lookahead.value
            self._expect('ID')
            if self._lookahead.type != 'LPAREN':
                return Node('VAR', (), name)

            children = [Node('ID', (), name)]
            self._next()
            if self._lookahead.type == 'RPAREN':
                self._next()
            else:
                while True:
                    children.append(self._test())

                    tp = self._lookahead.type
                    self._expect('COMMA', 'RPAREN')
                    if tp == 'RPAREN':
                        break
            return Node('CALL', children)

        elif self._lookahead.type == 'NUM':
            val = self._lookahead.value
            self._next()
            return Node('NUM', (), val)

        elif self._lookahead.type == 'FLOAT':
            val = self._lookahead.value
            self._next()
            return Node('FLOAT', (), val)

        elif self._lookahead.type == 'LPAREN':
            self._next()
            test = self._test()
            self._expect('RPAREN')
            return test

        else:
            # this will always raise an error
            self._expect('ID', 'NUM', 'LPAREN')

    def _id(self):
        name = self._lookahead.value
        self._expect('ID')
        return Node('ID', (), name)
