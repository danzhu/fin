from typing import Dict, Set, List, Iterable
import math
import os
from .reflect import Module, StructType, Function, Reference, Array, \
    SymbolTable, Type, Struct, Match, Generic, EnumerationType, Special, \
    Constant


def load_builtins() -> Module:
    mod = Module('', None, None)

    NUM_TYPES = {StructType(tp) for tp in {INT, FLOAT}}

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
            fn.add_param('left', tp)
            fn.add_param('right', tp)
            mod.add_function(fn)

        # unary
        for op in ['pos', 'neg']:
            fn = Function(op, tp)
            fn.add_param('value', tp)
            mod.add_function(fn)

        # comparison
        for op in ['equal', 'notEqual', 'less', 'lessEqual', 'greater',
                   'greaterEqual']:
            fn = Function(op, StructType(BOOL))
            fn.add_param('left', tp)
            fn.add_param('right', tp)
            mod.add_function(fn)

    for val in NUM_TYPES:
        for res in NUM_TYPES:
            if val == res:
                continue

            fn = Function('cast', res)
            fn.add_param('value', val)
            mod.add_function(fn)

    # array subscript
    fn = Function('subscript', None)
    t = fn.add_generic('T')
    fn.add_param('arr', Reference(Array(t), 1))
    fn.add_param('index', StructType(INT))
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    # alloc
    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.add_param('length', StructType(INT))
    fn.ret = Reference(Array(t), 1)
    mod.add_function(fn)

    # dealloc
    fn = Function('dealloc', VOID)
    t = fn.add_generic('T')
    fn.add_param('reference', Reference(t, 1))
    mod.add_function(fn)

    # realloc
    fn = Function('realloc', VOID)
    t = fn.add_generic('T')
    fn.add_param('array', Reference(Array(t), 1))
    fn.add_param('length', StructType(INT))
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
    return StructType(struct)


def to_level(tp: Type, lvl: int) -> Type:
    assert tp is not None
    assert tp != UNKNOWN

    if isinstance(tp, Reference):
        tp = tp.type

    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp


def to_ref(tp: Type) -> Reference:
    assert tp is not None
    assert tp != UNKNOWN

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


def load_module(mod_name: str, parent: Module) -> Module:
    # TODO: a better way to locate
    loc = os.path.dirname(os.path.realpath(__file__))
    filename = os.path.join(loc, 'ref', f'{mod_name}.fd')
    mod = Module(mod_name, parent)
    with open(filename) as f:
        for line in f:
            segs: List[str] = line.split()
            tp: str = segs[0]

            if tp == 'def':
                ret: Type
                if len(segs) % 2 == 0:  # void
                    [tp, name, *params] = segs
                    ret = VOID
                else:
                    [tp, name, *params, rt] = segs
                    ret = to_type(rt, mod)

                fn = Function(name, ret)
                for i in range(len(params) // 2):
                    name = params[i * 2]
                    param: Type = to_type(params[i * 2 + 1], mod)
                    fn.add_param(name, param)
                mod.add_function(fn)

            else:
                raise ValueError('invalid declaration type')

    return mod


def resolve_overload(overloads: Set[Match],
                     args: List[Type],
                     ret: Type) -> Set[Match]:
    assert None not in args and ret is not None

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

    if isinstance(self, StructType):
        if not isinstance(other, StructType):
            return False

        if self.struct != other.struct:
            return False

        for gen, other_gen in zip(self.generics, other.generics):
            if not match_type(gen, other_gen, gens):
                return False

        return True

    if isinstance(self, EnumerationType):
        if not isinstance(other, EnumerationType):
            return False

        if self.enum != other.enum:
            return False

        for gen, other_gen in zip(self.generics, other.generics):
            if not match_type(gen, other_gen, gens):
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

    if isinstance(self, (Array, StructType, EnumerationType)):
        if not match_type(self, other, gens):
            return None

        return MATCH_PERFECT - reduction

    assert False, f'unknown type {self}'


# structs
BOOL = Struct('Bool', 1)
INT = Struct('Int', 4)
FLOAT = Struct('Float', 4)

# types
BOOL_TYPE = StructType(BOOL)
INT_TYPE = StructType(INT)
FLOAT_TYPE = StructType(FLOAT)
UNKNOWN = Special('?')
DIVERGE = Special('Diverge')
VOID = Special('Void')

# constants
TRUE = Constant('TRUE', BOOL_TYPE, True)
FALSE = Constant('FALSE', BOOL_TYPE, False)

MATCH_PERFECT = 3.0
MATCH_TO_VOID = 1.0
