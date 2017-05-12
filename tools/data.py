#!/usr/bin/env python3

from enum import Enum

class Location(Enum):
    Frame = 0
    Global = 1


class SymbolTable:
    def __init__(self, loc, parent=None):
        self.location = loc
        self.parent = parent

        self.symbols = {}
        self.offset = 0

    def __getitem__(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent[name]
        else:
            raise KeyError(name)

    def add(self, name, tp):
        self.symbols[name] = Symbol(name, self.location, self.offset, tp)
        self.offset += tp.var_size()


class Symbol:
    def __init__(self, name, loc, off, tp):
        self.name = name
        self.location = loc
        self.offset = off
        self.type = tp


class Class:
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


class Module:
    def __init__(self, name):
        # TODO: version
        self.name = name
        self.functions = {}

    def add_function(self, fn):
        self.functions[fn.name] = fn


class Function:
    def __init__(self, mod, name, args, ret):
        self.module = mod
        self.name = name
        self.args = args
        self.ret = ret

    def __str__(self):
        return '{}:{}({}){}'.format(
                self.module.name,
                self.name,
                ','.join(str(arg) for arg in self.args),
                self.ret)


NONE = Class('None', 0)
BOOL = Class('Bool', 1)
INT = Class('Int', 4)

def builtin_types():
    tps = { NONE, BOOL, INT }
    return { cls.name: cls for cls in tps }

def to_type(tp, tps):
    name = tp.rstrip('&')
    lvl = len(tp) - len(name)
    return Type(tps[name], lvl)

def load_module(mod_name, tps, fns):
    # TODO: a better way to locate
    filename = 'ref/{}.fd'.format(mod_name)
    with open(filename) as f:
        mod = Module(mod_name)
        for line in f:
            [tp, name, *args] = line.split()

            if tp == 'def':
                params = [to_type(tp, tps) for tp in args[:-1]]
                ret = to_type(args[-1], tps)
                fn = Function(mod, name, params, ret)
                mod.add_function(fn)
                fns[fn.name] = fn

            else:
                raise ValueError('invalid declaration type')
