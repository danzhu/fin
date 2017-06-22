from typing import Tuple, Dict, Any, Set, List, Union, cast, Iterable
from enum import Enum
import math

class Location(Enum):
    Global = 0
    Struct = 1
    Param = 2
    Local = 3


class Type:
    def size(self):
        raise NotImplementedError()

    def resolve(self, gens: Dict[str, 'Type']) -> 'Type':
        raise NotImplementedError()

    def fullname(self) -> str:
        raise NotImplementedError()

    def fullpath(self) -> str:
        raise NotImplementedError()


class Symbol:
    name: str


class Variable(Symbol):
    def __init__(self,
                 name: str,
                 tp: Type,
                 loc: Location,
                 off: int = None) -> None:
        self.name = name
        self.type = tp
        self.location = loc
        self.offset = off

    def __str__(self) -> str:
        return f'{self.name} {self.type}'

    def var_type(self) -> Type:
        if not isinstance(self.type, Reference):
            return Reference(self.type, 1)

        return Reference(self.type.type, self.type.level + 1)


class Constant(Symbol):
    def __init__(self, name: str, tp: Type, val: Any) -> None:
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self) -> Type:
        return self.type


class SymbolTable:
    LOCATION: Location

    def __init__(self, parent: 'SymbolTable' = None) -> None:
        self.parent = parent

        self.symbols: Dict[str, Symbol] = {}

    def add_variable(self, name: str, tp: Type) -> Variable:
        raise NotImplementedError()

    def _check_exists(self, name: str):
        if name in self.symbols:
            raise LookupError(f"symbol '{name}' exists as {self.symbols[name]}")

    def _add_symbol(self, sym: Symbol) -> None:
        self._check_exists(sym.name)
        self.symbols[sym.name] = sym

    def find(self, name: str) -> Symbol:
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.find(name)

        return None

    def get(self, name, *tps: type) -> Symbol:
        sym = self.find(name)

        if sym is None:
            raise LookupError(f"cannot find symbol '{name}'")

        check_type(sym, tps)

        return sym

    def ancestor(self, tp: type) -> 'SymbolTable':
        if self.parent is None:
            raise LookupError(f'cannot find ancestor of type {tp.__name__}')

        if isinstance(self.parent, tp):
            return self.parent

        return self.parent.ancestor(tp)

    def module(self) -> 'Module':
        mod = self.ancestor(Module)
        assert isinstance(mod, Module)
        return mod

    def overloads(self, name: str) -> Set['Match']:
        if self.parent is not None:
            res = self.parent.overloads(name)
        else:
            res = set()

        if name in self.symbols:
            fns = self.symbols[name]

            check_type(fns, (FunctionGroup, Struct))

            if isinstance(fns, FunctionGroup):
                res |= {Match(fn) for fn in fns.functions}
            elif isinstance(fns, Struct):
                res.add(Match(fns))
            else:
                assert False

        return res


class Module(SymbolTable, Symbol):
    LOCATION = Location.Global

    def __init__(self, name: str) -> None:
        super().__init__()

        # TODO: version
        self.name = name

    def __str__(self) -> str:
        return self.name

    def __lt__(self, other: 'Module') -> bool:
        return self.name < other.name

    def fullname(self) -> str:
        return self.name

    def fullpath(self) -> str:
        if self.parent is not None:
            assert isinstance(self.parent, Module)

            # FIXME: use correct module hierarchy for this to work
            # return self.parent.path('.') + self.fullname()
            return self.fullname()

        return self.fullname()

    def path(self, sep: str = ':') -> str:
        path = self.fullpath()
        if path != '':
            path += sep

        return path

    def add_module(self, mod: 'Module') -> None:
        self._add_symbol(mod)
        mod.parent = self

    def add_struct(self, struct: 'Struct') -> None:
        self._add_symbol(struct)
        struct.parent = self

    def add_function(self, fn: 'Function') -> None:
        if fn.name not in self.symbols:
            group = FunctionGroup(fn.name)
            self.symbols[fn.name] = group

        else:
            sym = self.symbols[fn.name]

            if not isinstance(sym, FunctionGroup):
                raise LookupError(f"redefining '{group}' as function")

            group = sym

        group.add(fn)
        fn.parent = self

    def add_variable(self, name: str, tp: Type) -> None:
        raise NotImplementedError()

    def add_constant(self, const: Constant) -> None:
        self._add_symbol(const)


