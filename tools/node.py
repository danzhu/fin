#!/usr/bin/env python3

class Node:
    def __init__(self, tp, children, val=None, lvl=0):
        self.type = tp
        self.children = children
        self.value = val
        self.level = lvl

    def print(self, indent=0):
        content = ' ' * indent + self.type
        if self.value:
            content += ' {}'.format(self.value)
        if self.expr:
            content += ' [' + str(self.expr_type) + ']'
        print(content)
        for c in self.children:
            c.print(indent + 2)

    def annotate(self, parent=None):
        # types and var table
        self.types = parent.types if parent else builtin_types()
        self.vars = parent.vars if parent else SymbolTable()

        # expr
        if not parent:
            self.expr = False
        elif parent.expr:
            self.expr = True
        elif parent.type in ['EXPR', 'ASSN']:
            self.expr = True
        else:
            self.expr = False

        for c in self.children:
            c.annotate(self)

        # expr type
        if self.type == 'TYPE':
            self.expr_type = ExprType(self.types[self.children[0].value],
                    len(self.children))
        elif not self.expr:
            # ignore type of non-expressions
            pass
        elif self.type == 'ID':
            self.id = self.vars[self.value]
            self.expr_type = self.id.type
        elif self.type == 'NUM':
            self.expr_type = ExprType(self.types['int'], 0)
        elif self.type == 'BIN':
            # TODO: implicit conversion
            if self.children[0].expr_type.type != \
                    self.children[1].expr_type.type:
                raise TypeError()

            self.expr_type = ExprType(self.children[0].expr_type.type, 0)

        if self.type == 'LET':
            self.vars.add(self.children[1].value, self.children[0].expr_type)


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


class ExprType:
    def __init__(self, tp, lvl):
        self.type = tp
        self.level = lvl

    def __str__(self):
        s = self.type.name
        if self.level > 0:
            s += ' ' + '&' * self.level
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


class DeclType:
    def __init__(self, name, size):
        self.name = name
        self.size = size


def builtin_types():
    types = {
            DeclType('int', 4)
            }
    return {tp.name: tp for tp in types}
