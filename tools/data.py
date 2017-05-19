#!/usr/bin/env python3

from enum import Enum

class Location(Enum):
    Global = 0
    Param = 1
    Local = 2


class SymbolTable:
    def __init__(self, loc, parent=None, fn=None):
        self.location = loc
        self.parent = parent

        if fn or not parent:
            self.function = fn
        else:
            self.function = parent.function

        self.symbols = {}

        self.offset = 0
        self.parent_offset = 0

        if parent and parent.location == loc:
            self.parent_offset = parent.offset

    def _check_exists(self, name):
        if name in self.symbols:
            raise KeyError('symbol exists')

    def add_class(self, cls):
        self._check_exists(cls.name)

        self.symbols[cls.name] = cls

    def add_function(self, fn):
        self._check_exists(fn.name)

        self.symbols[fn.name] = fn

    def add_variable(self, name, tp):
        self._check_exists(name)

        offset = self.parent_offset + self.offset
        var = Variable(name, self.location, offset, tp, self)
        self.symbols[name] = var
        self.offset += tp.var_size()
        return var

    def get(self, name, tp=None):
        if name in self.symbols:
            sym = self.symbols[name]
            if tp is None or sym.TYPE == tp:
                return sym

            raise LookupError('expected {}, but got {} "{}"'.format(
                tp, sym.TYPE, name))
        elif self.parent:
            return self.parent.get(name, tp)
        else:
            raise KeyError('cannot find symbol "{}"'.format(name))


class Variable:
    TYPE = 'VARIABLE'

    def __init__(self, name, loc, off, tp, syms):
        self.name = name
        self.location = loc
        self.offset = off
        self.type = tp
        self.symbol_table = syms


class Class:
    TYPE = 'CLASS'

    def __init__(self, name, size):
        self.name = name
        self.size = size


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

    def var_size(self):
        return self.size(self.level - 1)

    def none(self):
        return self.cls.size == 0 and self.level == 0


class Module:
    TYPE = 'MODULE'

    def __init__(self, name):
        # TODO: version
        self.name = name
        self.functions = {}

    def add_function(self, fn):
        self.functions[fn.name] = fn


class Function:
    TYPE = 'FUNCTION'

    def __init__(self, mod, name, params, ret):
        self.module = mod
        self.name = name
        self.params = params
        self.ret = ret

    def __str__(self):
        return '{}{}({}){}'.format(
                self.module.name + ':' if self.module.name else '',
                self.name,
                ','.join(str(param) for param in self.params),
                self.ret if not self.ret.none() else '')


NONE = Class('None', 0)
BOOL = Class('Bool', 1)
INT = Class('Int', 4)
FLOAT = Class('Float', 4)

NUM_TYPES = [INT, FLOAT]

def load_builtins(syms):
    for tp in { NONE, BOOL, INT, FLOAT }:
        syms.add_class(tp)

def to_type(tp, syms):
    name = tp.rstrip('&')
    lvl = len(tp) - len(name)
    return Type(syms.get(name, 'CLASS'), lvl)

def interpolate_types(tps):
    cls = tps[0].cls
    lvl = tps[0].level
    for tp in tps:
        if tp.cls != cls:
            return Type(NONE)
        lvl = min(lvl, tp.level)
    return Type(cls, lvl)

def load_module(mod_name, syms):
    # TODO: a better way to locate
    filename = 'ref/{}.fd'.format(mod_name)
    with open(filename) as f:
        mod = Module(mod_name)
        for line in f:
            [tp, name, *args] = line.split()

            if tp == 'def':
                params = [to_type(tp, syms) for tp in args[:-1]]
                ret = to_type(args[-1], syms)
                fn = Function(mod, name, params, ret)
                mod.add_function(fn)
                syms.add_function(fn)

            else:
                raise ValueError('invalid declaration type')