class Struct(SymbolTable, Symbol):
    LOCATION = Location.Struct

    def __init__(self, name: str, size: int = 0) -> None:
        super().__init__()

        self.name = name
        self.size = size
        self.generics: List[Generic] = []
        self.fields: List[Variable] = []

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        return self.name

    def fullpath(self) -> str:
        return self.module().path() + self.fullname()

    def add_generic(self, name: str) -> 'Generic':
        gen = Generic(name)
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_variable(self, name: str, tp: Type) -> Variable:
        var = Variable(name, tp, Location.Struct)
        self.fields.append(var)
        self._add_symbol(var)
        return var

    def match(self, args: List[Type], ret: Type) \
            -> Tuple[List[float], Dict[str, Type]]:
        if len(self.fields) != len(args):
            return None, None

        gens: Dict[str, Type] = {}
        lvls = [accept_type(p.type, a, gens) for p, a in zip(self.fields, args)]

        if ret is not None:
            cons = Construct(self)
            lvls.append(accept_type(ret, cons, gens))
        else:
            lvls.append(math.nan)

        if None in lvls:
            return None, None

        return lvls, gens

    def resolve(self, gens: Dict[str, Type]) -> Tuple[List[Type], Type]:
        params = [p.type.resolve(gens) for p in self.fields]
        ret = Construct(self).resolve(gens)
        return params, ret


class Function(SymbolTable, Symbol):
    LOCATION = Location.Param

    def __init__(self, name: str, ret: Type) -> None:
        super().__init__()

        self.name = name
        self.ret = ret

        self.params: List[Variable] = []
        self.generics: List[Generic] = []

    def __str__(self) -> str:
        gens = ''
        if len(self.generics) > 0:
            gens = '{' + ', '.join(str(g) for g in self.generics) + '}'

        params = ', '.join(str(p) for p in self.params)

        ret = ''
        if self.ret != VOID:
            ret = ' ' + str(self.ret)

        return f'{self.name}{gens}({params}){ret}'

    def fullname(self) -> str:
        # TODO: generic parameters
        params = ','.join(p.type.fullpath() for p in self.params)

        ret = ''
        if self.ret != VOID:
            ret = self.ret.fullpath()

        return f'{self.name}({params}){ret}'

    def fullpath(self) -> str:
        return self.module().path() + self.fullname()

    def add_variable(self, name: str, tp: Type) -> Variable:
        assert isinstance(name, str)

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def add_generic(self, name: str) -> 'Generic':
        assert isinstance(name, str)

        gen = Generic(name)

        self._add_symbol(gen)
        self.generics.append(gen)

        return gen

    def match(self, args: List[Type], ret: Type) \
            -> Tuple[List[float], Dict[str, Type]]:
        if len(self.params) != len(args):
            return None, None

        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        gens: Dict[str, Type] = {}
        lvls = [accept_type(p.type, a, gens) for p, a in zip(self.params, args)]

        if ret is not None:
            lvls.append(accept_type(ret, self.ret, gens))
        else:
            lvls.append(math.nan)

        if None in lvls:
            return None, None

        return lvls, gens

    def resolve(self, gens: Dict[str, Type]) -> Tuple[List[Type], Type]:
        params = [p.type.resolve(gens) for p in self.params]
        ret = self.ret.resolve(gens)
        return params, ret


class Block(SymbolTable):
    LOCATION = Location.Local

    def __init__(self, parent: SymbolTable) -> None:
        super().__init__(parent)

        self.offset = 0

        if isinstance(parent, Block):
            self.parent_offset = parent.offset
        else:
            self.parent_offset = 0

    def add_variable(self, name: str, tp: Type) -> Variable:
        offset = self.parent_offset + self.offset
        var = Variable(name, tp, Location.Local, offset)
        self.offset += tp.size()

        self._add_symbol(var)
        return var


