from typing import Sequence, Set, List, Dict, Union, TypeVar, Callable, Any, \
    cast
from functools import wraps
from .tokens import Token
from . import symbols
from . import pattern
from .reflect import Module, Function, Struct, Block, Type, Reference, Array, \
    StructType, Special, Match, SymbolTable, Variable, Constant, Generic, \
    FunctionGroup, Symbol, Enumeration, Variant, EnumerationType
from .error import AnalyzerError
from .pattern import Pattern


TFn = TypeVar('TFn', bound=Callable[..., Any])


def error(fn: TFn) -> TFn:
    @wraps(fn)
    def dec(self: 'Node', *args, **kargs) -> Any:
        try:
            ret = fn(self, *args, **kargs)
        except (LookupError, TypeError) as e:
            self._error(str(e))

        return ret

    return cast(TFn, dec)


class StackNode:
    def __init__(self, tp: Type, nxt: 'StackNode') -> None:
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
                 token: Token,
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
        self.module: Module = None
        self.function: Function = None
        self.struct: Struct = None
        self.enum: Enumeration = None
        self.args: List[Type] = None
        self.match: Match = None
        self.matches: Set[Match] = None
        self.expr_type: Type = None
        self.target_type: Type = None
        self.stack_start: StackNode = None
        self.stack_end: StackNode = None
        self.stack_next: StackNode = None
        self.variable: Union[Variable, Constant] = None
        self.block: Block = None
        self.pattern: pattern.Pattern = None
        self.variables: List[Variable] = None

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

        if self.expr_type and self.expr_type != symbols.VOID:
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

    def analyze(self, mod: Module, root: Module, refs: Set[Function]) -> None:
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

        raise AnalyzerError(msg, self.token)

    @error
    def _expect_type(self, tp: Type) -> None:
        assert self.expr_type is not None, \
            f'{self.type} does not have expr_type'
        assert tp is not None

        if symbols.accept_type(tp, self.expr_type, {}) is None:
            self._error(f'{self.expr_type} cannot be converted to {tp}')

        self.target_type = tp

    @error
    def _declare(self, mod: Module) -> None:
        if self.type == 'STRUCT':
            self.struct = Struct(self.value)
            mod.add_struct(self.struct)

        elif self.type == 'ENUM':
            self.enum = Enumeration(self.value)
            mod.add_enum(self.enum)

        else:
            assert False

    @error
    def _define(self, mod: Module) -> None:
        if self.type == 'DEF':
            name = self.value
            ret = self.children[1]._type(mod)
            if ret is None:
                ret = symbols.VOID

            self.function = Function(name, ret)

            for p in self.children[0].children:
                name = p.value
                tp = p.children[0]._type(mod)
                self.function.add_param(name, tp)

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

    @error
    def _symbol(self, syms: SymbolTable, *tps) -> Symbol:
        if self.type == 'ID':
            return syms.get(self.value, *tps)
        elif self.type == 'SCOPE':
            st = self.children[0]._symbol(syms, SymbolTable)
            assert isinstance(st, SymbolTable)
            return st.member(self.children[1].value, *tps)
        else:
            assert False, f'unknown type {self.type}'

    @error
    def _type(self, syms: SymbolTable) -> Type:
        if self.type == 'EMPTY':
            return None

        if self.type == 'TYPE':
            name = self.children[0].value
            gen_args = self.children[1].children

            sym = syms.get(name, Struct, Enumeration, Generic)

            assert isinstance(sym, (Struct, Enumeration, Generic))

            if isinstance(sym, Generic):
                if len(gen_args) != 0:
                    self._error('generic type cannot have generic arguments')

                return sym

            if len(gen_args) != len(sym.generics):
                self._error('unmatched generic arguments')

            gens = {g.name: a._type(syms)
                    for g, a in zip(sym.generics, gen_args)}

            if isinstance(sym, Struct):
                return StructType(sym).resolve(gens)

            if isinstance(sym, Enumeration):
                return EnumerationType(sym).resolve(gens)

            assert False

        if self.type == 'REF':
            assert self.level > 0

            tp = self.children[0]._type(syms)
            return Reference(tp, self.level)

        if self.type == 'ARRAY':
            tp = self.children[0]._type(syms)

            if self.children[1].type != 'EMPTY':
                size = int(self.children[1].value)
                return Array(tp, size)

            return Array(tp)

        assert False, 'unknown AST node type'

    @error
    def _pattern(self, syms: Block, tp: Type) -> Pattern:
        pat: pattern.Pattern

        if self.type == 'PAT_ANY':
            pat = pattern.Any()

        elif self.type == 'PAT_NUM':
            pat = pattern.Int(int(self.value))

        elif self.type == 'PAT_FLOAT':
            pat = pattern.Float(float(self.value))

        elif self.type == 'PAT_VAR':
            name = self.children[0].value
            pat = pattern.Variable(name, tp)

        elif self.type == 'PAT_STRUCT':
            sym = self.children[0]._symbol(syms, Struct, Variant)
            if isinstance(sym, Struct):
                assert False, 'TODO'

            elif isinstance(sym, Variant):
                pat = pattern.Variant(sym)
                if len(self.children[1].children) != len(sym.struct.fields):
                    self._error('unmatched fields')

                gens: Dict[str, Type] = {}
                if symbols.accept_type(pat.type, tp, gens) is None:
                    self._error(f"unmatched pattern '{pat}' for type {tp}")

                pat.resolve(gens)

                # get resolved variant
                assert isinstance(pat.type, EnumerationType)
                var = pat.variant_struct

                for c, f in zip(self.children[1].children, var.fields):
                    pat.add_field(c._pattern(syms, f.type))

            else:
                assert False

        else:
            assert False, 'unknown pattern type'

        return pat

    @error
    def _resolve_overload(self,
                          refs: Set[Function],
                          args: List[Type],
                          ret: Type,
                          required: bool = False) -> None:
        if self.match is not None:
            return

        self.matches = symbols.resolve_overload(self.matches, args, ret)

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

    @error
    def _analyze_declare(self, root: Module) -> None:
        # structs must be declared first for recursive definition
        for c in self.children:
            if c.type == 'IMPORT':
                ref = c.children[0]._symbol(root, Module)
                assert isinstance(ref, Module)
                self.module.add_reference(ref)

            elif c.type in ['STRUCT', 'ENUM']:
                c._declare(self.module)

        # define structs and declare functions next so they can be used
        # anywhere in functions
        for c in self.children:
            if c.type in ['DEF', 'STRUCT', 'ENUM']:
                c._define(self.module)

    @error
    def _analyze_acquire(self, syms: SymbolTable, refs: Set[Function]) -> None:
        # symbol table
        if self.type == 'DEF':
            offset = -sum(f.type.size() for f in self.function.params)
            syms = Block(self.function, offset)
            vs = []

            for f in self.function.params:
                var = syms.add_local(f.name, f.type)
                vs.append(var)

            self.children[0].variables = vs  # params

            assert offset + syms.offset == 0

        elif self.type == 'STRUCT':
            syms = self.struct

        elif self.type == 'ENUM':
            syms = self.enum

        elif self.type in ('BLOCK', 'ARM'):
            assert isinstance(syms, Block)

            syms = Block(syms, syms.offset)
            self.block = syms

        # process children
        for c in self.children:
            c._analyze_acquire(syms, refs)

        # expr type
        if self.type == 'VAR':
            sym = self.children[0]._symbol(syms, Variable, Constant)
            assert isinstance(sym, (Variable, Constant))

            self.variable = sym
            self.expr_type = self.variable.var_type()

        elif self.type == 'NUM':
            self.expr_type = symbols.INT_TYPE

        elif self.type == 'FLOAT':
            self.expr_type = symbols.FLOAT_TYPE

        elif self.type == 'TEST':
            self.expr_type = symbols.BOOL_TYPE

        elif self.type == 'CALL':
            sym = self.children[0]._symbol(
                syms, FunctionGroup, Struct, Variant)

            assert isinstance(sym, (FunctionGroup, Struct, Variant))

            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.matches = sym.overloads()

            if len(self.matches) == 0:
                self._error(f"no callable '{self.value}' defined")

            self.args = [c.expr_type for c in self.children[1].children]
            self._resolve_overload(refs, self.args, self.target_type)

            if self.match is not None:
                self.expr_type = self.match.result

        elif self.type == 'OP':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.matches = syms.ancestor(Module).operators(self.value)

            assert len(self.matches) > 0

            self.args = [c.expr_type for c in self.children]
            self._resolve_overload(refs, self.args, self.target_type)

            if self.match is not None:
                self.expr_type = self.match.result

        elif self.type == 'INC_ASSN':
            assert len(self.children) == 2

            sym = syms.get(self.value, FunctionGroup)
            assert isinstance(sym, FunctionGroup)

            self.expr_type = symbols.VOID
            self.matches = sym.overloads()

            # no need to check empty since there are always operator overloads

            self.args = [c.expr_type for c in self.children]
            ret = symbols.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret)

        elif self.type == 'CAST':
            sym = syms.get('cast', FunctionGroup)
            assert isinstance(sym, FunctionGroup)

            self.expr_type = self.children[1]._type(syms)
            self.matches = sym.overloads()

            self.args = [self.children[0].expr_type]
            self._resolve_overload(refs, self.args, self.expr_type, True)

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 0)

            if not isinstance(tp, StructType):
                self._error('member access requires struct type')
                assert False

            self.variable = tp.field(self.children[1].value)
            self.expr_type = self.variable.var_type()

        elif self.type in ('BLOCK', 'ARM'):
            self.expr_type = self.children[-1].expr_type

        elif self.type == 'IF':
            tps = {c.expr_type for c in self.children[1:]}
            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type == 'LET':
            name = self.value
            tp = self.children[0]._type(syms)
            if tp is None:
                if self.children[1].type == 'EMPTY':
                    self._error('type is required when not assigning a value')

                tp = self.children[1].expr_type

                if isinstance(tp, Special):
                    if tp == symbols.UNKNOWN:
                        self._error('unable to infer type, ' +
                                    'type annotation required')
                    self._error(f'cannot create variable of type {tp}')

                tp = symbols.to_level(tp, self.level)

            assert isinstance(syms, Block)

            self.variable = syms.add_local(name, tp)
            self.expr_type = symbols.VOID

        elif self.type == 'MATCH':
            arms = self.children[1].children
            tps = {arm.expr_type for arm in arms}

            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type == 'PATTERN':
            assert isinstance(syms, Block)

            tp = self.ancestor('MATCH').children[0].expr_type

            self.pattern = self.children[0]._pattern(syms, tp)

            self.variables = []
            for v in self.pattern.variables():
                self.variables.append(syms.add_local(v.name, v.type))

        elif self.type == 'WHILE':
            bks = self.children[1].decedents('BREAK')
            tps = {node.children[0].expr_type for node in bks}
            tps.add(self.children[2].expr_type)  # else

            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type in ['IMPORT', 'DEF', 'STRUCT', 'ENUM', 'ASSN', 'EMPTY']:
            self.expr_type = symbols.VOID

        elif self.type in ['BREAK', 'CONTINUE', 'REDO', 'RETURN']:
            self.expr_type = symbols.DIVERGE

    @error
    def _analyze_expect(self, refs: Set[Function], stack: StackNode) -> None:
        if self.type == 'TEST':
            for c in self.children:
                c._expect_type(symbols.BOOL_TYPE)

        elif self.type == 'ASSN':
            tp = symbols.to_level(self.children[0].expr_type, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = symbols.to_level(self.children[0].expr_type, self.level)
            self.children[1]._expect_type(tp)

        elif self.type == 'CALL':
            self._resolve_overload(refs, self.args, self.target_type, True)

            if isinstance(self.match.source, Function):
                # record usage for ref generation
                refs.add(self.match.source)
            elif isinstance(self.match.source, (Struct, Variant)):
                pass
            else:
                assert False, f'unknown type {type(self.match.source)}'

            self.expr_type = self.match.result
            for c, p in zip(self.children[1].children, self.match.args):
                c._expect_type(p)

        elif self.type == 'OP':
            self._resolve_overload(refs, self.args, self.target_type, True)
            self.expr_type = self.match.result
            for c, p in zip(self.children, self.match.args):
                c._expect_type(p)

        elif self.type == 'INC_ASSN':
            ret = symbols.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret, True)

            if not isinstance(self.match.source, Function):
                self._error('why is it not a function...')
                assert False

            refs.add(self.match.source)

            tp = symbols.to_level(self.match.args[0], 1)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(self.match.args[1])

        elif self.type == 'CAST':
            if not isinstance(self.match.source, Function):
                self._error('how is casting not a function?')
                assert False

            refs.add(self.match.source)
            self.children[0]._expect_type(self.match.args[0])

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 1)
            self.children[0]._expect_type(tp)

        elif self.type == 'FILE':
            for c in self.children:
                c._expect_type(symbols.VOID)

        elif self.type == 'DEF':
            self.children[2]._expect_type(self.function.ret)

        elif self.type == 'BLOCK':
            self.expr_type = self.target_type

            for c in self.children[:-1]:
                c._expect_type(symbols.VOID)
            self.children[-1]._expect_type(self.expr_type)

        elif self.type == 'ARM':
            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)

        elif self.type == 'IF':
            self.children[0]._expect_type(symbols.BOOL_TYPE)

            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'MATCH':
            self.expr_type = self.target_type

            # TODO: this is inefficient
            self.children[0]._expect_type(self.children[0].expr_type)
            for c in self.children[1].children:
                c._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.expr_type = self.target_type

            self.children[0]._expect_type(symbols.BOOL_TYPE)
            self.children[1]._expect_type(symbols.VOID)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            tp = self.ancestor('DEF').function.ret
            self.children[0]._expect_type(tp)

        elif self.type == 'BREAK':
            tp = self.ancestor('WHILE').target_type
            self.children[0]._expect_type(tp)

        elif self.type == 'LET':
            if self.children[1].type != 'EMPTY':
                if isinstance(self.variable.type, Reference):
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
                and self.target_type != symbols.VOID:
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
            stack = StackNode(self.match.args[0],
                              self.children[0].stack_next)

            self.children[1]._analyze_expect(refs, stack)

            self.stack_end = self.children[1].stack_next

        else:
            self.stack_end = self.stack_start

            for c in self.children:
                c._analyze_expect(refs, self.stack_end)
                self.stack_end = c.stack_next
