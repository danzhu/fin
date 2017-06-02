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
    Class    = 1
    Function = 2
    Variable = 3
    Constant = 4


class Type:
    def __init__(self, cls, lvl=0):
        self.cls = cls
        self.level = lvl

    def __str__(self):
        return self.cls.name + '&' * self.level

    def fullname(self):
        return self.cls.fullname() + '&' * self.level

    def fullpath(self):
        return self.cls.fullpath() + '&' * self.level

    def size(self, lvl=-1):
        if lvl == -1:
            lvl = self.level
        if lvl > 0:
            return 8 # size of pointer
        else:
            return self.cls.size

    def none(self):
        return self.cls == NONE and self.level == 0

    def empty(self):
        return self.cls.size == 0 and self.level == 0

    def match(self, tp):
        # 0: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match

        # (Python's) None value denotes unknown type
        if tp is None:
            return math.nan

        if self.cls != tp.cls:
            if self.none():
                # everything can be cast to None
                return 1
            else:
                # otherwise, type mismatch
                return 0

        if self.level > tp.level:
            return 0

        if self.level < tp.level:
            return 2

        return 3


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
        return Type(self.type.cls, self.type.level + 1)


class Constant:
    TYPE = Symbol.Constant

    def __init__(self, name, cls, val):
        self.name = name
        self.cls = cls
        self.value = val

        self.type = Type(cls)

    def var_type(self):
        return Type(self.cls)


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

    def add_class(self, cls):
        self._add_symbol(cls)
        cls.parent = self

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



class Class(SymbolTable):
    LOCATION = Location.Struct
    TYPE = Symbol.Class

    def __init__(self, name, size=0):
        super().__init__()

        self.name = name
        self.size = size

    def fullname(self):
        return self.name

    def fullpath(self):
        return self.ancestor(Symbol.Module).path() + self.fullname()

    def add_variable(self, name, tp):
        var = Variable(name, tp, Location.Struct, self.size)
        self.size += tp.size()

        self._add_symbol(var)

        return var


class Function(SymbolTable):
    LOCATION = Location.Param
    TYPE = Symbol.Function

    def __init__(self, name, ret):
        super().__init__()

        self.name = name
        self.ret = ret

        self.params = []

    def __str__(self):
        return '{}({}){}'.format(
                self.name,
                ', '.join(str(p) for p in self.params),
                ' ' + str(self.ret) if not self.ret.none() else '')

    def fullname(self):
        return '{}({}){}'.format(
                self.name,
                ','.join(p.type.fullpath() for p in self.params),
                self.ret.fullpath() if not self.ret.none() else '')

    def fullpath(self):
        return self.ancestor(Symbol.Module).path() + self.fullname()

    def add_variable(self, name, tp):
        assert type(name) is str
        assert type(tp) is Type

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def match(self, args, ret):
        if len(self.params) != len(args):
            return None

        lvls = [p.type.match(a) for p, a in zip(self.params, args)]

        if ret is not None:
            lvls.append(ret.match(self.ret))
        else:
            lvls.append(math.nan)

        if 0 in lvls:
            return None

        return lvls


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
        assert len(self.match) == len(other.match)

        less = False
        for s, o in zip(self.match, other.match):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def update(self, args, ret):
        self.match = self.function.match(args, ret)
        return self.match is not None


NONE = Class('None', 0)
BOOL = Class('Bool', 1)
INT = Class('Int', 4)
FLOAT = Class('Float', 4)

TRUE = Constant('TRUE', BOOL, True)
FALSE = Constant('FALSE', BOOL, False)

NUM_TYPES = [INT, FLOAT]

def load_builtins():
    mod = Module('')

    # classes
    for cls in { NONE, BOOL, INT, FLOAT }:
        mod.add_class(cls)

    # constants
    for const in { TRUE, FALSE }:
        mod.add_constant(const)

    # builtin operations
    for cls in { INT, FLOAT }:
        tp = Type(cls)

        # binary
        for op in ['+', '-', '*', '/', '%']:
            fn = Function(op, tp)
            fn.add_variable('l', tp)
            fn.add_variable('r', tp)
            mod.add_function(fn)

        # unary
        for op in ['+', '-']:
            fn = Function(op, tp)
            fn.add_variable('v', tp)
            mod.add_function(fn)

        # comparison
        for op in ['<', '<=', '>', '>=', '==', '!=']:
            fn = Function(op, Type(BOOL))
            fn.add_variable('l', tp)
            fn.add_variable('r', tp)
            mod.add_function(fn)

    return mod

def to_type(tp, syms):
    name = tp.rstrip('&')
    lvl = len(tp) - len(name)
    return Type(syms.get(name, Symbol.Class), lvl)

def interpolate_types(tps):
    if None in tps:
        return None

    cls = tps[0].cls
    lvl = tps[0].level
    for tp in tps:
        if tp.cls != cls:
            return Type(NONE)
        lvl = min(lvl, tp.level)
    return Type(cls, lvl)

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

def resolve_overload(matches, args, ret):
    res = set()

    for match in matches:
        if not match.update(args, ret):
            continue

        res = {r for r in res if not r < match}

        for r in res:
            if match < r:
                break
        else:
            res.add(match)

    return res
