#!/usr/bin/env python3

from enum import Enum

class Location(Enum):
    Global = 0
    Module = 1
    Param = 2
    Local = 3


class SymbolTable:
    def __init__(self, loc, parent=None, fn=None):
        self.location = loc
        self.parent = parent

        # for checking return type
        if fn or not parent:
            self.function = fn
        else:
            self.function = parent.function

        self.symbols = {}
        self.references = set()

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
        if fn.name in self.symbols:
            group = self.symbols[fn.name]
            if group.TYPE != 'FN_GROUP':
                raise KeyError('redefining non-function as function')
        else:
            group = FunctionGroup(fn.name)
            self.symbols[group.name] = group

        group.add(fn)

    def add_variable(self, name, tp):
        self._check_exists(name)

        offset = self.parent_offset + self.offset
        var = Variable(name, self.location, offset, tp, self)
        self.symbols[name] = var
        self.offset += tp.var_size()
        return var

    def add_constant(self, const):
        self._check_exists(const.name)

        self.symbols[const.name] = const

    def get(self, name, *tps):
        if name in self.symbols:
            sym = self.symbols[name]

            if sym.TYPE not in tps:
                raise TypeError('expected {}, but got {} "{}"'.format(
                    ' or '.join(tps), sym.TYPE, name))

            if self.location == Location.Global:
                self.references.add(sym)

            return sym

        elif self.parent:
            return self.parent.get(name, *tps)
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


class Constant:
    TYPE = 'CONSTANT'

    def __init__(self, name, cls, val):
        self.name = name
        self.cls = cls
        self.value = val

        self.type = Type(cls)


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

    def accept(self, tp):
        # everything can be cast to None
        if self.none():
            return True

        # (Python's) None value denotes unknown type
        if tp is None or tp.none():
            return True

        if self.cls != tp.cls:
            return False

        if self.level > tp.level:
            return False

        return True


class Module:
    TYPE = 'MODULE'

    def __init__(self, name):
        # TODO: version
        self.name = name
        self.functions = {}

    def add_function(self, fn):
        self.functions[fn.name] = fn


class FunctionGroup:
    TYPE = 'FN_GROUP'

    def __init__(self, name):
        self.name = name
        self.functions = set()

    def add(self, fn):
        self.functions.add(fn)

    def resolve(self, params, ret):
        fns = set()
        for fn in self.functions:
            if fn.match(params, ret):
                fns.add(fn)

        return fns


class Function:
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

    def match(self, params, ret):
        if len(self.params) != len(params):
            return False

        for i in range(len(params)):
            if not self.params[i].accept(params[i]):
                return False

        if not self.ret.accept(ret):
            return False

        return True


NONE = Class('None', 0)
BOOL = Class('Bool', 1)
INT = Class('Int', 4)
FLOAT = Class('Float', 4)

TRUE = Constant('TRUE', BOOL, True)
FALSE = Constant('FALSE', BOOL, False)

NUM_TYPES = [INT, FLOAT]

def load_builtins(syms):
    for tp in { NONE, BOOL, INT, FLOAT }:
        syms.add_class(tp)
    for const in { TRUE, FALSE }:
        syms.add_constant(const)

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
