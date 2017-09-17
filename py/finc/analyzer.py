from typing import Sequence, Set, Dict, TypeVar, Callable, Any, Type
from . import ast
from . import builtin
from . import error
from . import pattern
from . import symbols
from . import types

TFn = TypeVar('TFn', bound=Callable[..., Any])


def get_symbol(syms: symbols.SymbolTable,
               path: ast.Path,
               *tps: Type[symbols.Symbol]) -> symbols.Symbol:
    if path.path is None:
        return syms.get(path.name, *tps)

    st = get_symbol(syms, path.path, symbols.Scope)
    assert isinstance(st, symbols.Scope)

    return st.member(path.name, *tps)


def get_type(syms: symbols.SymbolTable,
             node: ast.Type) -> types.Type:
    if node is None:
        return None

    if isinstance(node, ast.TypeNamed):
        sym = get_symbol(syms,
                         node.path,
                         symbols.Struct,
                         symbols.Enumeration,
                         symbols.Generic)

        assert isinstance(sym, (symbols.Struct,
                                symbols.Enumeration,
                                symbols.Generic))

        if isinstance(sym, symbols.Generic):
            if len(node.generics) != 0:
                raise error.AnalyzerError(
                    'generic type cannot have generic arguments',
                    node)

            return types.Generic(sym)

        if len(node.generics) != len(sym.generics):
            raise error.AnalyzerError(
                'unmatched generic arguments',
                node)

        gens = types.Generics(sym.generics,
                              [get_type(syms, g) for g in node.generics])

        if isinstance(sym, symbols.Struct):
            return types.StructType(sym, gens)

        elif isinstance(sym, symbols.Enumeration):
            return types.EnumerationType(sym, gens)

        assert False, 'unreachable'

    if isinstance(node, ast.TypeRef):
        child = get_type(syms, node.type)
        return types.Reference(child)

    if isinstance(node, ast.TypeArray):
        child = get_type(syms, node.type)

        if node.length is not None:
            leng = int(node.length.value)
            return types.Array(child, leng)

        return types.Array(child)

    assert False, 'unknown AST type node'


def get_pattern(node: ast.Pattern,
                syms: symbols.Block,
                tp: types.Type) -> pattern.Pattern:
    pat: pattern.Pattern

    if isinstance(node, ast.PatternCall):
        sym = get_symbol(syms,
                         node.path,
                         symbols.Struct,
                         symbols.Variant)
        assert isinstance(sym, (symbols.Struct, symbols.Variant))

        pat = pattern.Struct(sym)
        if len(node.fields) != len(sym.fields):
            raise error.AnalyzerError(
                'unmatched number of fields',
                node)

    elif isinstance(node, ast.PatternAny):
        pat = pattern.Wildcard()

    elif isinstance(node, ast.PatternVar):
        pat = pattern.Variable(node.name, tp)

    elif isinstance(node, ast.PatternConst):
        if node.type == 'num':
            tp = builtin.INT
        elif node.type == 'float':
            tp = builtin.FLOAT
        else:
            assert False, 'unknown const type'

        pat = pattern.Constant(node.value, tp)

    else:
        assert False, 'unknown pattern type'

    res = types.Resolution()
    if res.accept_type(pat.type, tp, False) is None:
        raise error.AnalyzerError(
            f"unmatched pattern '{pat}' for type {tp}",
            node)

    pat.resolve(res)
    # TODO
    # if not pat.resolved():
    #     self._error("unresolved pattern '{pat}'")

    # subpatterns
    if isinstance(node, ast.PatternCall):
        assert isinstance(pat, pattern.Struct)
        for child, fld in zip(node.fields, pat.fields):
            pat.add_field(get_pattern(child, syms, fld.type))

    return pat


class OverloadSet:
    def __init__(self,
                 matches: Set[types.Match],
                 args: Sequence[types.Type]) -> None:
        self.matches = matches
        self.args = args

    def resolve(self, ret: types.Type, required: bool = False) -> types.Match:
        self.matches = types.resolve_overload(self.matches, self.args, ret)

        if len(self.matches) == 0:
            raise error.SymbolError(
                'no viable function overload',
                None)

        if len(self.matches) > 1:
            if not required:
                return None

            raise error.SymbolError(
                'cannot resolve function overload between\n' +
                '\n'.join('    ' + str(fn) for fn in self.matches),
                None)

        match = next(iter(self.matches))

        if not match.resolve():
            if not required:
                return None

            raise error.SymbolError(
                f'cannot resolve generic parameters\n  {match}',
                None)

        return match


