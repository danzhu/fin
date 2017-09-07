from typing import Iterator, List, Callable
from . import error
from . import node
from . import tokens


class Parser:
    def __init__(self) -> None:
        self._src: Iterator[tokens.Token] = None
        self._lookahead: tokens.Token = None

    def parse(self, src: Iterator[tokens.Token]):
        self._src = src
        self._next()
        return self._file()

    def _next(self) -> None:
        self._lookahead = next(self._src)

    def _expect(self, *types: str) -> None:
        if len(types) == 0:
            self._error(f'unexpected token {self._lookahead.type}')

        if self._lookahead.type not in types:
            tps = ' or '.join(types)
            self._error(f'expecting {tps}, but got {self._lookahead.type}')

        self._next()

    def _error(self, msg: str):
        raise error.ParserError(msg, self._lookahead)

    def _id(self) -> str:
        name = self._lookahead.value
        self._expect('ID')
        return name

    def _params(self, fn: Callable[[], node.Node]) -> List[node.Node]:
        self._expect('LPAREN')
        if self._lookahead.type == 'RPAREN':
            self._next()
            return []

        children = []
        while True:
            children.append(fn())

            tp = self._lookahead.type
            self._expect('COMMA', 'RPAREN')
            if tp == 'RPAREN':
                break

        return children

    def _children(self, tp: str, fn: Callable[[], node.Node]) -> node.Node:
        self._expect('INDENT')

        children = []
        while self._lookahead.type != 'DEDENT':
            children.append(fn())

        self._next()  # DEDENT

        return node.Node(tp, None, children)

    def _empty(self) -> node.Node:
        return node.Node('EMPTY', self._lookahead, ())

    def _file(self) -> node.Node:
        children = []
        while self._lookahead.type != 'EOF':
            if self._lookahead.type == 'IMPORT':
                children.append(self._import())
            elif self._lookahead.type == 'DEF':
                children.append(self._def())
            elif self._lookahead.type == 'STRUCT':
                children.append(self._struct())
            elif self._lookahead.type == 'ENUM':
                children.append(self._enum())
            else:
                self._expect()

        return node.Node('FILE', None, children)

    def _import(self) -> node.Node:
        token = self._lookahead
        self._expect('IMPORT')
        name = self._name()
        self._expect('EOL')
        return node.Node('IMPORT', token, (name,))

    def _pattern(self) -> node.Node:
        token = self._lookahead

        if token.type == 'UNDERSCORE':
            self._next()
            return node.Node('PAT_ANY', token, ())

        if token.type in ('NUM', 'FLOAT'):
            self._next()
            return node.Node(f'PAT_{token.type}', token, (), token.value)

        name = self._name()

        if self._lookahead.type != 'LPAREN':
            return node.Node('PAT_VAR', token, (name,))

        children = node.Node('PAT_PARAMS', None, self._params(self._pattern))
        return node.Node('PAT_STRUCT', token, (name, children))

    def _gens(self) -> node.Node:
        children = []
        self._expect('LBRACE')

        while True:
            token = self._lookahead
            name = self._id()

            children.append(node.Node('ID', token, (), name))

            tp = self._lookahead.type
            self._expect('COMMA', 'RBRACE')

            if tp == 'RBRACE':
                break

        return node.Node('GEN_PARAMS', None, children)

    def _struct(self) -> node.Node:
        self._expect('STRUCT')
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = self._empty()

        fields = self._children('FIELDS', self._field)
        self._expect('EOL')

        return node.Node('STRUCT', token, (gens, fields), name)

    def _field(self) -> node.Node:
        token = self._lookahead
        name = self._id()
        tp = self._type()
        self._expect('EOL')
        return node.Node('FIELD', token, (tp,), name)

    def _enum(self) -> node.Node:
        self._expect('ENUM')
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = self._empty()

        variants = self._children('VARIANTS', self._variant)
        self._expect('EOL')

        return node.Node('ENUM', token, (gens, variants), name)

    def _variant(self) -> node.Node:
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LPAREN':
            params = self._params(self._param)
        else:
            params = []

        self._expect('EOL')

        return node.Node('VARIANT', token, params, name)

    def _def(self) -> node.Node:
        self._expect('DEF')
        token = self._lookahead

        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = self._empty()

        params = node.Node('PARAMS', None, self._params(self._param))

        if self._lookahead.type != 'INDENT':
            ret = self._type()
        else:
            ret = self._empty()

        cont = self._block()
        self._expect('EOL')
        return node.Node('DEF', token, (gens, params, ret, cont), name)

    def _let(self) -> node.Node:
        token = self._lookahead
        self._expect('LET')
        name = self._id()

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

        return node.Node('LET', token, (tp, val), name, lvl)

    def _if(self) -> node.Node:
        token = self._lookahead
        self._expect('IF')
        cond = self._block()
        self._expect('THEN')
        succ = self._block()
        if self._lookahead.type == 'ELSE':
            self._next()  # ELSE
            fail = self._block()
        else:
            fail = self._empty()

        return node.Node('IF', token, (cond, succ, fail))

    def _match(self) -> node.Node:
        token = self._lookahead
        self._expect('MATCH')
        val = self._test()
        arms = self._children('ARMS', self._arm)
        return node.Node('MATCH', token, (val, arms))

    def _arm(self) -> node.Node:
        pat = node.Node('PATTERN', None, (self._pattern(),))

        tp = self._lookahead.type
        self._expect('ARM', 'EOL')

        if tp == 'ARM':
            cont = self._test()
        elif tp == 'EOL':
            cont = self._block()
        else:
            assert False

        self._expect('EOL')

        return node.Node('ARM', None, (pat, cont))

    def _while(self) -> node.Node:
        token = self._lookahead
        self._expect('WHILE')
        cond = self._block()
        self._expect('DO')
        cont = self._block()

        if self._lookahead.type == 'ELSE':
            self._next()  # ELSE
            fail = self._block()
        else:
            fail = self._empty()

        return node.Node('WHILE', token, (cond, cont, fail))

    def _param(self) -> node.Node:
        token = self._lookahead
        name = self._id()
        tp = self._type()
        return node.Node('PARAM', token, (tp,), name)

    def _name(self) -> node.Node:
        token = self._lookahead
        name = self._id()

        n = node.Node('ID', token, (), name)

        while self._lookahead.type == 'SCOPE':
            self._next()
            token = self._lookahead
            member = node.Node('ID', self._lookahead, (), self._id())
            n = node.Node('SCOPE', token, (n, member))

        return n

    def _type(self) -> node.Node:
        token = self._lookahead

        if self._lookahead.type == 'AMP':
            lvl = 0
            while self._lookahead.type == 'AMP':
                self._next()
                lvl += 1

            tp = self._type()
            return node.Node('REF', token, (tp,), None, lvl)

        if self._lookahead.type == 'LBRACKET':
            self._next()  # LBRACKET
            tp = self._type()

            if self._lookahead.type == 'SEMICOLON':
                self._next()

                num = self._lookahead
                self._expect('NUM')
                size = node.Node(num.type, num, (), num.value)
            else:
                size = self._empty()

            self._expect('RBRACKET')
            return node.Node('ARRAY', token, (tp, size))

        if self._lookahead.type == 'ID':
            name = self._name()

            children = []
            if self._lookahead.type == 'LBRACE':
                self._next()

                while True:
                    children.append(self._type())

                    sym = self._lookahead.type
                    self._expect('COMMA', 'RBRACE')
                    if sym == 'RBRACE':
                        break

            gens = node.Node('GEN_ARGS', None, children)
            return node.Node('TYPE', token, (name, gens))

        self._expect()
        assert False

    def _block(self) -> node.Node:
        stmts = []

        if self._lookahead.type == 'INDENT':
            self._next()  # INDENT
            while self._lookahead.type != 'DEDENT':
                if self._lookahead.type == 'LET':
                    stmt = self._let()
                else:
                    stmt = self._test()

                self._expect('EOL')
                stmts.append(stmt)

            self._next()
        else:
            stmts.append(self._test())

        return node.Node('BLOCK', None, stmts)

    def _test(self) -> node.Node:
        n = self._or_test()

        if self._lookahead.type not in ['ASSN', 'INC_ASSN', 'COLON']:
            return n

        if self._lookahead.type == 'INC_ASSN':
            token = self._lookahead
            op = self._lookahead.variant.split('_', 1)[0].lower()
            self._next()  # INC_ASSN
            val = self._test()
            return node.Node('INC_ASSN', token, (n, val), op)

        token = self._lookahead
        lvl = 0
        while self._lookahead.type == 'COLON':
            self._next()
            lvl += 1
        op = None
        self._expect('ASSN')

        val = self._test()
        return node.Node('ASSN', token, (n, val), op, lvl)

    def _or_test(self) -> node.Node:
        n = self._and_test()
        while self._lookahead.type == 'OR':
            token = self._lookahead
            self._next()
            r = self._and_test()
            n = node.Node('TEST', token, (n, r), 'OR')
        return n

    def _and_test(self) -> node.Node:
        n = self._not_test()
        while self._lookahead.type == 'AND':
            token = self._lookahead
            self._next()
            r = self._not_test()
            n = node.Node('TEST', token, (n, r), 'AND')
        return n

    def _not_test(self) -> node.Node:
        if self._lookahead.type == 'NOT':
            token = self._lookahead
            self._next()
            val = self._not_test()
            return node.Node('TEST', token, (val,), 'NOT')

        return self._comp()

    def _comp(self) -> node.Node:
        n = self._expr()
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
            n = node.Node('OP', token, (n, r), op)
        return n

    def _expr(self) -> node.Node:
        n = self._term()
        while self._lookahead.type in ['PLUS', 'MINUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._term()
            n = node.Node('OP', token, (n, r), op)
        return n

    def _term(self) -> node.Node:
        n = self._factor()
        while self._lookahead.type in ['MULTIPLIES', 'DIVIDES', 'MODULUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._factor()
            n = node.Node('OP', token, (n, r), op)
        return n

    def _factor(self) -> node.Node:
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
            return node.Node('OP', token, (val,), op)
        else:
            return self._atom_expr()

    def _atom_expr(self) -> node.Node:
        n = self._atom()

        while True:
            if self._lookahead.type == 'DOT':
                self._next()  # DOT
                token = self._lookahead
                name = self._name()

                if self._lookahead.type == 'LPAREN':
                    # method call
                    children = [n] + self._params(self._test)
                    args = node.Node('ARGS', None, children)
                    n = node.Node('CALL', token, (name, args))
                else:
                    # member access
                    n = node.Node('MEMBER', token, (n, name))

            elif self._lookahead.type == 'LBRACKET':
                token = self._lookahead
                self._next()  # LBRACKET
                idx = self._test()
                self._expect('RBRACKET')
                n = node.Node('OP', token, (n, idx), 'subscript')

            elif self._lookahead.type == 'ARROW':
                token = self._lookahead
                self._next()
                tp = self._type()
                n = node.Node('CAST', token, (n, tp))

            else:
                break

        return n

    def _atom(self) -> node.Node:
        if self._lookahead.type == 'ID':
            token = self._lookahead
            name = self._name()

            if self._lookahead.type == 'LPAREN':
                args = node.Node('ARGS', None, self._params(self._test))
                return node.Node('CALL', token, (name, args))

            return node.Node('VAR', token, (name,))

        if self._lookahead.type in ['NUM', 'FLOAT']:
            return self._const()

        if self._lookahead.type == 'LPAREN':
            self._next()
            test = self._test()
            self._expect('RPAREN')
            return test

        if self._lookahead.type == 'IF':
            return self._if()

        if self._lookahead.type == 'MATCH':
            return self._match()

        if self._lookahead.type == 'WHILE':
            return self._while()

        if self._lookahead.type == 'BEGIN':
            self._expect('BEGIN')
            return self._block()

        if self._lookahead.type == 'RETURN':
            token = self._lookahead
            self._next()  # RETURN
            # FIXME: hacks
            if self._lookahead.type not in ('EOL', 'THEN', 'DO', 'ELSE'):
                val = self._test()
            else:
                val = self._empty()

            return node.Node('RETURN', token, (val,))

        if self._lookahead.type == 'BREAK':
            token = self._lookahead
            self._next()  # BREAK
            # FIXME: hacks
            if self._lookahead.type not in ('EOL', 'THEN', 'DO', 'ELSE'):
                val = self._test()
            else:
                val = self._empty()

            return node.Node('BREAK', token, (val,))

        if self._lookahead.type in ['CONTINUE', 'REDO']:
            token = self._lookahead
            tp = self._lookahead.type
            self._next()
            return node.Node(tp, token, ())

        self._expect()
        assert False

    def _const(self) -> node.Node:
        token = self._lookahead
        self._expect('NUM', 'FLOAT')
        return node.Node(token.type, token, (), token.value)
