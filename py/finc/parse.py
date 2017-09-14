from typing import Iterator, List, Callable
from . import error
from . import ast
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

    def _params(self,
                paren: str,
                fn: Callable[[], ast.TNode]) -> ast.List[ast.TNode]:
        self._expect(f'L{paren}')
        if self._lookahead.type == f'R{paren}':
            self._next()
            return ast.List([])

        children = []
        while True:
            children.append(fn())

            tp = self._lookahead.type
            self._expect('COMMA', f'R{paren}')
            if tp == f'R{paren}':
                break

        return ast.List(children)

    def _children(self,
                  fn: Callable[[], ast.TNode]) -> ast.List[ast.TNode]:
        self._expect('INDENT')

        children = []
        while self._lookahead.type != 'DEDENT':
            children.append(fn())
            self._expect('EOL')

        self._next()  # DEDENT

        return ast.List(children)

    def _file(self) -> ast.File:
        decls: List[ast.Decl] = []
        while self._lookahead.type != 'EOF':
            if self._lookahead.type == 'IMPORT':
                decls.append(self._import())
            elif self._lookahead.type == 'DEF':
                decls.append(self._def())
            elif self._lookahead.type == 'STRUCT':
                decls.append(self._struct())
            elif self._lookahead.type == 'ENUM':
                decls.append(self._enum())
            else:
                self._expect()

        return ast.File(decls)

    def _import(self) -> ast.Import:
        token = self._lookahead
        self._expect('IMPORT')
        path = self._path()
        self._expect('EOL')
        return ast.Import(path)

    def _pattern(self) -> ast.Pattern:
        token = self._lookahead

        if token.type == 'UNDERSCORE':
            self._next()
            return ast.PatternAny()

        if token.type in ('NUM', 'FLOAT'):
            tp = token.type.lower()
            self._next()
            return ast.PatternConst(token.value, tp)

        path = self._path()

        if self._lookahead.type != 'LPAREN':
            # if path is not a single id
            if path.path is not None:
                # this will always raise;
                # we expect a left parenthesis after path in pattern
                self._expect('LPAREN')

            # otherwise this is a variable pattern
            return ast.PatternVar(path.name)

        args = self._params('PAREN', self._pattern)
        return ast.PatternCall(path, args)

    def _gens(self) -> ast.List[ast.Generic]:
        children = []
        self._expect('LBRACE')

        while True:
            token = self._lookahead
            name = self._id()

            children.append(ast.Generic(name))

            tp = self._lookahead.type
            self._expect('COMMA', 'RBRACE')

            if tp == 'RBRACE':
                break

        return ast.List(children)

    def _struct(self) -> ast.Struct:
        self._expect('STRUCT')
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = ast.List([])

        fields = self._children(self._field)
        self._expect('EOL')

        return ast.Struct(name, gens, fields)

    def _field(self) -> ast.Field:
        token = self._lookahead
        name = self._id()
        tp = self._type()
        return ast.Field(name, tp)

    def _enum(self) -> ast.Enum:
        self._expect('ENUM')
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = ast.List([])

        variants = self._children(self._variant)
        self._expect('EOL')

        return ast.Enum(name, gens, variants)

    def _variant(self) -> ast.Variant:
        token = self._lookahead
        name = self._id()

        if self._lookahead.type == 'LPAREN':
            params = self._params('PAREN', self._field)
        else:
            params = ast.List([])

        return ast.Variant(name, params)

    def _def(self) -> ast.Def:
        self._expect('DEF')
        token = self._lookahead

        name = self._id()

        if self._lookahead.type == 'LBRACE':
            gens = self._gens()
        else:
            gens = ast.List([])

        params = self._params('PAREN', self._param)

        if self._lookahead.type != 'INDENT':
            ret = self._type()
        else:
            ret = None

        cont = self._block()
        self._expect('EOL')
        return ast.Def(name, gens, params, ret, cont)

    def _let(self) -> ast.Let:
        token = self._lookahead
        self._expect('LET')
        name = self._id()

        if self._lookahead.type not in ['ASSN', 'EOL']:
            tp = self._type()
        else:
            tp = None

        if self._lookahead.type == 'ASSN':
            self._next()  # ASSN
            val = self._test()

        elif self._lookahead.type == 'EOL':
            val = None

        else:
            self._expect()

        return ast.Let(name, tp, val)

    def _if(self) -> ast.If:
        token = self._lookahead
        self._expect('IF')
        cond = self._block()
        self._expect('THEN')
        succ = self._block()
        if self._lookahead.type == 'ELSE':
            self._next()  # ELSE
            fail = self._block()
        else:
            fail = ast.Noop()

        return ast.If(cond, succ, fail)

    def _match(self) -> ast.Match:
        token = self._lookahead
        self._expect('MATCH')
        val = self._test()
        arms = self._children(self._arm)
        return ast.Match(val, arms)

    def _arm(self) -> ast.Arm:
        pat = self._pattern()

        self._expect('ARM')
        cont = self._block()

        return ast.Arm(pat, cont)

    def _while(self) -> ast.While:
        token = self._lookahead
        self._expect('WHILE')
        cond = self._block()
        self._expect('DO')
        cont = self._block()

        if self._lookahead.type == 'ELSE':
            self._next()  # ELSE
            fail = self._block()
        else:
            fail = ast.Noop()

        return ast.While(cond, cont, fail)

    def _param(self) -> ast.Param:
        token = self._lookahead
        name = self._id()
        tp = self._type()
        return ast.Param(name, tp)

    def _path(self) -> ast.Path:
        token = self._lookahead
        name = self._id()

        n = ast.Path(None, name)

        while self._lookahead.type == 'COLON':
            self._next()
            token = self._lookahead
            n = ast.Path(n, self._id())

        return n

    def _type(self) -> ast.Type:
        token = self._lookahead

        if self._lookahead.type == 'AMP':
            self._next()  # AMP
            tp = self._type()
            return ast.TypeRef(tp)

        if self._lookahead.type == 'LBRACKET':
            self._next()  # LBRACKET
            tp = self._type()

            size = None
            if self._lookahead.type == 'SEMICOLON':
                self._next()

                num = self._lookahead
                self._expect('NUM')
                size = ast.Const(num.value, 'num')

            self._expect('RBRACKET')
            return ast.TypeArray(tp, size)

        if self._lookahead.type == 'ID':
            name = self._path()
            if self._lookahead.type == 'LBRACE':
                gens = self._params('BRACE', self._type)
            else:
                gens = ast.List([])

            return ast.TypeNamed(name, gens)

        self._expect()
        assert False

    def _block(self) -> ast.Expr:
        if self._lookahead.type != 'INDENT':
            return self._test()

        self._next()  # INDENT
        stmts: List[ast.Expr] = []
        while self._lookahead.type != 'DEDENT':
            stmt: ast.Expr
            if self._lookahead.type == 'LET':
                stmt = self._let()
            else:
                stmt = self._test()

            self._expect('EOL')
            stmts.append(stmt)

        self._next()  # DEDENT
        return ast.Block(stmts)

    def _test(self) -> ast.Expr:
        n = self._or_test()

        if self._lookahead.type == 'ASSN':
            token = self._lookahead
            self._next()  # ASSN

            val = self._test()
            return ast.Assn(n, val)

        if self._lookahead.type == 'INC_ASSN':
            token = self._lookahead
            # PLUS_ASSN -> plus
            op = self._lookahead.variant.split('_', 1)[0].lower()
            self._next()  # INC_ASSN

            val = self._test()
            return ast.IncAssn(n, op, val)

        return n

    def _or_test(self) -> ast.Expr:
        n = self._and_test()
        while self._lookahead.type == 'OR':
            token = self._lookahead
            self._next()
            r = self._and_test()
            n = ast.BinTest(n, 'or', r)

        return n

    def _and_test(self) -> ast.Expr:
        n = self._not_test()
        while self._lookahead.type == 'AND':
            token = self._lookahead
            self._next()
            r = self._not_test()
            n = ast.BinTest(n, 'and', r)

        return n

    def _not_test(self) -> ast.Expr:
        if self._lookahead.type != 'NOT':
            return self._comp()

        token = self._lookahead
        self._next()
        val = self._not_test()
        return ast.NotTest(val)

    def _comp(self) -> ast.Expr:
        n = self._expr()
        if self._lookahead.type != 'COMP':
            return n

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

        self._next()  # COMP
        r = self._expr()
        return ast.Op(op, ast.List([n, r]))

    def _expr(self) -> ast.Expr:
        n: ast.Expr = self._term()
        while self._lookahead.type in ['PLUS', 'MINUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._term()
            n = ast.Op(op, ast.List([n, r]))

        return n

    def _term(self) -> ast.Expr:
        n = self._factor()
        while self._lookahead.type in ['MULTIPLIES', 'DIVIDES', 'MODULUS']:
            token = self._lookahead
            op = self._lookahead.type.lower()
            self._next()
            r = self._factor()
            n = ast.Op(op, ast.List([n, r]))

        return n

    def _factor(self) -> ast.Expr:
        if self._lookahead.type not in ['PLUS', 'MINUS']:
            return self._atom_expr()

        token = self._lookahead
        if self._lookahead.type == 'PLUS':
            op = 'pos'
        elif self._lookahead.type == 'MINUS':
            op = 'neg'
        else:
            assert False, 'unreachable'

        self._next()
        val = self._factor()
        return ast.Op(op, ast.List([val]))

    def _atom_expr(self) -> ast.Expr:
        n = self._atom()

        while True:
            if self._lookahead.type == 'DOT':
                self._next()  # DOT
                token = self._lookahead
                name = self._path()

                if self._lookahead.type == 'LPAREN':
                    # method call
                    args = self._params('PAREN', self._test)
                    n = ast.Method(n, name, args)
                else:
                    # member access
                    n = ast.Member(n, name)

            elif self._lookahead.type == 'LBRACKET':
                token = self._lookahead
                self._next()  # LBRACKET
                idx = self._test()
                self._expect('RBRACKET')
                n = ast.Op('subscript', ast.List([n, idx]))

            elif self._lookahead.type == 'ARROW':
                token = self._lookahead
                self._next()
                tp = self._type()
                n = ast.Cast(n, tp)

            else:
                break

        return n

    def _atom(self) -> ast.Expr:
        if self._lookahead.type == 'ID':
            token = self._lookahead
            name = self._path()

            if self._lookahead.type == 'LPAREN':
                args = self._params('PAREN', self._test)
                return ast.Call(name, args)

            return ast.Var(name)

        if self._lookahead.type in ['NUM', 'FLOAT']:
            tp = self._lookahead.type.lower()
            token = self._lookahead
            self._next()

            return ast.Const(token.value, tp)

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

        if self._lookahead.type in ['RETURN', 'BREAK']:
            token = self._lookahead
            self._next()  # RETURN / BREAK

            # TODO: remove this hack
            if self._lookahead.type not in ['EOL', 'THEN', 'DO', 'ELSE']:
                val = self._test()
            else:
                val = ast.Noop()

            if token.type == 'RETURN':
                return ast.Return(val)
            elif token.type == 'BREAK':
                return ast.Break(val)

        if self._lookahead.type in ['CONTINUE', 'REDO']:
            token = self._lookahead
            self._next()  # CONTINUE / REDO

            if token.type == 'CONTINUE':
                return ast.Continue()
            elif token.type == 'REDO':
                return ast.Redo()

        self._expect()
        assert False, 'unreachable'
