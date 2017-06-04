#!/usr/bin/env python3

from enum import Enum
import math

class Location(Enum):
    Global = 0
    Struct = 1
    Param  = 2
    Local  = 3


class Symbol(Enum):
    Module   = 0
    Struct   = 1
    Function = 2
    Variable = 3
    Constant = 4


MATCH_PERFECT = 3.0
MATCH_REDUCTION = 2.0
MATCH_TO_NONE = 1.0


class Variable:
    TYPE = Symbol.Variable

    def __init__(self, name, tp, loc, off):
        self.name = name
        self.type = tp
        self.location = loc
        self.offset = off

    def __str__(self):
        return '{} {}'.format(self.name, self.type, self.location)

    def var_type(self):
        if type(self.type) is not Reference:
            return Reference(self.type, 1)
        else:
            return Reference(self.type.type, self.type.level + 1)


class Constant:
    TYPE = Symbol.Constant

    def __init__(self, name, tp, val):
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self):
        return self.type


class Generic:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def size(self):
        assert False, 'should not use size on generic'

    def match(self, other, gens):
        if self.name in gens:
            return gens[self.name].match(other, gens)
        else:
            gens[self.name] = other
            return True

    def accept(self, other, gens):
        if self.name in gens:
            return gens[self.name].accept(other, gens)

        else:
            gens[self.name] = other
            return MATCH_PERFECT

    def resolve(self, gens):
        return gens[self.name]


class SymbolTable:
    def __init__(self, parent=None):
        self.parent = parent

        self.symbols = {}

    def _check_exists(self, name):
        if name in self.symbols:
            raise KeyError("symbol '{}' exists as {}".format(
                name, self.symbols[name]))

    def _add_symbol(self, sym):
        self._check_exists(sym.name)
        self.symbols[sym.name] = sym

    def find(self, name):
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.find(name)

        return None

    def get(self, name, *tps):
        sym = self.find(name)

        if sym is None:
            raise KeyError('cannot find symbol "{}"'.format(name))

        if sym.TYPE not in tps:
            raise TypeError('expected {}, but got {} "{}"'.format(
                ' or '.join(str(t) for t in tps), sym.TYPE, name))

        return sym

    def ancestor(self, sym):
        if self.TYPE == sym:
            return self

        if self.parent is not None:
            return self.parent.ancestor(sym)

        raise LookupError('no ancestor of type {}'.format(sym))

    def overloads(self, name):
        if self.parent is not None:
            res = self.parent.overloads(name)
        else:
            res = set()

        if name in self.symbols:
            fns = self.symbols[name]

            if type(fns) is not set:
                raise LookupError('{} "{}" is not a function'.format(
                    fns.TYPE,
                    name))

            res |= {Match(fn) for fn in fns}

        return res


class Module(SymbolTable):
    LOCATION = Location.Global
    TYPE = Symbol.Module

    def __init__(self, name):
        super().__init__()

        # TODO: version
        self.name = name

    def __lt__(self, other):
        return self.name < other.name

    def fullname(self):
        return self.name

    def fullpath(self):
        if self.parent is not None:
            assert self.parent.TYPE == Symbol.Module

            # FIXME: use correct module hierarchy for this to work
            # return self.parent.path('.') + self.fullname()
            return self.fullname()
        else:
            return self.fullname()

    def path(self, sep=':'):
        path = self.fullpath()
        if path != '':
            path += sep

        return path

    def add_module(self, mod):
        self._add_symbol(mod)
        mod.parent = self

    def add_struct(self, struct):
        self._add_symbol(struct)
        struct.parent = self

    def add_function(self, fn):
        if fn.name not in self.symbols:
            group = set()
            self.symbols[fn.name] = group

        elif type(self.symbols[fn.name]) is not set:
            # TODO: better way to check
            raise KeyError('redefining non-function as function')

        else:
            group = self.symbols[fn.name]

        group.add(fn)
        fn.parent = self

    def add_variable(self, name, tp):
        raise NotImplementedError()

    def add_constant(self, const):
        self._add_symbol(const)



