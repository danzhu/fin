#!/usr/bin/env python3

class RuntimeType:
    def __init__(self, name, size):
        self.name = name
        self.size = size


class ExprType:
    def __init__(self, tp: RuntimeType, lvl):
        self.type = tp
        self.level = lvl

    def __str__(self):
        s = self.type.name + '&' * self.level
        return s

    def size(self, lvl=-1):
        if lvl == -1:
            lvl = self.level
        if lvl > 0:
            return 8 # size of pointer
        else:
            return self.type.size

    def var_size(self):
        return self.size(self.level - 1)


class FunctionType:
    def __init__(self, ret: ExprType):
        self.ret = ret

    def __str__(self):
        return '{}'.format(self.ret)


NONE = RuntimeType('None', 0)
BOOL = RuntimeType('Bool', 1)
INT = RuntimeType('Int', 4)

def builtin_types():
    types = { BOOL, INT }
    return {tp.name: tp for tp in types}

def builtin_fns():
    return {
            'print': FunctionType(ExprType(NONE, 0)),
            'input': FunctionType(ExprType(INT, 0)),
            }
