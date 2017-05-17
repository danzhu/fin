#!/usr/bin/env python3

import data
from data import Location, SymbolTable, Type, Module, Function

class Node:
    def __init__(self, tp, children, val=None, lvl=None):
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
        if self.expr_type.cls not in tps:
            raise TypeError('expecting {}, but got {}'.format(
                ' or '.join(tp.name for tp in tps),
                self.expr_type))

    def _expect_level(self, lvl):
        if self.expr_type.level < lvl:
            raise TypeError('expecting level {}, but got level {}'.format(
                lvl,
                self.expr_type.level))

    def _decl(self, syms, mod):
        name = self.children[0].value
        params = [p.children[1]._type(syms) for p in self.children[1].children]
        ret = self.children[2]._type(syms)
        self.fn = Function(mod, name, params, ret)
        syms.add_function(self.fn)

    def _type(self, syms, var=False):
        if len(self.children) == 0:
            tp = data.NONE
            lvl = 0
        else:
            tp = syms.get(self.children[0].value, 'CLASS')
            lvl = self.level
        if var:
            lvl += 1
        return Type(tp, lvl)

    def _annotate(self, syms):
        self.annotated = True

        # local variable symbol creation
        if self.type in ['PARAM', 'LET']:
            name = self.children[0].value
            tp = self.children[1]._type(syms, True)
            if self.type == 'PARAM':
                self.sym = syms.add_param(name, tp)
            elif self.type == 'LET':
                self.sym = syms.add_local(name, tp)

        # symbol table
        if self.type == 'BLOCK':
            syms = SymbolTable(Location.Frame, syms)

        self.symbol_table = syms

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
            self.children[0]._expect_type(data.INT, data.FLOAT)
            self.children[1]._expect_type(self.children[0].expr_type.cls)

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'UNARY':
            self.children[0]._expect_type(data.INT, data.FLOAT)

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'COMP':
            self.children[0]._expect_type(data.INT, data.FLOAT)
            self.children[1]._expect_type(self.children[0].expr_type.cls)

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

        elif self.type == 'LET':
            if self.children[2].type != 'EMPTY':
                if self.sym.type.level != self.level + 1:
                    raise TypeError('initialization level mismatch')
                self.children[2]._expect_type(self.sym.type.cls)
                self.children[2]._expect_level(self.level)