class Analyzer:
    def __init__(self,
                 root: symbols.Module) -> None:
        self.root = root

    def analyze(self, file: ast.File, mod: symbols.Module) -> None:
        raise NotImplementedError()


class AnalyzeImport(Analyzer):
    def analyze(self, file: ast.File, mod: symbols.Module) -> None:
        for decl in file.items:
            if isinstance(decl, ast.Import):
                ref = get_symbol(self.root, decl.path, symbols.Module)
                assert isinstance(ref, symbols.Module)
                mod.add_reference(ref)


class AnalyzeDeclare(Analyzer):
    def analyze(self, file: ast.File, mod: symbols.Module) -> None:
        # structs / enums must be declared first for recursive definition
        # and for usage as arg / ret of functions
        for decl in file.items:
            try:
                if isinstance(decl, ast.Def):
                    decl.symbol = symbols.Function(decl.name)
                    mod.add_function(decl.symbol)

                elif isinstance(decl, ast.Struct):
                    decl.symbol = symbols.Struct(decl.name)
                    mod.add_struct(decl.symbol)

                elif isinstance(decl, ast.Enum):
                    decl.symbol = symbols.Enumeration(decl.name)
                    mod.add_enum(decl.symbol)
            except error.SymbolError as e:
                raise error.AnalyzerError(str(e), decl, e.symbol)

        # define structs and declare functions next so they can be used
        # anywhere in functions
        for decl in file.items:
            try:
                if isinstance(decl, ast.Def):
                    self._declare_function(decl)

                elif isinstance(decl, ast.Struct):
                    self._define_struct(decl)

                elif isinstance(decl, ast.Enum):
                    self._define_enum(decl)
            except error.SymbolError as e:
                # TODO: error message can use a more specific ast node
                raise error.AnalyzerError(str(e), decl, e.symbol)

    def _declare_function(self, fn: ast.Def) -> None:
        # generic parameters
        for gen in fn.generics:
            fn.symbol.add_generic(gen.name)

        # parameters
        for param in fn.parameters:
            tp = get_type(fn.symbol, param.type)
            fn.symbol.add_param(param.name, tp)

        # return type
        ret = get_type(fn.symbol, fn.return_type)
        if ret is None:
            ret = builtin.VOID

        fn.symbol.set_ret(ret)

    def _define_struct(self, struct: ast.Struct) -> None:
        for gen in struct.generics:
            struct.symbol.add_generic(gen.name)

        for fld in struct.fields:
            tp = get_type(struct.symbol, fld.type)
            struct.symbol.add_field(fld.name, tp)

    def _define_enum(self, enum: ast.Enum) -> None:
        for gen in enum.generics:
            enum.symbol.add_generic(gen.name)

        for v in enum.variants:
            var = enum.symbol.add_variant(v.name)

            for fld in v.fields:
                tp = get_type(enum.symbol, fld.type)
                var.add_field(fld.name, tp)


class AnalyzeJump(Analyzer):
    def analyze(self, file: ast.File, mod: symbols.Module) -> None:
        for decl in file:
            if isinstance(decl, ast.Def):
                self._recurse(decl.body, decl, None)

    def _recurse(self,
                 expr: ast.Expr,
                 fn: ast.Def,
                 whl: ast.While) -> None:
        if isinstance(expr, ast.While):
            self._recurse(expr.condition, fn, whl)

            # use current while
            self._recurse(expr.content, fn, expr)

            self._recurse(expr.failure, fn, whl)

        elif isinstance(expr, ast.Match):
            self._recurse(expr.expr, fn, whl)

            for arm in expr.arms:
                arm.target = expr
                self._recurse(arm.content, fn, whl)

        elif isinstance(expr, ast.Return):
            # no need to check None since exprs are always in function
            expr.target = fn

        elif isinstance(expr, (ast.Break, ast.Continue, ast.Redo)):
            if whl is None:
                raise error.AnalyzerError(
                    'jump not in a while loop',
                    expr)

            expr.target = whl

        else:
            for child in expr.children():
                if isinstance(child, ast.Expr):
                    self._recurse(child, fn, whl)


