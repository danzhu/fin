from typing import Sequence, Set, List, Dict, Union
from tokens import Token
import symbols
from symbols import Module, Function, Struct, Block, Type, Reference, Array, \
    Construct, Special, Match, SymbolTable, Variable, Constant, Generic
from error import AnalyzerError

def error(fn):
    def dec(self: 'Node', *args, **kargs):
        try:
            ret = fn(self, *args, **kargs)
        except (LookupError, TypeError) as e:
            self._error(str(e))

        return ret

    return dec

class StackNode:
    def __init__(self, tp: Type, nxt: 'StackNode') -> None:
        self.type = tp
        self.next = nxt

    def __str__(self) -> str:
        return f'{self.next} {self.type}'


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
        self.field: Variable = None

        # code generation
        self.context: Dict[str, str] = None

    def __str__(self) -> str:
        content = self.type

        if self.match:
            content += f' {self.match}'
        elif self.function:
            content += f' {self.function}'
        elif self.value:
            content += f' {self.value}'

        if self.expr_type and self.expr_type != symbols.VOID:
            content += f' <{self.expr_type}'
            if self.target_type:
                content += f' -> {self.target_type}'
            content += '>'

        if self.level:
            content += f' {self.level}'

        return content

    def print(self, indent: int = 0) -> None:
        print('  ' * indent + str(self))
        for c in self.children:
            c.print(indent + 1)

    def analyze(self, mod_name: str, mod: Module, refs) -> None:
        assert self.type == 'FILE'

        self.module = Module(mod_name)
        mod.add_module(self.module)
        mod = self.module

        self._analyze_declare()
        self._analyze_acquire(mod, refs)
        self._analyze_expect(refs, '')

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
            if self.args is None:
                self.args = [c.expr_type for c in self.children]

            args = ', '.join(str(a) for a in self.args)
            msg += f'\n    {self.value}({args}) {self.target_type}'

        raise AnalyzerError(msg, self.token)

    @error
    def _expect_type(self, tp: Type) -> None:
        assert self.expr_type is not None
        assert tp is not None

        if symbols.accept_type(tp, self.expr_type, {}) is None:
            self._error(f'{self.expr_type} cannot be converted to {tp}')

        self.target_type = tp

    @error
    def _declare(self, mod: Module) -> None:
        self.struct = Struct(self.value)
        mod.add_struct(self.struct)

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
                self.function.add_variable(name, tp)

            mod.add_function(self.function)

        elif self.type == 'STRUCT':
            for g in self.children[0].children:
                self.struct.add_generic(g.value)

            for f in self.children[1].children:
                name = f.value
                tp = f.children[0]._type(self.struct)
                self.struct.add_variable(name, tp)

        else:
            assert False, 'unknown declaration'

    @error
    def _type(self, syms: SymbolTable) -> Type:
        if self.type == 'EMPTY':
            return None

        if self.type == 'TYPE':
            sym = syms.get(self.value, Struct, Generic)

            assert isinstance(sym, (Struct, Generic))

            if isinstance(sym, Generic):
                if len(self.children) != 0:
                    self._error('generic type cannot have generic arguments')

                return sym

            if len(self.children) != len(sym.generics):
                self._error('unmatched generic arguments')

            gens = {g.name: c._type(syms)
                    for g, c in zip(sym.generics, self.children)}
            return Construct(sym).resolve(gens)

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

            self._error('cannot resolve function overload between\n'
                        + '\n'.join('    ' + str(fn) for fn in self.matches))

        match = next(iter(self.matches))

        if not match.resolve():
            if not required:
                return

            self._error('cannot resolve generic parameters\n  ' + str(match))

        self.match = match

    @error
    def _analyze_declare(self) -> None:
        # structs must be declared first for recursive definition
        for c in self.children:
            if c.type == 'STRUCT':
                c._declare(self.module)

        # define structs and declare functions next so they can be used anywhere
        # in functions
        for c in self.children:
            if c.type in ['DEF', 'STRUCT']:
                c._define(self.module)

    @error
    def _analyze_acquire(self, syms: SymbolTable, refs: Set[Function]) -> None:
        # symbol table
        if self.type == 'DEF':
            syms = self.function

        elif self.type == 'STRUCT':
            syms = self.struct

        elif self.type == 'BLOCK':
            syms = Block(syms)
            self.block = syms

        # process children
        for c in self.children:
            c._analyze_acquire(syms, refs)

        # expr type
        if self.type == 'VAR':
            sym = syms.get(self.value, Variable, Constant)
            assert isinstance(sym, (Variable, Constant))

            self.variable = sym
            self.expr_type = self.variable.var_type()

        elif self.type == 'NUM':
            self.expr_type = Construct(symbols.INT)

        elif self.type == 'FLOAT':
            self.expr_type = Construct(symbols.FLOAT)

        elif self.type == 'TEST':
            self.expr_type = Construct(symbols.BOOL)

        elif self.type == 'CALL':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.matches = syms.overloads(self.value)

            if len(self.matches) == 0:
                self._error(f"no function '{self.value}' defined")

            self.args = [c.expr_type for c in self.children]
            self._resolve_overload(refs, self.args, self.target_type)

            if self.match is not None:
                self.expr_type = self.match.ret

        elif self.type == 'INC_ASSN':
            assert len(self.children) == 2

            self.expr_type = symbols.VOID
            self.matches = syms.overloads(self.value)

            # no need to check empty since there are always operator overloads

            self.args = [c.expr_type for c in self.children]
            ret = symbols.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret)

        elif self.type == 'CAST':
            self.expr_type = self.children[1]._type(syms)
            self.matches = syms.overloads('cast')

            self.args = [self.children[0].expr_type]
            self._resolve_overload(refs, self.args, self.expr_type, True)

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 0)

            if not isinstance(tp, Construct):
                self._error('member access requires struct type')
                assert False

            self.field = tp.member(self.value)
            self.expr_type = self.field.var_type()

        elif self.type == 'BLOCK':
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

            self.variable = syms.add_variable(name, tp)
            self.expr_type = symbols.VOID

        elif self.type == 'WHILE':
            bks = self.children[1].decedents('BREAK')
            tps = {node.children[0].expr_type for node in bks}
            tps.add(self.children[2].expr_type) # else

            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type in ['DEF', 'STRUCT', 'ASSN', 'EMPTY']:
            self.expr_type = symbols.VOID

        elif self.type in ['BREAK', 'CONTINUE', 'REDO', 'RETURN']:
            self.expr_type = symbols.DIVERGE

    @error
    def _analyze_expect(self, refs: Set[Function], stack: StackNode) -> None:
        self.stack_start = stack
        self.stack_next = stack

        if self.type == 'TEST':
            for c in self.children:
                c._expect_type(Construct(symbols.BOOL))

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
            elif isinstance(self.match.source, Struct):
                pass
            else:
                assert False

            self.expr_type = self.match.ret
            for c, p in zip(self.children, self.match.params):
                c._expect_type(p)

        elif self.type == 'INC_ASSN':
            ret = symbols.to_level(self.args[0], 0)
            self._resolve_overload(refs, self.args, ret, True)

            if not isinstance(self.match.source, Function):
                self._error('why is it not a function...')
                assert False

            refs.add(self.match.source)

            tp = symbols.to_level(self.match.params[0], 1)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(self.match.params[1])

        elif self.type == 'CAST':
            if not isinstance(self.match.source, Function):
                self._error('how is casting not a function?')
                assert False

            refs.add(self.match.source)
            self.children[0]._expect_type(self.match.params[0])

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

        elif self.type == 'IF':
            self.children[0]._expect_type(Construct(symbols.BOOL))

            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.expr_type = self.target_type

            self.children[0]._expect_type(Construct(symbols.BOOL))
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

            self.stack_next = StackNode(self.variable.type, stack)

        if self.target_type is not None \
                and self.target_type != symbols.VOID:
            self.stack_next = StackNode(self.target_type, stack)

        # recurse
        if self.type in ['IF', 'WHILE', 'TEST']:
            # these nodes don't leave data on the stack
            for c in self.children:
                c._analyze_expect(refs, stack)

            # the result stack after children is the same as final result stack
            self.stack_end = self.stack_next
        elif self.type == 'INC_ASSN':
            self.children[0]._analyze_expect(refs, stack)

            # the ref is duplicated on the stack and loaded
            stack = StackNode(self.match.params[0], self.children[0].stack_next)

            self.children[1]._analyze_expect(refs, stack)

            self.stack_end = self.children[1].stack_next
        else:
            for c in self.children:
                c._analyze_expect(refs, stack)
                stack = c.stack_next

            self.stack_end = stack
