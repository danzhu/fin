#!/usr/bin/env python3

import data
from data import Location, SymbolTable, Type

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

    def analyze(self, tps, fns):
        # TODO: global
        ids = SymbolTable(Location.Frame)
        self._annotate(tps, fns, ids)

    def _expect_type(self, tp):
        if self.expr_type.cls == tp.cls:
            return
        raise TypeError('expected {}, but got {}'.format(tp, self.expr_type))

    def _annotate(self, tps, fns, ids):
        # expr
        if self.type == 'CALL':
            for c in self.children[1:]:
                c.expr = True
        elif self.expr or self.type in ['EXPR', 'ASSN', 'ARGS']:
            for c in self.children:
                c.expr = True
        elif self.type in ['IF', 'WHILE']:
            self.children[0].expr = True

        # process children
        for c in self.children:
            c._annotate(tps, fns, ids)

        # expr type
        if self.type == 'TYPE':
            tp = tps[self.children[0].value]
            lvl = len(self.children)
            self.expr_type = Type(tp, lvl)

        elif not self.expr:
            # ignore type of non-expressions
            pass

        elif self.type == 'ID':
            self.id = ids[self.value]
            self.expr_type = self.id.type

        elif self.type == 'NUM':
            self.expr_type = Type(data.INT)

        elif self.type == 'BIN':
            # TODO: implicit conversion
            self.children[0]._expect_type(self.children[1].expr_type)

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'COMP':
            # TODO: comparable type check
            self.children[0]._expect_type(self.children[1].expr_type)
            self.expr_type = Type(data.BOOL)

        elif self.type == 'CALL':
            self.fn = fns[self.children[0].value]
            self.expr_type = self.fn.ret

            for i in range(len(self.fn.args)):
                self.children[i + 1]._expect_type(self.fn.args[i])

        # local variable symbol creation
        if self.type == 'LET':
            ids.add(self.children[0].value, self.children[1].expr_type)

        # type checks
        if self.type in ['IF', 'WHILE']:
            self.children[0]._expect_type(Type(data.BOOL))
