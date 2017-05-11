#!/usr/bin/env python3

class RuntimeType:
    def __init__(self, name, size):
        self.name = name
        self.size = size


class ExprType:
    def __init__(self, tp: RuntimeType, lvl=0):
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
    def __init__(self, name, args, ret):
        self.name = name
        self.args = args
        self.ret = ret

    def __str__(self):
        return '{}({}){}'.format(
                self.name,
                ','.join(str(arg) for arg in self.args),
                self.ret)


NONE = RuntimeType('fin.None', 0)
BOOL = RuntimeType('fin.Bool', 1)
INT = RuntimeType('fin.Int', 4)

def builtin_types():
    return {
            'Bool': BOOL,
            'Int': INT
            }

def builtin_fns():
    return {
            'print': FunctionType('fin.print', [ExprType(INT)], ExprType(NONE)),
            'input': FunctionType('fin.input', [], ExprType(INT)),
            }