class Match:
    def __init__(self, src: Union[Function, Struct]) -> None:
        self.source = src
        self.levels: List[float] = None
        self.gens: Dict[str, Type] = None
        self.params: List[Type] = None
        self.ret: Type = None

    def __lt__(self, other: 'Match') -> bool:
        assert len(self.levels) == len(other.levels)

        # generic has lower precedence
        if len(self.source.generics) == 0 \
                and len(other.source.generics) > 0:
            return False

        less = False
        for s, o in zip(self.levels, other.levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self) -> str:
        gens = ''.join(f', {k} = {g}' for k, g in self.gens.items())
        return f'{self.source} {self.levels}{gens}'

    def update(self, args: List[Type], ret: Type) -> bool:
        self.levels, self.gens = self.source.match(args, ret)
        return self.levels is not None

    def resolve(self) -> bool:
        # check that all generic params are resolved
        if len(self.gens) != len(self.source.generics):
            return False

        self.params, self.ret = self.source.resolve(self.gens)
        return True


class FunctionGroup(Symbol):
    def __init__(self, name: str) -> None:
        self.name = name
        self.functions: Set[Function] = set()

    def __str__(self) -> str:
        return self.name

    def add(self, fn: Function) -> None:
        self.functions.add(fn)


class Reference(Type):
    def __init__(self, tp: Type, lvl: int) -> None:
        assert not isinstance(tp, Reference)

        self.type = tp
        self.level = lvl

    def __format(self, tp: Any) -> str:
        return '&' * self.level + str(tp)

    def __str__(self) -> str:
        return self.__format(self.type)

    def fullname(self) -> str:
        return self.__format(self.type.fullname())

    def fullpath(self) -> str:
        return self.__format(self.type.fullpath())

    def size(self) -> int:
        return 8 # size of pointer

    def resolve(self, gens: Dict[str, Type]) -> 'Reference':
        return Reference(self.type.resolve(gens), self.level)


class Array(Type):
    def __init__(self, tp: Type, length: int = None) -> None:
        self.type = tp
        self.length = length

    def __format(self, tp: Any, sep: str) -> str:
        length = ''
        if self.length is None:
            length = f'{sep}{self.length}'

        return f'[{tp}{length}]'

    def __str__(self) -> str:
        return self.__format(self.type, '; ')

    def fullname(self) -> str:
        return self.__format(self.type.fullname(), ';')

    def fullpath(self) -> str:
        return self.__format(self.type.fullpath(), ';')

    def size(self) -> int:
        if self.length is None:
            raise TypeError('array is unsized')

        return self.type.size() * self.length

    def resolve(self, gens: Dict[str, Type]) -> 'Array':
        return Array(self.type.resolve(gens))


class Generic(Type, Symbol):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        assert False, 'should not use fullname on generic'

    def fullpath(self) -> str:
        assert False, 'should not use fullpath on generic'

    def size(self) -> int:
        assert False, 'should not use size on generic'

    def resolve(self, gens: Dict[str, Type]) -> Type:
        return gens[self.name]


class Construct(Type):
    def __init__(self,
                 struct: Struct,
                 fields: List[Variable] = None,
                 gens: List[Type] = None) -> None:
        self.struct = struct
        self.fields = fields
        self.generics = gens

        if self.fields is None:
            self.fields = struct.fields

        if self.generics is None:
            self.generics = cast(List[Type], struct.generics)

        self._finalized = False
        self.symbols: Dict[str, Variable] = None

    def __str__(self) -> str:
        res = str(self.struct)
        if len(self.generics) > 0:
            res += '{' + ', '.join(str(g) for g in self.generics) + '}'

        return res

    def fullname(self) -> str:
        res = self.struct.fullname()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullname() for g in self.generics) + '}'

        return res

    def fullpath(self) -> str:
        res = self.struct.fullpath()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullpath() for g in self.generics) + '}'

        return res

    def member(self, name: str) -> Variable:
        self.finalize()

        if name not in self.symbols:
            raise LookupError(
                f"field '{name}' does not exist in struct '{self.struct}'")

        return self.symbols[name]

    def size(self) -> int:
        self.finalize()

        # note: struct size is only for builtins
        return self.struct.size + sum(f.type.size() for f in self.fields)

    def resolve(self, gens: Dict[str, Type]) -> 'Construct':
        fields = []
        for f in self.fields:
            var = Variable(f.name, f.type.resolve(gens), Location.Struct)
            fields.append(var)

        gen_args = []
        for g in self.generics:
            if isinstance(g, Generic):
                g = g.resolve(gens)

            gen_args.append(g)

        return Construct(self.struct, fields, gen_args)

    def finalize(self) -> None:
        if self._finalized:
            return

        size = 0
        self.symbols = {}
        for f in self.fields:
            f.offset = size
            size += f.type.size()
            self.symbols[f.name] = f

        self._finalized = True


