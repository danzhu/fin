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
        if len(types) == 0:
            self._error('unexpected token {}'.format(self._lookahead.type))

        if self._lookahead.type not in types:
            self._error('expecting {}, but got {}'.format(
                ' or '.join(types),
                self._lookahead.type))

        self._next()

    def _error(self, msg):
        raise SyntaxError(msg
                + '\nat line {0.line}, col {0.column}'.format(self._lookahead))

    def _empty(self):
        return Node('EMPTY', ())

    def _file(self):
        children = []
        while self._lookahead.type != 'EOF':
            if self._lookahead.type == 'IMPORT':
                children.append(self._import())
            elif self._lookahead.type == 'DEF':
                children.append(self._def())
            elif self._lookahead.type == 'STRUCT':
                children.append(self._struct())
            else:
                children.append(self._stmt())
        return Node('FILE', children)

    def _import(self):
        self._expect('IMPORT')
        name = self._id()
        self._expect('EOL')
        return Node('IMPORT', (name,))

    def _struct(self):
        self._expect('STRUCT')
        name = self._id()
        self._expect('EOL')
        fields = self._fields()
        return Node('STRUCT', (name, fields))

    def _fields(self):
        self._expect('INDENT')
        children = []
        while self._lookahead.type != 'DEDENT':
            children.append(self._field())
        self._next() # DEDENT
        self._expect('EOL')
        return Node('FIELDS', children)

    def _field(self):
        name = self._id()
        tp = self._type()
        self._expect('EOL')
        return Node('FIELD', (name, tp))

    def _def(self):
        self._expect('DEF')

        name = self._id()
        params = self._params()

        if self._lookahead.type == 'EOL':
            ret = Node('TYPE', ())
        else:
            ret = self._type()

        self._expect('EOL')

        cont = self._block()
        self._expect('EOL')
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
            node = self._let()
        else:
            node = self._test()
        self._expect('EOL')
        return node

    def _let(self):
        self._expect('LET')
        name = self._id()
        tp = self._type()

        lvl = 0
        if self._lookahead.type in ['ASSN', 'COLON']:
            while self._lookahead.type == 'COLON':
                self._next()
                lvl += 1
            self._expect('ASSN')
            val = self._test()

        elif self._lookahead.type == 'EOL':
            val = self._empty()

        else:
            self._expect()

        return Node('LET', (name, tp, val), None, lvl)

    def _if(self):
        self._expect('IF')
        cond = self._test()
        self._expect('EOL')
        succ = self._block()
        fail = self._else()
        return Node('IF', (cond, succ, fail))

    def _else(self):
        if self._lookahead.type == 'ELIF':
            self._next()
            cond = self._test()
            self._expect('EOL')
            succ = self._block()
            fail = self._else()
            return Node('IF', (cond, succ, fail))

        elif self._lookahead.type == 'ELSE':
            self._next()
            self._expect('EOL')
            return self._block()

        else:
            return self._empty()

    def _while(self):
        self._expect('WHILE')
        cond = self._test()
        self._expect('EOL')
        cont = self._block()
        return Node('WHILE', (cond, cont))

    def _begin(self):
        self._expect('BEGIN')
        self._expect('EOL')
        return self._block()

    def _return(self):
        self._expect('RETURN')
        if self._lookahead.type == 'EOL':
            children = ()
        else:
            children = (self._test(),)
        return Node('RETURN', children)

    def _param(self):
        name = self._id()
        tp = self._type()
        return Node('PARAM', (name, tp))

    def _type(self):
        name = self._id()
        lvl = 0
        while self._lookahead.type == 'AMP':
            self._next()
            lvl += 1
        return Node('TYPE', (name,), None, lvl)

    def _block(self):
        stmts = []
        self._expect('INDENT')
        while self._lookahead.type != 'DEDENT':
            stmts.append(self._stmt())
        self._next()
        return Node('BLOCK', stmts)

    def _args(self):
        return Node('ARGS', args)

    def _test(self):
        node = self._or_test()

        if self._lookahead.type not in ['ASSN', 'INC_ASSN', 'COLON']:
            return node

        lvl = 0

        tp = self._lookahead.type
        if tp == 'INC_ASSN':
            op = self._lookahead.variant
            self._next()

        else:
            tp = 'ASSN'
            while self._lookahead.type == 'COLON':
                self._next()
                lvl += 1
            op = None
            self._expect('ASSN')

        val = self._test()
        return Node(tp, (node, val), op, lvl)

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
        if self._lookahead.type == 'COMP':
            op = self._lookahead.variant
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
        if self._lookahead.type in ['ADD', 'SUB']:
            op = self._lookahead.type
            self._next()
            val = self._factor()
            return Node('UNARY', (val,), op)
        else:
            return self._atom()

    def _atom(self):
        if self._lookahead.type == 'ID':
            name = self._lookahead.value
            self._next() # ID

            if self._lookahead.type == 'LPAREN':
                children = [Node('ID', (), name)]
                self._next() # LPAREN
                if self._lookahead.type == 'RPAREN':
                    self._next() # RPAREN
                else:
                    while True:
                        children.append(self._test())

                        tp = self._lookahead.type
                        self._expect('COMMA', 'RPAREN')
                        if tp == 'RPAREN':
                            break
                return Node('CALL', children)

            node = Node('VAR', (), name)
            while self._lookahead.type == 'DOT':
                self._next() # DOT
                field = self._id()
                node = Node('MEMBER', (node, field))

            return node

        elif self._lookahead.type in ['NUM', 'FLOAT']:
            tp = self._lookahead.type
            val = self._lookahead.value
            self._next()
            return Node(tp, (), val)

        elif self._lookahead.type == 'LPAREN':
            self._next()
            test = self._test()
            self._expect('RPAREN')
            return test

        elif self._lookahead.type == 'IF':
            return self._if()

        elif self._lookahead.type == 'WHILE':
            return self._while()

        elif self._lookahead.type == 'BEGIN':
            return self._begin()

        elif self._lookahead.type == 'RETURN':
            return self._return()

        else:
            self._expect()

    def _id(self):
        name = self._lookahead.value
        self._expect('ID')
        return Node('ID', (), name)
