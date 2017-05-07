#!/usr/bin/env python3

import tps
from tps import ExprType

class Node:
    def __init__(self, tp, children, val=None, lvl=0):
        self.type = tp
        self.children = children
        self.value = val
        # TODO: maybe this should be stored somewhere else?
        self.level = lvl

        self.expr = False

    def print(self, indent=0):
        content = ' ' * indent + self.type
        if self.value:
            content += ' {}'.format(self.value)
        if self.expr:
            content += ' [{}]'.format(self.expr_type)
        if self.level > 0:
            content += ' {}'.format(self.level)
        print(content)
        for c in self.children:
            c.print(indent + 2)

    def analyze(self):
        types = tps.builtin_types()
        fns = tps.builtin_fns()
        ids = SymbolTable()
        self._annotate(types, fns, ids)

    def _annotate(self, types, fns, ids):
        # expr
        if self.type == 'CALL':
            pass
        elif self.expr or self.type in ['EXPR', 'ASSN', 'ARGS']:
            for c in self.children:
                c.expr = True
        elif self.type in ['IF', 'WHILE']:
            self.children[0].expr = True

        # process children
        for c in self.children:
            c._annotate(types, fns, ids)

        # expr type
        if self.type == 'TYPE':
            tp = types[self.children[0].value]
            lvl = len(self.children)
            self.expr_type = ExprType(tp, lvl)
        elif not self.expr:
            # ignore type of non-expressions
            pass
        elif self.type == 'ID':
            self.id = ids[self.value]
            self.expr_type = self.id.type
        elif self.type == 'NUM':
            self.expr_type = ExprType(tps.INT, 0)
        elif self.type == 'BIN':
            # TODO: implicit conversion
            if self.children[0].expr_type.type != \
                    self.children[1].expr_type.type:
                raise TypeError()

            self.expr_type = ExprType(self.children[0].expr_type.type, 0)
        elif self.type == 'COMP':
            # TODO: type check
            self.expr_type = ExprType(tps.BOOL, 0)
        elif self.type == 'CALL':
            fn = fns[self.children[0].value]
            self.expr_type = fn.ret

        if self.type == 'LET':
            ids.add(self.children[0].value, self.children[1].expr_type)


class SymbolTable:
    def __init__(self, parent=None):
        self.symbols = {}
        self.offset = 0
        self.parent = parent

    def __getitem__(self, name):
        if name in self.symbols:
            return self.symbols[name]
        elif self.parent:
            return self.parent[name]
        else:
            raise KeyError(name)

    def add(self, name, tp):
        # TODO: get real size
        self.symbols[name] = Symbol(name, self.offset, tp)
        self.offset += tp.var_size()


class Symbol:
    def __init__(self, name, off, tp):
        self.name = name
        self.offset = off
        self.type = tp