class Special(Type):
    def __init__(self, name: str) -> None:
        self.name = name

    def __str__(self) -> str:
        return self.name

    def fullname(self) -> str:
        assert False, 'should not use fullname on special'

    def fullpath(self) -> str:
        assert False, 'should not use fullpath on special'

    def size(self) -> int:
        assert False, 'should not use size on special'

    def resolve(self, gens: Dict[str, Type]) -> 'Special':
        return self


def load_builtins() -> Module:
    mod = Module('')

    NUM_TYPES = {Construct(tp) for tp in {INT, FLOAT}}

    # classes
    for struct in {BOOL, INT, FLOAT}:
        mod.add_struct(struct)

    # constants
    for const in {TRUE, FALSE}:
        mod.add_constant(const)

    # builtin operations
    for tp in NUM_TYPES:
        # binary
        for op in ['plus', 'minus', 'multiplies', 'divides', 'modulus']:
            fn = Function(op, tp)
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

        # unary
        for op in ['pos', 'neg']:
            fn = Function(op, tp)
            fn.add_variable('value', tp)
            mod.add_function(fn)

        # comparison
        for op in ['equal', 'notEqual', 'less', 'lessEqual', 'greater',
                   'greaterEqual']:
            fn = Function(op, Construct(BOOL))
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

    for val in NUM_TYPES:
        for res in NUM_TYPES:
            if val == res:
                continue

            fn = Function('cast', res)
            fn.add_variable('value', val)
            mod.add_function(fn)

    # array subscript
    fn = Function('subscript', None)
    t = fn.add_generic('T')
    fn.add_variable('arr', Reference(Array(t), 1))
    fn.add_variable('index', Construct(INT))
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    # alloc
    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.add_variable('length', Construct(INT))
    fn.ret = Reference(Array(t), 1)
    mod.add_function(fn)

    # dealloc
    fn = Function('dealloc', VOID)
    t = fn.add_generic('T')
    fn.add_variable('reference', Reference(t, 1))
    mod.add_function(fn)

    # realloc
    fn = Function('realloc', VOID)
    t = fn.add_generic('T')
    fn.add_variable('array', Reference(Array(t), 1))
    fn.add_variable('length', Construct(INT))
    mod.add_function(fn)

    return mod

def to_type(val: str, syms: SymbolTable) -> Type:
    if val[0] == '&':
        sub = val.lstrip('&')

        tp = to_type(sub, syms)
        lvl = len(val) - len(sub)
        return Reference(tp, lvl)
    elif val[0] == '[':
        sub = val[1:-1]

        # TODO: sized arrays
        # maybe we should use the lexer for this
        tp = to_type(sub, syms)
        return Array(tp)

    struct = syms.get(val, Struct)
    assert isinstance(struct, Struct)
    return Construct(struct)

def to_level(tp, lvl: int) -> Type:
    if tp == UNKNOWN:
        return UNKNOWN

    if isinstance(tp, Reference):
        tp = tp.type

    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp

def to_ref(tp: Type) -> Reference:
    if not isinstance(tp, Reference):
        tp = Reference(tp, 0)

    return tp

def interpolate_types(tps: Iterable[Type], gens: Dict[str, Type]) -> Type:
    res: Type = DIVERGE
    unknown = False
    for other in tps:
        if other == UNKNOWN:
            unknown = True
            continue

        if other == VOID:
            return VOID

        # diverge does not affect any type
        if res == DIVERGE:
            res = other
            continue
        elif other == DIVERGE:
            continue

        if isinstance(res, Reference):
            if not isinstance(other, Reference):
                other = Reference(other, 0)

            if not match_type(res.type, other.type, gens):
                return VOID

            lvl = min(res.level, other.level)
            res = to_level(res.type, lvl)
            continue

        if isinstance(other, Reference):
            other = other.type

        if not match_type(res, other, gens):
            return VOID

    if unknown:
        return UNKNOWN

    return res

