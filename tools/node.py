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
        self.target_type = None

    def __str__(self):
        content = self.type
        if self.value:
            content += ' {}'.format(self.value)
        if self.expr_type:
            content += ' [{}]'.format(self.expr_type)
        if self.target_type:
            content += ' -> [{}]'.format(self.target_type)
        if self.level:
            content += ' {}'.format(self.level)
        return content

    def print(self, indent=0):
        print(' ' * indent + str(self))
        for c in self.children:
            c.print(indent + 2)

    def analyze(self, syms):
        mod = Module('')

        for c in self.children:
            if c.type == 'DEF':
                c._decl(syms, mod)

        self._annotate(syms)

    def _expect_type(self, tp):
        assert self.expr_type, '{} does not have an expr type'.format(self.type)
        assert tp

        if not tp.none():
            if self.expr_type.cls != tp.cls:
                raise TypeError('expecting {}, but got {}'.format(
                    tp,
                    self.expr_type))

            if self.expr_type.level < tp.level:
                raise TypeError('not enough levels')

        self.target_type = tp

    def _expect_types(self, *tps):
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
        assert self.type == 'DEF'

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

        # symbol table
        if self.type == 'DEF':
            syms = SymbolTable(Location.Param, syms, self.fn)
            self.symbol_table = syms
        elif self.type == 'BLOCK':
            syms = SymbolTable(Location.Local, syms)
            self.symbol_table = syms

        # local variable symbol creation
        if self.type in ['PARAM', 'LET']:
            name = self.children[0].value
            tp = self.children[1]._type(syms, True)
            self.sym = syms.add_variable(name, tp)

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
            self.children[0]._expect_type(Type(data.BOOL))
            self.children[1]._expect_type(Type(data.BOOL))

            self.expr_type = Type(data.BOOL)

        elif self.type == 'BIN':
            self.children[0]._expect_types(*data.NUM_TYPES)

            tp = Type(self.children[0].expr_type.cls)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(tp)

            self.expr_type = tp

        elif self.type == 'UNARY':
            self.children[0]._expect_types(*data.NUM_TYPES)

            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'COMP':
            self.children[0]._expect_types(*data.NUM_TYPES)

            tp = Type(self.children[0].expr_type.cls)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(tp)

            self.expr_type = Type(data.BOOL)

        elif self.type == 'ASSN':
            tp = Type(self.children[0].expr_type.cls, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = Type(self.children[0].expr_type.cls, self.level)
            self.children[1]._expect_type(tp)

            self.expr_type = Type(data.NONE)

        elif self.type == 'INC_ASSN':
            tp = Type(self.children[0].expr_type.cls, 1)
            self.children[0]._expect_type(tp)

            tp = Type(self.children[0].expr_type.cls)
            self.children[1]._expect_type(tp)

            self.expr_type = Type(data.NONE)

        elif self.type == 'CALL':
            self.fn = syms.get(self.children[0].value, 'FUNCTION')
            self.expr_type = self.fn.ret
            self.arg_size = sum(c.size() for c in self.fn.params)

            for i in range(len(self.fn.params)):
                self.children[i + 1]._expect_type(self.fn.params[i])

        elif self.type == 'DEF':
            self.children[3]._expect_type(self.fn.ret)

        elif self.type == 'BLOCK':
            self.expr_type = self.children[-1].expr_type

            for c in self.children[:-1]:
                c._expect_type(Type(data.NONE))

        elif self.type == 'IF':
            tps = [c.expr_type for c in self.children[1:]]
            self.expr_type = data.interpolate_types(tps)
            # update children as well
            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.expr_type = Type(data.NONE)
            self.children[1]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            self.expr_type = Type(data.NONE)
            self.children[0]._expect_type(syms.function.ret)

        elif self.type == 'EMPTY':
            self.expr_type = Type(data.NONE)

        # type checks
        if self.type in ['IF', 'WHILE']:
            self.children[0]._expect_type(Type(data.BOOL))

        elif self.type == 'LET':
            if self.children[2].type != 'EMPTY':
                if self.sym.type.level != self.level + 1:
                    raise TypeError('initialization level mismatch')
                self.children[2]._expect_type(self.sym.type.cls)
                self.children[2]._expect_level(self.level)
