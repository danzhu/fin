from typing import Sequence, Set, List, Dict, Union, TypeVar, Callable, Any, \
    cast
from functools import wraps
from . import tokens
from . import symbols
from . import pattern
from . import builtin
from . import types
from . import error
from .pattern import Pattern


TFn = TypeVar('TFn', bound=Callable[..., Any])


def forward_error(fn: TFn) -> TFn:
    @wraps(fn)
    def dec(self: 'Node', *args, **kargs) -> Any:
        try:
            ret = fn(self, *args, **kargs)
        except (LookupError, TypeError) as e:
            self._error(str(e))

        return ret

    return cast(TFn, dec)


class StackNode:
    def __init__(self, tp: types.Type, nxt: 'StackNode') -> None:
        self.type = tp
        self.next = nxt


def print_stack(node: StackNode) -> str:
    if node is None:
        return ''

    if node.next is None:
        return str(node.type)

    return print_stack(node.next) + f' {node.type}'


class Node:
    def __init__(self,
                 tp: str,
                 token: tokens.Token,
                 children: Sequence['Node'],
                 val: str = None,
                 lvl: int = None) -> None:
        # basic data
        self.type = tp
        self.token = token
        self.children = children
        self.value = val
        # TODO: maybe this should be stored somewhere else?
        self.level = lvl

        self.parent = None
        for c in children:
            c.parent = self

        # semantic analysis
        self.module: symbols.Module = None
        self.function: symbols.Function = None
        self.struct: symbols.Struct = None
        self.enum: symbols.Enumeration = None
        self.args: List[types.Type] = None
        self.match: types.Match = None
        self.matches: Set[types.Match] = None
        self.expr_type: types.Type = None
        self.target_type: types.Type = None
        self.stack_start: StackNode = None
        self.stack_end: StackNode = None
        self.stack_next: StackNode = None
        self.variable: Union[symbols.Variable, symbols.Constant] = None
        self.block: symbols.Block = None
        self.pattern: pattern.Pattern = None
        self.variables: List[symbols.Variable] = None

        # code generation
        self.context: Dict[str, str] = None

    def __str__(self) -> str:
        content = self.type

        if self.match:
            content += f' {self.match}'
        elif self.function:
            content += f' {self.function}'
        elif self.pattern:
            content += f' {self.pattern}'
        elif self.value:
            content += f' {self.value}'

        if self.expr_type and self.expr_type != builtin.VOID:
            content += f' <{self.expr_type}'
            if self.target_type:
                content += f' -> {self.target_type}'
            content += '>'

        if self.level:
            content += f' {self.level}'

        if self.stack_end:
            content += ' << ' + \
                print_stack(self.stack_end) + \
                ' >>'

        return content

    def print(self, indent: int = 0) -> None:
        print('  ' * indent + str(self))
        for c in self.children:
            c.print(indent + 1)

    def analyze(self,
                mod: symbols.Module,
                root: symbols.Module,
                refs: Set[symbols.Function]) -> None:
        assert self.type == 'FILE'

        self.module = mod

        self._analyze_declare(root)
        self._analyze_acquire(mod, refs)
        self._analyze_expect(refs, None)

    def ancestor(self, tp: str) -> 'Node':
        node = self.parent

        while True:
            if node is None:
                self._error(f'cannot find ancestor {tp}')

            if node.type == tp:
                return node

            node = node.parent

    def decedents(self, tp: str) -> Set['Node']:
        res = set()
        for c in self.children:
            if c.type == tp:
                res.add(c)

            res |= c.decedents(tp)

        return res

    def _error(self, msg: str):
        msg += f'\n  in {self}'
        if self.type == 'CALL':
            assert self.args is not None

            args = ', '.join(str(a) for a in self.args)
            msg += f'\n    {self.value}({args}) {self.target_type}'

        raise error.AnalyzerError(msg, self.token)

    @forward_error
    def _expect_type(self, tp: types.Type) -> None:
        assert self.expr_type is not None, \
            f'{self.type} does not have expr_type'
        assert tp is not None

        res = types.Resolution()
        if res.accept_type(tp, self.expr_type) is None:
            self._error(f'{self.expr_type} cannot be converted to {tp}')

        tp = tp.resolve(res)

        self.expr_type.finalize()
        tp.finalize()

        self.target_type = tp

    @forward_error
    def _declare(self, mod: symbols.Module) -> None:
        if self.type == 'STRUCT':
            self.struct = symbols.Struct(self.value)
            mod.add_struct(self.struct)

        elif self.type == 'ENUM':
            self.enum = symbols.Enumeration(self.value)
            mod.add_enum(self.enum)

        else:
            assert False

    @forward_error
    def _define(self, mod: symbols.Module) -> None:
        if self.type == 'DEF':
            name = self.value
            ret = self.children[1]._type(mod)
            if ret is None:
                ret = builtin.VOID

            self.function = symbols.Function(name)

            for p in self.children[0].children:
                name = p.value
                tp = p.children[0]._type(mod)
                tp.finalize()
                self.function.add_param(name, tp)

            ret.finalize()
            self.function.ret = ret

            mod.add_function(self.function)

        elif self.type == 'STRUCT':
            for g in self.children[0].children:
                self.struct.add_generic(g.value)

            for f in self.children[1].children:
                name = f.value
                tp = f.children[0]._type(self.struct)
                self.struct.add_field(name, tp)

        elif self.type == 'ENUM':
            for g in self.children[0].children:
                self.enum.add_generic(g.value)

            for v in self.children[1].children:
                var = self.enum.add_variant(v.value)
                for p in v.children:
                    tp = p.children[0]._type(self.enum)
                    var.add_field(p.value, tp)

        else:
            assert False, 'unknown declaration'

    @forward_error
    def _symbol(self, syms: symbols.SymbolTable, *tps) -> symbols.Symbol:
        if self.type == 'ID':
            return syms.get(self.value, *tps)

        if self.type == 'SCOPE':
            st = self.children[0]._symbol(syms, symbols.SymbolTable)
            assert isinstance(st, symbols.SymbolTable)

            return st.member(self.children[1].value, *tps)

        assert False, f'unknown type {self.type}'

    @forward_error
    def _type(self, syms: symbols.SymbolTable) -> types.Type:
        if self.type == 'EMPTY':
            return None

        if self.type == 'TYPE':
            name = self.children[0].value
            gen_args = self.children[1].children

            sym = syms.get(name,
                           symbols.Struct,
                           symbols.Enumeration,
                           symbols.Generic)

            assert isinstance(sym, (symbols.Struct,
                                    symbols.Enumeration,
                                    symbols.Generic))

            if isinstance(sym, symbols.Generic):
                if len(gen_args) != 0:
                    self._error('generic type cannot have generic arguments')

                return sym.type

            if len(gen_args) != len(sym.generics):
                self._error('unmatched generic arguments')

            gens = [g._type(syms) for g in gen_args]

            if isinstance(sym, symbols.Struct):
                return types.StructType(sym).fill(gens)

            if isinstance(sym, symbols.Enumeration):
                return types.EnumerationType(sym).fill(gens)

            assert False

        if self.type == 'REF':
            assert self.level > 0

            tp = self.children[0]._type(syms)
            return types.Reference(tp, self.level)

        if self.type == 'ARRAY':
            tp = self.children[0]._type(syms)

            if self.children[1].type != 'EMPTY':
                size = int(self.children[1].value)
                return types.Array(tp, size)

            return types.Array(tp)

        assert False, 'unknown AST node type'

    @forward_error
    def _pattern(self, syms: symbols.Block, tp: types.Type) -> Pattern:
        pat: pattern.Pattern

        if self.type == 'PAT_STRUCT':
            sym = self.children[0]._symbol(syms,
                                           symbols.Struct,
                                           symbols.Variant)
            if isinstance(sym, symbols.Struct):
                assert False, 'TODO'

            elif isinstance(sym, symbols.Variant):
                pat = pattern.Variant(sym)
                if len(self.children[1].children) != len(sym.fields):
                    self._error('unmatched number of fields')

            else:
                assert False

        elif self.type == 'PAT_ANY':
            pat = pattern.Any()

        elif self.type == 'PAT_VAR':
            name = self.children[0].value
            pat = pattern.Variable(name, tp)

        elif self.type == 'PAT_NUM':
            pat = pattern.Int(int(self.value))

        elif self.type == 'PAT_FLOAT':
            pat = pattern.Float(float(self.value))

        else:
            assert False, 'unknown pattern type'

        res = types.Resolution()
        if res.accept_type(pat.type, tp) is None:
            self._error(f"unmatched pattern '{pat}' for type {tp}")

        pat.resolve(res)
        if not pat.finalize():
            self._error("unresolved pattern '{pat}'")

        # subpatterns
        if isinstance(pat, pattern.Struct):
            assert False, 'TODO'

        elif isinstance(pat, pattern.Variant):
            for c, f in zip(self.children[1].children, pat.fields):
                pat.add_field(c._pattern(syms, f.type))

        return pat

    @forward_error
    def _resolve_overload(self,
                          refs: Set[symbols.Function],
                          args: List[types.Type],
                          ret: types.Type,
                          required: bool = False) -> None:
        if self.match is not None:
            return

        self.matches = types.resolve_overload(self.matches, args, ret)

        if len(self.matches) == 0:
            self._error('no viable function overload')

        if len(self.matches) > 1:
            if not required:
                return

            self._error('cannot resolve function overload between\n' +
                        '\n'.join('    ' + str(fn) for fn in self.matches))

        match = next(iter(self.matches))

        if not match.resolve():
            if not required:
                return

            self._error('cannot resolve generic parameters\n  ' + str(match))

        self.match = match

    @forward_error
    def _analyze_declare(self, root: symbols.Module) -> None:
        # structs must be declared first for recursive definition
        for c in self.children:
            if c.type == 'IMPORT':
                ref = c.children[0]._symbol(root, symbols.Module)
                assert isinstance(ref, symbols.Module)
                self.module.add_reference(ref)

            elif c.type in ['STRUCT', 'ENUM']:
                c._declare(self.module)

        # define structs and declare functions next so they can be used
        # anywhere in functions
        for c in self.children:
            if c.type in ['DEF', 'STRUCT', 'ENUM']:
                c._define(self.module)

    @forward_error
    def _analyze_acquire(self,
                         syms: symbols.SymbolTable,
                         refs: Set[symbols.Function]) -> None:
        # symbol table
        if self.type == 'DEF':
            offset = -sum(p.type.size() for p in self.function.params)
            syms = symbols.Block(self.function, offset)
            vs = []

            for f in self.function.params:
                var = syms.add_local(f.name, f.type)
                vs.append(var)

            self.children[0].variables = vs  # params

            assert syms.offset == 0

        elif self.type == 'STRUCT':
            syms = self.struct

        elif self.type == 'ENUM':
            syms = self.enum

        elif self.type in ('BLOCK', 'ARM'):
            assert isinstance(syms, symbols.Block)

            syms = symbols.Block(syms, syms.offset)
            self.block = syms

        # process children
        for c in self.children:
            c._analyze_acquire(syms, refs)

        # expr type
        if self.type == 'VAR':
            sym = self.children[0]._symbol(syms,
                                           symbols.Variable,
                                           symbols.Constant)
            assert isinstance(sym, (symbols.Variable, symbols.Constant))

            self.variable = sym
            self.expr_type = self.variable.var_type()

        elif self.type == 'NUM':
            self.expr_type = builtin.INT

        elif self.type == 'FLOAT':
            self.expr_type = builtin.FLOAT

        elif self.type == 'TEST':
            self.expr_type = builtin.BOOL

        elif self.type == 'CALL':
            sym = self.children[0]._symbol(syms,
                                           symbols.FunctionGroup,
                                           symbols.Struct,
                                           symbols.Variant)

            assert isinstance(sym, (symbols.FunctionGroup,
                                    symbols.Struct,
                                    symbols.Variant))

            self.expr_type = builtin.UNKNOWN
            self.target_type = builtin.UNKNOWN
            self.matches = sym.overloads()

            if len(self.matches) == 0:
                self._error(f"no callable '{self.value}' defined")

            self.args = [c.expr_type for c in self.children[1].children]
            self._resolve_overload(refs, self.args, self.target_type)

            if self.match is not None:
                self.expr_type = self.match.ret

        elif self.type == 'OP':
            self.expr_type = builtin.UNKNOWN
            self.target_type = builtin.UNKNOWN
            self.matches = syms.ancestor(symbols.Module).operators(self.value)

            assert len(self.matches) > 0

            self.args = [c.expr_type for c in self.children]
            self._resolve_overload(refs, self.args, self.target_type)

            if self.match is not None:
                self.expr_type = self.match.ret

        elif self.type == 'INC_ASSN':
            assert len(self.children) == 2

            sym = syms.get(self.value, symbols.FunctionGroup)
            assert isinstance(sym, symbols.FunctionGroup)

            self.expr_type = builtin.VOID
            self.matches = sym.overloads()

            # no need to check empty since there are always operator overloads

            self.args = [c.expr_type for c in self.children]
            ret = types.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret)

        elif self.type == 'CAST':
            sym = syms.get('cast', symbols.FunctionGroup)
            assert isinstance(sym, symbols.FunctionGroup)

            self.expr_type = self.children[1]._type(syms)
            self.matches = sym.overloads()

            self.args = [self.children[0].expr_type]
            self._resolve_overload(refs, self.args, self.expr_type, True)

        elif self.type == 'MEMBER':
            tp = types.to_level(self.children[0].expr_type, 0)

            if not isinstance(tp, types.StructType):
                self._error('member access requires struct type')
                assert False

            name = self.children[1].value
            self.variable = tp.fields[name]

            if self.variable is None:
                self._error("cannot find member '{name}' in {tp}")

            self.expr_type = self.variable.var_type()

        elif self.type in ('BLOCK', 'ARM'):
            self.expr_type = self.children[-1].expr_type

        elif self.type == 'IF':
            tps = {c.expr_type for c in self.children[1:]}
            res = types.Resolution()
            self.expr_type = res.interpolate_types(tps)

        elif self.type == 'LET':
            name = self.value
            tp = self.children[0]._type(syms)
            if tp is None:
                if self.children[1].type == 'EMPTY':
                    self._error('type is required when not assigning a value')

                tp = self.children[1].expr_type

                if isinstance(tp, types.Special):
                    if tp == builtin.UNKNOWN:
                        self._error('unable to infer type, ' +
                                    'type annotation required')
                    self._error(f'cannot create variable of type {tp}')

                tp = types.to_level(tp, self.level)

            assert isinstance(syms, symbols.Block)

            self.variable = syms.add_local(name, tp)
            self.expr_type = builtin.VOID

        elif self.type == 'MATCH':
            arms = self.children[1].children
            tps = {arm.expr_type for arm in arms}

            res = types.Resolution()
            self.expr_type = res.interpolate_types(tps)

        elif self.type == 'PATTERN':
            assert isinstance(syms, symbols.Block)

            tp = self.ancestor('MATCH').children[0].expr_type

            self.pattern = self.children[0]._pattern(syms, tp)

            self.variables = []
            for v in self.pattern.variables():
                self.variables.append(syms.add_local(v.name, v.type))

        elif self.type == 'WHILE':
            bks = self.children[1].decedents('BREAK')
            tps = {node.children[0].expr_type for node in bks}
            tps.add(self.children[2].expr_type)  # else

            res = types.Resolution()
            self.expr_type = res.interpolate_types(tps)

        elif self.type in ['IMPORT', 'DEF', 'STRUCT', 'ENUM', 'ASSN', 'EMPTY']:
            self.expr_type = builtin.VOID

        elif self.type in ['BREAK', 'CONTINUE', 'REDO', 'RETURN']:
            self.expr_type = builtin.DIVERGE

    @forward_error
    def _analyze_expect(self,
                        refs: Set[symbols.Function],
                        stack: StackNode) -> None:
        if self.type == 'TEST':
            for c in self.children:
                c._expect_type(builtin.BOOL)

        elif self.type == 'ASSN':
            tp = types.to_level(self.children[0].expr_type, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = types.to_level(self.children[0].expr_type, self.level)
            self.children[1]._expect_type(tp)

        elif self.type == 'CALL':
            self._resolve_overload(refs, self.args, self.target_type, True)

            if isinstance(self.match.source, symbols.Function):
                # record usage for ref generation
                refs.add(self.match.source)
            elif isinstance(self.match.source, (symbols.Struct,
                                                symbols.Variant)):
                pass
            else:
                assert False, f'unknown type {type(self.match.source)}'

            self.expr_type = self.match.ret
            for c, p in zip(self.children[1].children,
                            self.match.params):
                c._expect_type(p.type)

        elif self.type == 'OP':
            self._resolve_overload(refs, self.args, self.target_type, True)
            self.expr_type = self.match.ret
            for c, p in zip(self.children, self.match.params):
                c._expect_type(p.type)

        elif self.type == 'INC_ASSN':
            ret = types.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret, True)

            if not isinstance(self.match.source, symbols.Function):
                self._error('why is it not a function...')
                assert False

            refs.add(self.match.source)

            tp = types.to_level(self.match.params[0].type, 1)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(self.match.params[1].type)

        elif self.type == 'CAST':
            if not isinstance(self.match.source, symbols.Function):
                self._error('how is casting not a function?')
                assert False

            refs.add(self.match.source)
            self.children[0]._expect_type(self.match.params[0].type)

        elif self.type == 'MEMBER':
            tp = types.to_level(self.children[0].expr_type, 1)
            self.children[0]._expect_type(tp)

        elif self.type == 'FILE':
            for c in self.children:
                c._expect_type(builtin.VOID)

        elif self.type == 'DEF':
            self.children[2]._expect_type(self.function.ret)

        elif self.type == 'BLOCK':
            self.expr_type = self.target_type

            for c in self.children[:-1]:
                c._expect_type(builtin.VOID)
            self.children[-1]._expect_type(self.expr_type)

        elif self.type == 'ARM':
            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)

        elif self.type == 'IF':
            self.children[0]._expect_type(builtin.BOOL)

            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'MATCH':
            self.expr_type = self.target_type

            # TODO: this is inefficient - level can be lowered when applicable
            self.children[0]._expect_type(self.children[0].expr_type)
            for c in self.children[1].children:
                c._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.expr_type = self.target_type

            self.children[0]._expect_type(builtin.BOOL)
            self.children[1]._expect_type(builtin.VOID)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            tp = self.ancestor('DEF').function.ret
            self.children[0]._expect_type(tp)

        elif self.type == 'BREAK':
            tp = self.ancestor('WHILE').target_type
            self.children[0]._expect_type(tp)

        elif self.type == 'LET':
            if self.children[1].type != 'EMPTY':
                if isinstance(self.variable.type, types.Reference):
                    lvl = self.variable.type.level
                else:
                    lvl = 0

                if lvl != self.level:
                    self._error('initialization level mismatch')

                self.children[1]._expect_type(self.variable.type)

        self.stack_start = stack

        # stack_next
        if self.type == 'LET':
            stack = StackNode(self.variable.type, stack)

        elif self.type in ['PARAMS', 'PATTERN']:
            for var in self.variables:
                stack = StackNode(var.type, stack)

        elif self.target_type is not None \
                and self.target_type != builtin.VOID:
            stack = StackNode(self.target_type, stack)

        self.stack_next = stack

        # recurse
        if len(self.children) == 0:
            pass

        elif self.type in ['IF', 'MATCH', 'ARMS', 'WHILE', 'TEST']:
            # these nodes don't leave data on the stack
            for c in self.children:
                c._analyze_expect(refs, self.stack_start)

            # the result stack after children is the same as final result stack
            self.stack_end = self.stack_next

        elif self.type == 'INC_ASSN':
            self.children[0]._analyze_expect(refs, self.stack_start)

            # the ref is duplicated on the stack and loaded
            stack = StackNode(self.match.params[0].type,
                              self.children[0].stack_next)

            self.children[1]._analyze_expect(refs, stack)

            self.stack_end = self.children[1].stack_next

        else:
            self.stack_end = self.stack_start

            for c in self.children:
                c._analyze_expect(refs, self.stack_end)
                self.stack_end = c.stack_next