class AnalyzeExpr(Analyzer):
    def __init__(self, *args, **kargs) -> None:
        Analyzer.__init__(self, *args, **kargs)

        self.module: symbols.Module
        self.matches: Dict[ast.Node, OverloadSet]

    def analyze(self, file: ast.File, mod: symbols.Module) -> None:
        self.module = mod
        self.matches = {}

        for decl in file:
            if isinstance(decl, ast.Def):
                self._expr(decl.body, decl.symbol)

        for decl in file:
            if isinstance(decl, ast.Def):
                decl.body = self._expect(decl.body, decl.symbol.ret)

    def _expr(self, expr: ast.Expr, syms: symbols.SymbolTable) -> None:
        try:
            self._update(expr, syms)
        except error.SymbolError as e:
            raise error.AnalyzerError(str(e), expr, e.symbol)

    def _update(self, expr: ast.Expr, syms: symbols.SymbolTable) -> None:
        if isinstance(expr, ast.Block):
            syms = symbols.Block(syms)
            for child in expr:
                self._expr(child, syms)

            expr.block = syms
            expr.expr_type = expr.items[-1].expr_type

        elif isinstance(expr, ast.Let):
            if expr.value is not None:
                self._expr(expr.value, syms)

            tp = get_type(syms, expr.type)
            if tp is None:
                if expr.value is None:
                    raise error.AnalyzerError(
                        'type is required when not assigning a value',
                        expr)

                tp = expr.value.expr_type

                if isinstance(tp, types.Special):
                    if tp == builtin.UNKNOWN:
                        raise error.AnalyzerError(
                            'unable to infer type, type annotation required',
                            expr)

                    raise error.AnalyzerError(
                        f'cannot create variable of type {tp}',
                        expr)

            assert isinstance(syms, symbols.Block)

            expr.symbol = syms.add_local(expr.name, tp)
            expr.expr_type = builtin.VOID

        elif isinstance(expr, ast.If):
            self._expr(expr.condition, syms)
            self._expr(expr.success, syms)
            self._expr(expr.failure, syms)

            tps = [expr.success.expr_type, expr.failure.expr_type]
            res = types.Resolution()
            expr.expr_type = res.interpolate_types(tps)

        elif isinstance(expr, ast.While):
            self._expr(expr.condition, syms)
            self._expr(expr.content, syms)
            self._expr(expr.failure, syms)

            bks = expr.content.decedents(ast.Break)
            tps = [b.value.expr_type for b in bks]
            tps.append(expr.failure.expr_type)

            res = types.Resolution()
            expr.expr_type = res.interpolate_types(tps)

        elif isinstance(expr, ast.Match):
            self._expr(expr.expr, syms)
            for arm in expr.arms:
                arm_syms = symbols.Block(syms)

                tp = arm.target.expr.expr_type

                arm.pat = get_pattern(arm.pattern, arm_syms, tp)

                for v in arm.pat.variables():
                    var = arm_syms.add_local(v.name, v.type)
                    v.set_variable(var)

                self._expr(arm.content, arm_syms)

            tps = [arm.content.expr_type for arm in expr.arms]

            res = types.Resolution()
            expr.expr_type = res.interpolate_types(tps)

        elif isinstance(expr, ast.BinTest):
            self._expr(expr.left, syms)
            self._expr(expr.right, syms)

            expr.expr_type = builtin.BOOL

        elif isinstance(expr, ast.NotTest):
            self._expr(expr.expr, syms)

            expr.expr_type = builtin.BOOL

        elif isinstance(expr, ast.Call):
            for child in expr.arguments:
                self._expr(child, syms)

            sym = get_symbol(syms,
                             expr.path,
                             symbols.FunctionGroup,
                             symbols.Struct,
                             symbols.Variant)

            assert isinstance(sym, (symbols.FunctionGroup,
                                    symbols.Struct,
                                    symbols.Variant))

            matches = sym.overloads()

            assert len(matches) > 0, 'overloads returned empty set'

            expr.expr_type = builtin.UNKNOWN
            args = [c.expr_type for c in expr.arguments]
            os = OverloadSet(matches, args)
            self.matches[expr] = os

            match = os.resolve(expr.expr_type)

            if match is not None:
                expr.match = match
                expr.expr_type = match.ret

        elif isinstance(expr, ast.Method):
            self._expr(expr.object, syms)
            for child in expr.arguments:
                self._expr(child, syms)

            sym = get_symbol(syms, expr.path, symbols.FunctionGroup)

            assert isinstance(sym, symbols.FunctionGroup)

            matches = sym.overloads()

            assert len(matches) > 0, 'overloads returned empty set'

            expr.expr_type = builtin.UNKNOWN
            args = [expr.object.expr_type] + \
                [c.expr_type for c in expr.arguments]
            os = OverloadSet(matches, args)
            self.matches[expr] = os

            match = os.resolve(expr.expr_type)

            if match is not None:
                expr.match = match
                expr.expr_type = match.ret

        elif isinstance(expr, ast.Op):
            for child in expr.arguments:
                self._expr(child, syms)

            matches = self.module.operators(expr.operator)

            assert len(matches) > 0, 'operators returned empty set'

            expr.expr_type = builtin.UNKNOWN
            args = [c.expr_type for c in expr.arguments]
            os = OverloadSet(matches, args)
            self.matches[expr] = os

            match = os.resolve(expr.expr_type)

            if match is not None:
                expr.match = match
                expr.expr_type = match.ret

        elif isinstance(expr, ast.Cast):
            self._expr(expr.expr, syms)

            matches = self.module.operators('cast')

            expr.expr_type = get_type(syms, expr.type)
            args = [expr.expr.expr_type]
            os = OverloadSet(matches, args)
            expr.match = os.resolve(expr.expr_type, required=True)

        elif isinstance(expr, ast.Member):
            self._expr(expr.expr, syms)

            tp = types.remove_ref(expr.expr.expr_type)

            if not isinstance(tp, types.StructType):
                raise error.AnalyzerError(
                    'member access requires struct type',
                    expr.member)

            if expr.member.path is not None:
                raise error.AnalyzerError(
                    'path member access unsupported',
                    expr.member)

            var = tp.fields[expr.member.name]
            expr.expr_type = var.var_type()

        elif isinstance(expr, ast.Var):
            sym = get_symbol(syms,
                             expr.path,
                             symbols.Variable,
                             symbols.Constant)
            assert isinstance(sym, (symbols.Variable, symbols.Constant))

            expr.variable = sym
            expr.expr_type = sym.var_type()

        elif isinstance(expr, ast.Const):
            if expr.type == 'num':
                expr.expr_type = builtin.INT
            elif expr.type == 'float':
                expr.expr_type = builtin.FLOAT
            else:
                assert False, 'unknown const type'

        elif isinstance(expr, ast.Assn):
            self._expr(expr.variable, syms)
            self._expr(expr.value, syms)

            expr.expr_type = builtin.VOID

        elif isinstance(expr, ast.IncAssn):
            self._expr(expr.variable, syms)
            self._expr(expr.value, syms)

            matches = self.module.operators(expr.operator)

            assert len(matches) > 0

            expr.expr_type = builtin.VOID
            args = [expr.variable.expr_type, expr.value.expr_type]
            ret = types.remove_ref(expr.variable.expr_type)
            os = OverloadSet(matches, args)

            expr.match = os.resolve(ret, required=True)
            expr.expr_type = builtin.VOID

        elif isinstance(expr, (ast.Return, ast.Break)):
            self._expr(expr.value, syms)

            expr.expr_type = builtin.DIVERGE

        elif isinstance(expr, (ast.Continue, ast.Redo)):
            expr.expr_type = builtin.DIVERGE

        elif isinstance(expr, ast.Noop):
            expr.expr_type = builtin.VOID

        else:
            assert False, f'unknown expr type {expr}'

    def _expect(self, expr: ast.Expr, tar_type: types.Type) -> ast.Expr:
        if isinstance(expr, ast.Block):
            for i in range(len(expr) - 1):
                expr[i] = self._expect(expr[i], builtin.VOID)

            expr[-1] = self._expect(expr[-1], tar_type)

            expr.expr_type = tar_type

        elif isinstance(expr, ast.Let):
            if expr.value is not None:
                expr.value = self._expect(expr.value, expr.symbol.type)

        elif isinstance(expr, ast.If):
            expr.condition = self._expect(expr.condition, builtin.BOOL)
            expr.success = self._expect(expr.success, tar_type)
            expr.failure = self._expect(expr.failure, tar_type)

            expr.expr_type = tar_type

        elif isinstance(expr, ast.While):
            expr.condition = self._expect(expr.condition, builtin.BOOL)
            expr.content = self._expect(expr.content, builtin.VOID)
            expr.failure = self._expect(expr.failure, tar_type)

            expr.expr_type = tar_type

        elif isinstance(expr, ast.Match):
            # TODO: this is inefficient - level can be lowered when applicable
            expr.expr = self._expect(expr.expr, expr.expr.expr_type)
            for arm in expr.arms:
                arm.content = self._expect(arm.content, tar_type)

            expr.expr_type = tar_type

        elif isinstance(expr, ast.BinTest):
            expr.left = self._expect(expr.left, builtin.BOOL)
            expr.right = self._expect(expr.right, builtin.BOOL)

        elif isinstance(expr, ast.NotTest):
            expr.expr = self._expect(expr.expr, builtin.BOOL)

        elif isinstance(expr, (ast.Call, ast.Op)):
            if expr.match is None:
                os = self.matches[expr]
                match = os.resolve(tar_type, required=True)

                expr.match = match
                expr.expr_type = match.ret

            if isinstance(expr, ast.Op) and \
                    not isinstance(expr.match.source, symbols.Function):
                raise error.AnalyzerError('operator not a function', expr)

            assert len(expr.arguments) == len(expr.match.params)
            for i in range(len(expr.arguments)):
                tp = expr.match.params[i].type
                expr.arguments[i] = self._expect(expr.arguments[i], tp)

        elif isinstance(expr, ast.Method):
            # TODO: remove this duplicate code
            if expr.match is None:
                os = self.matches[expr]
                match = os.resolve(tar_type, required=True)

                expr.match = match
                expr.expr_type = match.ret

            # object
            expr.object = self._expect(expr.object, expr.match.params[0].type)

            # arguments
            assert len(expr.arguments) == len(expr.match.params) - 1
            for i in range(len(expr.arguments)):
                tp = expr.match.params[i + 1].type
                expr.arguments[i] = self._expect(expr.arguments[i], tp)

        elif isinstance(expr, ast.Cast):
            if not isinstance(expr.match.source, symbols.Function):
                raise error.AnalyzerError('cast not a function', expr)

            expr.expr = self._expect(expr.expr, expr.match.params[0].type)

        elif isinstance(expr, ast.Member):
            tp = types.Reference(types.remove_ref(expr.expr.expr_type))
            expr.expr = self._expect(expr.expr, tp)

        elif isinstance(expr, (ast.Var, ast.Const)):
            # nothing to do, simply here so that the assert below works
            pass

        elif isinstance(expr, ast.Assn):
            tp = types.deref(expr.variable.expr_type)

            expr.variable = self._expect(expr.variable,
                                         expr.variable.expr_type)
            expr.value = self._expect(expr.value, tp)

        elif isinstance(expr, ast.IncAssn):
            if not isinstance(expr.match.source, symbols.Function):
                raise error.AnalyzerError(
                    'incremental assignment not a function',
                    expr)

            tp = types.Reference(expr.match.params[0].type)
            expr.variable = self._expect(expr.variable, tp)
            expr.value = self._expect(expr.value, expr.match.params[1].type)

        elif isinstance(expr, ast.Return):
            expr.value = self._expect(expr.value, expr.target.symbol.ret)

        elif isinstance(expr, ast.Break):
            expr.value = self._expect(expr.value, expr.target.expr_type)

        elif isinstance(expr, (ast.Continue, ast.Redo, ast.Noop)):
            # nothing to do
            pass

        else:
            assert False, f'unknown expr type {expr}'

        return self._cast(expr, tar_type)

    def _cast(self, expr: ast.Expr, tar: types.Type) -> ast.Expr:
        assert expr.expr_type is not None, f'{expr}.expr_type == None'
        assert tar is not None

        res = types.Resolution()
        if res.accept_type(tar, expr.expr_type, False) is None:
            raise error.AnalyzerError(
                f'{expr.expr_type} cannot be converted to {tar}',
                expr)

        tar = tar.resolve(res)

        # same, no need to cast
        if expr.expr_type == tar:
            return expr

        # diverge will never reach the cast
        if expr.expr_type == builtin.DIVERGE:
            return expr

        # cast to void
        if tar == builtin.VOID:
            void = ast.Void(expr)
            void.expr_type = builtin.VOID
            return void

        # deref
        while expr.expr_type != tar:
            assert isinstance(expr.expr_type, types.Reference)
            deref = ast.Deref(expr)
            deref.expr_type = expr.expr_type.type
            expr = deref

        return expr
