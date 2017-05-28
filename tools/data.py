#!/usr/bin/env python3

from enum import Enum

class Location(Enum):
    Module = 0
    Struct = 1
    Param  = 2
    Local  = 3


class Symbol(Enum):
    Module   = 0
    Class    = 1
    FnGroup  = 2
    Variable = 3
    Constant = 4


class Type:
    def __init__(self, cls, lvl=0):
        self.cls = cls
        self.level = lvl

    def __str__(self):
        s = self.cls.name + '&' * self.level
        return s

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
        # 4: unknown

        # (Python's) None value denotes unknown type
        if tp is None:
            return 4

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
        return '{} {} [{}]'.format(self.name, self.type, self.location)

    def var_type(self):
        return Type(self.type.cls, self.type.level + 1)


class Constant:
    TYPE = Symbol.Constant

    def __init__(self, name, cls, val):
        self.name = name
        self.cls = cls
        self.value = val

        self.type = Type(cls)


class FunctionGroup:
    TYPE = Symbol.FnGroup

    def __init__(self, name):
        self.name = name
        self.functions = set()

    def add(self, fn):
        self.functions.add(fn)

    def resolve(self, params, ret):
        fns = set()
        max_lvl = 1

        for fn in self.functions:
            lvl = fn.match(params, ret)

            if lvl < max_lvl:
                continue

            if lvl > max_lvl:
                max_lvl = lvl
                fns = set()

            fns.add(fn)

        return fns


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

    def get(self, name, *tps):
        if name in self.symbols:
            sym = self.symbols[name]

            if sym.TYPE not in tps:
                raise TypeError('expected {}, but got {} "{}"'.format(
                    ' or '.join(tps), sym.TYPE, name))

            return sym

        elif self.parent:
            return self.parent.get(name, *tps)
        else:
            raise KeyError('cannot find symbol "{}"'.format(name))

    def ancestor(self, loc):
        if self.LOCATION == loc:
            return self
        elif self.parent is not None:
            return self.parent.ancestor(loc)
        else:
            raise LookupError('no ancestor of location {}'.format(loc))


class Module(SymbolTable):
    LOCATION = Location.Module
    TYPE = Symbol.Module

    def __init__(self, name):
        super().__init__()

        # TODO: version
        self.name = name

    def __lt__(self, other):
        return self.name < other.name

    def add_module(self, mod):
        self._add_symbol(mod)
        mod.parent = self

    def add_class(self, cls):
        self._add_symbol(cls)
        cls.parent = self

    def add_function(self, fn):
        if fn.name not in self.symbols:
            group = FunctionGroup(fn.name)
            self.symbols[group.name] = group
        elif self.symbols[fn.name].TYPE != Symbol.FnGroup:
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

    def add_variable(self, name, tp):
        var = Variable(name, tp, Location.Struct, self.size)
        self.size += tp.size()

        self._add_symbol(var)

        return var


class Function(SymbolTable):
    LOCATION = Location.Param

    def __init__(self, name, ret):
        super().__init__()

        self.name = name
        self.ret = ret

        self.params = []

    def __str__(self):
        return '{}({}){}'.format(
                self.name,
                ','.join(str(param.type) for param in self.params),
                self.ret if not self.ret.none() else '')

    def fullname(self):
        return '{}:{}'.format(self.ancestor(Location.Module).name, self)

    def add_variable(self, name, tp):
        assert type(name) is str
        assert type(tp) is Type

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def match(self, params, ret):
        if len(self.params) != len(params):
            return 0

        if ret is not None:
            lvl = ret.match(self.ret)
        else:
            lvl = 4

        for i in range(len(params)):
            lvl = min(lvl, self.params[i].type.match(params[i]))

        return lvl


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


NONE = Class('None', 0)
BOOL = Class('Bool', 1)
INT = Class('Int', 4)
FLOAT = Class('Float', 4)

TRUE = Constant('TRUE', BOOL, True)
FALSE = Constant('FALSE', BOOL, False)

NUM_TYPES = [INT, FLOAT]

def load_builtins():
    mod = Module('')
    for tp in { NONE, BOOL, INT, FLOAT }:
        mod.add_class(tp)
    for const in { TRUE, FALSE }:
        mod.add_constant(const)
    return mod

def to_type(tp, syms):
    name = tp.rstrip('&')
    lvl = len(tp) - len(name)
    return Type(syms.get(name, Symbol.Class), lvl)

def interpolate_types(tps):
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
                    name = params[i]
                    tp = to_type(params[i + 1], mod)
                    fn.add_variable(name, tp)
                mod.add_function(fn)

            else:
                raise ValueError('invalid declaration type')

    return mod
