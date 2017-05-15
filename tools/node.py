#!/usr/bin/env python3

import data
from data import Location, SymbolTable, Type, Module, Function

class Node:
    def __init__(self, tp, children, val=None, lvl=0):
        self.type = tp
        self.children = children
        self.value = val
        # TODO: maybe this should be stored somewhere else?
        self.level = lvl

        self.expr_type = None

    def print(self, indent=0):
        content = ' ' * indent + self.type
        if self.value:
            content += ' {}'.format(self.value)
        if self.expr_type:
            content += ' [{}]'.format(self.expr_type)
        if self.level > 0:
            content += ' {}'.format(self.level)
        print(content)
        for c in self.children:
            c.print(indent + 2)

    def analyze(self, syms):
        mod = Module('')

        for c in self.children:
            if c.type == 'DEF':
                c._decl(syms, mod)

        self._annotate(syms)

    def _expect_type(self, *tps):
        if self.expr_type.cls in tps:
            return
        raise TypeError('expected {}, but got {}'.format(
            ' or '.join(tp),
            self.expr_type))

    def _decl(self, syms, mod):
        name = self.children[0].value
        params = [p.children[1]._type(syms) for p in self.children[1].children]
        ret = self.children[2]._type(syms)
        self.fn = Function(mod, name, params, ret)
        syms.add_function(self.fn)

    def _type(self, syms, var=False):
        if len(self.children) == 0:
            tp = 'None'
            lvl = 0
        else:
            tp = self.children[0].value
            lvl = len(self.children) - 1
        if var:
            lvl += 1
        return Type(syms.get(tp, 'CLASS'), lvl)

    def _annotate(self, syms):
        self.annotated = True

        # local variable symbol creation
        if self.type in ['PARAM', 'LET']:
            name = self.children[0].value
            self.sym = self.children[1]._type(syms, True)
            if self.type == 'PARAM':
                syms.add_param(name, self.sym)
            elif self.type == 'LET':
                syms.add_local(name, self.sym)

        # symbol table
        if self.type == 'DEF':
            syms = SymbolTable(Location.Frame, syms)

        # process children
        for c in self.children:
            c._annotate(syms)

        # expr type
        if self.type == 'VAR':
            self.sym = syms.get(self.value)
            self.expr_type = self.sym.type

        elif self.type == 'NUM':
            self.expr_type = Type(data.INT)

        elif self.type == 'FLOAT':
            self.expr_type = Type(data.FLOAT)

        elif self.type == 'TEST':
            self.children[0]._expect_type(data.BOOL)
            self.children[1]._expect_type(data.BOOL)

            self.expr_type = Type(data.BOOL)

        elif self.type == 'BIN':
            # TODO: custom operator overload
            self.children[0]._expect_type(data.INT, data.FLOAT)

            # TODO: implicit conversion
            if self.children[0].expr_type.cls != self.children[1].expr_type.cls:
                raise TypeError('unmatched type')

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'UNARY':
            self.children[0]._expect_type(data.INT, data.FLOAT)

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'COMP':
            # TODO: comparable type check
            self.children[0]._expect_type(data.INT, data.FLOAT)

            if self.children[0].expr_type.cls != self.children[1].expr_type.cls:
                raise TypeError('unmatched type')

            self.expr_type = Type(data.BOOL)

        elif self.type == 'CALL':
            self.fn = syms.get(self.children[0].value, 'FUNCTION')
            self.expr_type = self.fn.ret
            self.arg_size = sum(c.size() for c in self.fn.params)

            for i in range(len(self.fn.params)):
                self.children[i + 1]._expect_type(self.fn.params[i].cls)

        # type checks
        if self.type in ['IF', 'WHILE']:
            self.children[0]._expect_type(data.BOOL)
