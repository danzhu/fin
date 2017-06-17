import sys
from lexer import Lexer
from node import Node
from error import ParserError

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
        raise ParserError(msg, self._lookahead)

    def _args(self):
        self._expect('LPAREN')
        if self._lookahead.type == 'RPAREN':
            self._next()
            return []

        children = []
        while True:
            children.append(self._test())

            tp = self._lookahead.type
            self._expect('COMMA', 'RPAREN')
            if tp == 'RPAREN':
                break

        return children

    def _empty(self):
        return Node('EMPTY', self._lookahead, ())

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
        return Node('FILE', None, children)

    def _import(self):
        token = self._lookahead
        self._expect('IMPORT')
        name = self._name()
        self._expect('EOL')
        return Node('IMPORT', token, (), name)

    def _struct(self):
        token = self._lookahead
        self._expect('STRUCT')
        name = self._name()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = self._empty()

        self._expect('EOL')

        fields = self._fields()
        self._expect('EOL')

        return Node('STRUCT', token, (gens, fields), name)

    def _gens(self):
        children = []
        self._expect('LBRACE')

        while True:
            children.append(self._gen())

            tp = self._lookahead.type
            self._expect('COMMA', 'RBRACE')

            if tp == 'RBRACE':
                break

        return Node('GENS', None, children)

    def _gen(self):
        token = self._lookahead
        self._expect('ID')
        return Node('GEN', token, (), token.value)

    def _fields(self):
        self._expect('INDENT')

        children = []
        while self._lookahead.type != 'DEDENT':
            children.append(self._field())

        self._next() # DEDENT

        return Node('FIELDS', None, children)

    def _field(self):
        token = self._lookahead
        name = self._name()
        tp = self._type()
        self._expect('EOL')
        return Node('FIELD', token, (tp,), name)

    def _def(self):
        token = self._lookahead
        self._expect('DEF')

        name = self._name()
        params = self._params()

        if self._lookahead.type == 'EOL':
            ret = self._empty()
        else:
            ret = self._type()

        self._expect('EOL')

        cont = self._block()
        self._expect('EOL')
        return Node('DEF', token, (params, ret, cont), name)

    def _params(self):
        token = self._lookahead
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
        return Node('PARAMS', token, children)

    def _stmt(self):
        if self._lookahead.type == 'LET':
            node = self._let()
        else:
            node = self._test()
        self._expect('EOL')
        return node

    def _let(self):
        token = self._lookahead
        self._expect('LET')
        name = self._name()

        if self._lookahead.type in ['ASSN', 'COLON', 'EOL']:
            tp = self._empty()
        else:
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

        return Node('LET', token, (tp, val), name, lvl)

    def _if(self):
        token = self._lookahead
        self._expect('IF')
        cond = self._test()
        self._expect('EOL')
        succ = self._block()
        fail = self._else()
        return Node('IF', token, (cond, succ, fail))

    def _else(self):
        if self._lookahead.type == 'ELIF':
            token = self._lookahead
            self._next()
            cond = self._test()
            self._expect('EOL')
            succ = self._block()
            fail = self._else()
            return Node('IF', token, (cond, succ, fail))

        elif self._lookahead.type == 'ELSE':
            self._next()
            self._expect('EOL')
            return self._block()

        else:
            return self._empty()

    def _while(self):
        token = self._lookahead
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

        return Node('WHILE', token, (cond, cont, fail))

    def _begin(self):
        self._expect('BEGIN')
        self._expect('EOL')
        return self._block()

    def _return(self):
        token = self._lookahead
        self._expect('RETURN')
        if self._lookahead.type != 'EOL':
            val = self._test()
        else:
            val = self._empty()

        return Node('RETURN', token, (val,))

    def _param(self):
        token = self._lookahead
        name = self._name()
        tp = self._type()
        return Node('PARAM', token, (tp,), name)

    def _type(self):
        token = self._lookahead

        if self._lookahead.type == 'AMP':
            lvl = 0
            while self._lookahead.type == 'AMP':
                self._next()
                lvl += 1

            node = self._type()
            return Node('REF', token, (node,), None, lvl)

        if self._lookahead.type == 'LBRACKET':
            self._next() # LBRACKET
            node = self._type()

            if self._lookahead.type == 'SEMICOLON':
                self._next()

                num = self._lookahead
                self._expect('NUM')
                size = Node(num.type, num, (), num.value)
            else:
                size = self._empty()

            self._expect('RBRACKET')
            return Node('ARRAY', token, (node, size))

        if self._lookahead.type == 'ID':
            name = self._name()

            children = []
            if self._lookahead.type == 'LBRACE':
                self._next()

                while True:
                    children.append(self._type())

                    tp = self._lookahead.type
                    self._expect('COMMA', 'RBRACE')
                    if tp == 'RBRACE':
                        break

            return Node('TYPE', token, children, name)

        self._expect()

    def _block(self):
        token = self._lookahead
        stmts = []
        self._expect('INDENT')
        while self._lookahead.type != 'DEDENT':
            stmts.append(self._stmt())
        self._next()
        return Node('BLOCK', token, stmts)

    def _test(self):
        node = self._or_test()

        if self._lookahead.type not in ['ASSN', 'INC_ASSN', 'COLON']:
            return node

        if self._lookahead.type == 'INC_ASSN':
            token = self._lookahead
            op = self._lookahead.variant.split('_', 1)[0].lower()
            self._next() # INC_ASSN
            val = self._test()
            return Node('INC_ASSN', token, (node, val), op)

        token = self._lookahead
        lvl = 0
        while self._lookahead.type == 'COLON':
            self._next()
            lvl += 1
        op = None
        self._expect('ASSN')

        val = self._test()
        return Node('ASSN', token, (node, val), op, lvl)

    def _or_test(self):
        node = self._and_test()
        while self._lookahead.type == 'OR':
            token = self._lookahead
            self._next()
            r = self._and_test()
            node = Node('TEST', token, (node, r), 'OR')
        return node

    def _and_test(self):
        node = self._not_test()
        while self._lookahead.type == 'AND':
            token = self._lookahead
            self._next()
            r = self._not_test()
            node = Node('TEST', token, (node, r), 'AND')
        return node

    def _not_test(self):
        if self._lookahead.type == 'NOT':
            token = self._lookahead
            self._next()
            val = self._not_test()
            return Node('TEST', token, (val,), 'NOT')
        else:
            return self._comp()

    def _comp(self):
        node = self._expr()
        if self._lookahead.type == 'COMP':
            token = self._lookahead
            if self._lookahead.variant == 'EQ':
                op = 'equal'
            elif self._lookahead.variant == 'NE':
                op = 'notEqual'
            elif self._lookahead.variant == 'LT':
                op = 'less'
            elif self._lookahead.variant == 'LE':
                op = 'lessEqual'
            elif self._lookahead.variant == 'GT':
                op = 'greater'
            elif self._lookahead.variant == 'GE':
                op = 'greaterEqual'
            else:
                assert False
            self._next()
            r = self._expr()
            node = Node('CALL', token, (node, r), op)
        return node

    def _expr(self):
        node = self._term()
        while self._lookahead.type in ['PLUS', 'MINUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._term()
            node = Node('CALL', token, (node, r), op)
        return node

    def _term(self):
        node = self._factor()
        while self._lookahead.type in ['MULTIPLIES', 'DIVIDES', 'MODULUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._factor()
            node = Node('CALL', token, (node, r), op)
        return node

    def _factor(self):
        if self._lookahead.type in ['PLUS', 'MINUS']:
            token = self._lookahead
            if self._lookahead.type == 'PLUS':
                op = 'pos'
            elif self._lookahead.type == 'MINUS':
                op = 'neg'
            else:
                assert False
            self._next()
            val = self._factor()
            return Node('CALL', token, (val,), op)
        else:
            return self._atom_expr()

    def _atom_expr(self):
        node = self._atom()

        while True:
            if self._lookahead.type == 'DOT':
                self._next() # DOT
                token = self._lookahead
                name = self._name()

                if self._lookahead.type == 'LPAREN':
                    # method call
                    args = self._args()
                    node = Node('CALL', token, [node] + args, name)
                else:
                    # member access
                    node = Node('MEMBER', token, (node,), name)

            elif self._lookahead.type == 'LBRACKET':
                token = self._lookahead
                self._next() # LBRACKET
                idx = self._test()
                self._expect('RBRACKET')
                node = Node('CALL', token, (node, idx), '[]')

            else:
                break

        return node


    def _atom(self):
        if self._lookahead.type == 'ID':
            token = self._lookahead
            name = self._name()

            if self._lookahead.type == 'LPAREN':
                args = self._args()
                return Node('CALL', token, args, name)
            else:
                return Node('VAR', token, (), name)

        elif self._lookahead.type in ['NUM', 'FLOAT']:
            token = self._lookahead
            tp = self._lookahead.type
            val = self._lookahead.value
            self._next()
            return Node(tp, token, (), val)

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

        elif self._lookahead.type == 'BREAK':
            token = self._lookahead
            self._next()
            if self._lookahead.type != 'EOL':
                val = self._test()
            else:
                val = self._empty()

            return Node('BREAK', token, (val,))

        elif self._lookahead.type in ['CONTINUE', 'REDO']:
            token = self._lookahead
            tp = self._lookahead.type
            self._next()
            return Node(tp, token, ())

        else:
            self._expect()

    def _name(self):
        name = self._lookahead.value
        self._expect('ID')
        return name