def load_module(mod_name: str, glob: Module) -> Module:
    # TODO: a better way to locate
    filename = f'ref/{mod_name}.fd'
    mod = Module(mod_name)
    glob.add_module(mod)
    with open(filename) as f:
        for line in f:
            segs: List[str] = line.split()
            tp: str = segs[0]

            if tp == 'def':
                ret: Type
                if len(segs) % 2 == 0: # void
                    [tp, name, *params] = segs
                    ret = VOID
                else:
                    [tp, name, *params, rt] = segs
                    ret = to_type(rt, mod)

                fn = Function(name, ret)
                for i in range(len(params) // 2):
                    name = params[i * 2]
                    param: Type = to_type(params[i * 2 + 1], mod)
                    fn.add_variable(name, param)
                mod.add_function(fn)

            else:
                raise ValueError('invalid declaration type')

    return mod

def resolve_overload(overloads: Set[Match], args: List[Type], ret: Type) \
        -> Set[Match]:
    res: Set[Match] = set()

    for match in overloads:
        if not match.update(args, ret):
            continue

        res = {r for r in res if not r < match}

        for other in res:
            if match < other:
                break
        else:
            res.add(match)

    return res

def check_type(sym: Symbol, tps: Tuple[type, ...]):
    for tp in tps:
        if isinstance(sym, tp):
            return

    exp = ' or '.join(t.__name__ for t in tps)
    raise LookupError(f"expecting {exp}, but got '{sym}'")

def match_type(self: Type, other: Type, gens: Dict[str, Type]) -> bool:
    if isinstance(other, Generic):
        if other.name not in gens:
            gens[other.name] = self
            return True

        other = gens[other.name]

    if isinstance(self, Generic):
        if self.name not in gens:
            gens[self.name] = other
            return True

        self = gens[self.name]

    if isinstance(self, Reference):
        return isinstance(other, Reference) \
                and self.level == other.level \
                and match_unsized(self.type, other.type, gens)

    if isinstance(self, Array):
        return isinstance(other, Array) \
                and self.length == other.length \
                and match_type(self.type, other.type, gens)

    if isinstance(self, Construct):
        if not isinstance(other, Construct):
            return False

        if self.struct != other.struct:
            return False

        for field, other_field in zip(self.fields, other.fields):
            if not match_type(field.type, other_field.type, gens):
                return False

        return True

    assert False, f'unknown type {self}'

def match_unsized(self: Type, other: Type, gens: Dict[str, Type]) -> bool:
    if isinstance(self, Array) and isinstance(other, Array):
        if not match_type(self.type, other.type, gens):
            return False

        return self.length is None or self.length == other.length

    return match_type(self, other, gens)

def accept_type(self: Type, other: Type, gens: Dict[str, Type]) -> float:
    if other == DIVERGE:
        return MATCH_PERFECT

    if self == UNKNOWN or other == UNKNOWN:
        return math.nan

    if self == VOID:
        if other == VOID:
            return MATCH_PERFECT

        return MATCH_TO_VOID

    if other == VOID:
        return None

    if isinstance(other, Generic):
        if other.name not in gens:
            gens[other.name] = self
            return MATCH_PERFECT

        other = gens[other.name]

    if isinstance(self, Generic):
        if self.name not in gens:
            gens[self.name] = other
            return MATCH_PERFECT

        self = gens[self.name]

    if isinstance(self, Reference):
        if not isinstance(other, Reference) or self.level > other.level \
                or not match_unsized(self.type, other.type, gens):
            return None

        return MATCH_PERFECT - 1.0 + self.level / other.level

    if isinstance(other, Reference):
        # auto reduction to level 0
        other = other.type
        reduction = 1.0
    else:
        reduction = 0.0

    if isinstance(self, (Array, Construct)):
        if not match_type(self, other, gens):
            return None

        return MATCH_PERFECT - reduction

    assert False, f'unknown type {self}'

BOOL = Struct('Bool', 1)
INT = Struct('Int', 4)
FLOAT = Struct('Float', 4)
UNKNOWN = Special('?')
DIVERGE = Special('Diverge')
VOID = Special('Void')

TRUE = Constant('TRUE', Construct(BOOL), True)
FALSE = Constant('FALSE', Construct(BOOL), False)

MATCH_PERFECT = 3.0
MATCH_TO_VOID = 1.0