class Struct(SymbolTable):
    LOCATION = Location.Struct
    TYPE = Symbol.Struct

    def __init__(self, name, size=0):
        super().__init__()

        self.name = name
        self._size = size

    def __str__(self):
        return self.name

    def size(self):
        return self._size

    def fullname(self):
        return self.name

    def fullpath(self):
        return self.ancestor(Symbol.Module).path() + self.fullname()

    def add_variable(self, name, tp):
        var = Variable(name, tp, Location.Struct, self._size)
        self._size += tp.size()

        self._add_symbol(var)

        return var

    def match(self, other, gens):
        return self == other

    def accept(self, other, gens):
        if self == UNKNOWN or other == UNKNOWN:
            return math.nan

        # if reference, reduce to level 0
        ref = type(other) is Reference
        if ref:
            other = other.type

        elif type(other) is Generic:
            gens[other.name] = self
            return MATCH_PERFECT

        elif type(other) is not Struct:
            # does not accept other types
            return None

        if self == other:
            # score is lower if there's level reduction
            return MATCH_REDUCTION if ref else MATCH_PERFECT
        elif self == NONE:
            return MATCH_TO_NONE
        else:
            return None

    def interpolate(self, other):
        if type(other) is Reference:
            other = other.type

        if self == UNKNOWN or other == UNKNOWN:
            return UNKNOWN

        if self != other:
            return NONE

        return self

    def resolve(self, gens):
        return self


class Function(SymbolTable):
    LOCATION = Location.Param
    TYPE = Symbol.Function

    def __init__(self, name, ret):
        super().__init__()

        self.name = name
        self.ret = ret

        self.params = []
        self.generics = []

    def __str__(self):
        return '{}{}({}){}'.format(
                self.name,
                '{' + ', '.join(str(g) for g in self.generics) + '}'
                    if self.generics else '',
                ', '.join(str(p) for p in self.params),
                ' ' + str(self.ret) if self.ret != NONE else '')

    def fullname(self):
        # TODO: generic parameters
        return '{}({}){}'.format(
                self.name,
                ','.join(p.type.fullpath() for p in self.params),
                self.ret.fullpath() if self.ret != NONE else '')

    def fullpath(self):
        return self.ancestor(Symbol.Module).path() + self.fullname()

    def add_variable(self, name, tp):
        assert type(name) is str

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def add_generic(self, name):
        assert type(name) is str

        gen = Generic(name)

        self._add_symbol(gen)
        self.generics.append(gen)

        return gen

    def resolve(self, args, ret):
        if len(self.params) != len(args):
            return None, None

        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        gens = {}
        lvls = [p.type.accept(a, gens) for p, a in zip(self.params, args)]

        if ret is not None:
            lvls.append(ret.accept(self.ret, gens))
        else:
            lvls.append(math.nan)

        if None in lvls:
            return None, None

        return lvls, gens


class Block(SymbolTable):
    LOCATION = Location.Local

    def __init__(self, parent):
        super().__init__(parent)

        self.offset = 0

        if parent.LOCATION == Location.Local:
            self.parent_offset = parent.offset
        else:
            self.parent_offset = 0

    def add_variable(self, name, tp):
        offset = self.parent_offset + self.offset
        var = Variable(name, tp, Location.Local, offset)
        self.offset += tp.size()

        self._add_symbol(var)

        return var


class Match:
    def __init__(self, fn):
        self.function = fn

    def __lt__(self, other):
        assert len(self.levels) == len(other.levels)

        less = False
        for s, o in zip(self.levels, other.levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self):
        return '{} {}'.format(self.function, self.levels)

    def update(self, args, ret):
        self.levels, self.gens = self.function.resolve(args, ret)
        return self.levels is not None


class Reference:
    def __init__(self, tp, lvl):
        assert type(tp) is not Reference

        self.type = tp
        self.level = lvl

    def __str__(self):
        return str(self.type) + '&' * self.level

    def fullname(self):
        return self.type.fullname() + '&' * self.level

    def fullpath(self):
        return self.type.fullpath() + '&' * self.level

    def size(self):
        return 8 # size of pointer

    def match(self, other, gens):
        if type(other) is not Reference:
            return False
        return self.level == other.level and self.type.match(other.type, gens)

    def accept(self, other, gens):
        if self == UNKNOWN or other == UNKNOWN:
            return math.nan

        if type(other) is not Reference:
            other = Reference(other, 0)

        if self.level > other.level:
            if type(other.type) is Generic:
                gens[other.type.name] = to_level(self.type,
                        self.level - other.level)
                return MATCH_PERFECT
            else:
                return None

        if self.type.match(other.type, gens):
            return MATCH_REDUCTION + self.level / other.level
        else:
            return None

    def interpolate(self, other):
        if other == UNKNOWN:
            return UNKNOWN

        if type(other) is not Reference:
            other = Reference(other, 0)

        tp = self.type.interpolate(other.type)

        lvl = min(self.level, other.level)
        if lvl > 0:
            tp = Reference(tp, lvl)

        return tp

    def resolve(self, gens):
        return Reference(self.type.resolve(gens), self.level)


class Array:
    def __init__(self, tp, size=-1):
        self.type = tp
        self._size = size

    def __str__(self):
        return '[{}]'.format(self.type)

    def size(self):
        if self._size == -1:
            raise TypeError('array is unsized')
        return self._size

    def match(self, other, gens):
        if type(other) is not Array:
            return False
        return self.type.match(other.type, gens)

    def accept(self, other, gens):
        if self == UNKNOWN or other == UNKNOWN:
            return math.nan

        if type(other) is not Array:
            return None

        return self.type == other.type

    def resolve(self, gens):
        return Array(self.type.resolve(gens))


NONE = Struct('None', 0)
BOOL = Struct('Bool', 1)
INT = Struct('Int', 4)
FLOAT = Struct('Float', 4)
UNKNOWN = Struct('?', -1)

TRUE = Constant('TRUE', BOOL, True)
FALSE = Constant('FALSE', BOOL, False)

def load_builtins():
    mod = Module('')

    # classes
    for struct in { NONE, BOOL, INT, FLOAT }:
        mod.add_struct(struct)

    # constants
    for const in { TRUE, FALSE }:
        mod.add_constant(const)

    # builtin operations
    for tp in { INT, FLOAT }:
        # binary
        for op in ['+', '-', '*', '/', '%']:
            fn = Function(op, tp)
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

        # unary
        for op in ['+', '-']:
            fn = Function(op, tp)
            fn.add_variable('value', tp)
            mod.add_function(fn)

        # comparison
        for op in ['<', '<=', '>', '>=', '==', '!=']:
            fn = Function(op, BOOL)
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

        # incremental assignment
        for op in ['+=', '-=', '*=', '/=', '%=']:
            fn = Function(op, NONE)
            fn.add_variable('self', Reference(tp, 1))
            fn.add_variable('value', tp)
            mod.add_function(fn)

    # array subscript
    fn = Function('[]', None)
    t = fn.add_generic('T')
    fn.add_variable('arr', Reference(Array(t), 1))
    fn.add_variable('index', INT)
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    return mod

def to_type(val, syms):
    name = val.rstrip('&')
    tp = syms.get(name, Symbol.Struct)

    lvl = len(val) - len(name)
    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp

def to_level(tp, lvl):
    if tp == UNKNOWN:
        return UNKNOWN

    if type(tp) is Reference:
        tp = tp.type

    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp

def to_ref(tp):
    if type(tp) is not Reference:
        tp = Reference(tp, 0)

    return tp

def interpolate_types(tps):
    res = tps[0]
    for tp in tps[1:]:
        res = res.interpolate(tp)
    return res

def load_module(mod_name, glob):
    # TODO: a better way to locate
    filename = 'ref/{}.fd'.format(mod_name)
    mod = Module(mod_name)
    glob.add_module(mod)
    with open(filename) as f:
        for line in f:
            [tp, name, *params, ret] = line.split()

            if tp == 'def':
                fn = Function(name, to_type(ret, mod))
                for i in range(len(params) // 2):
                    name = params[i * 2]
                    tp = to_type(params[i * 2 + 1], mod)
                    fn.add_variable(name, tp)
                mod.add_function(fn)

            else:
                raise ValueError('invalid declaration type')

    return mod

def resolve_overload(overloads, args, ret):
    res = set()

    for match in overloads:
        if not match.update(args, ret):
            continue

        res = {r for r in res if not r < match}

        for r in res:
            if match < r:
                break
        else:
            res.add(match)

    return res
