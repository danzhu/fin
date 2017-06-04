#!/usr/bin/env python3

import symbols
from symbols import Symbol, Module, Function, Struct, Block, Reference, Array

class Node:
    def __init__(self, tp, children, val=None, lvl=None):
        self.type = tp
        self.children = children
        self.value = val
        # TODO: maybe this should be stored somewhere else?
        self.level = lvl

        self.function = None
        self.expr_type = None
        self.target_type = None

    def __str__(self):
        content = self.type

        if self.function:
            content += ' {}'.format(self.function)
        elif self.value:
            content += ' {}'.format(self.value)

        if self.expr_type:
            content += ' <{}'.format(self.expr_type)
            if self.target_type:
                content += ' -> {}'.format(self.target_type)
            content += '>'

        if self.level:
            content += ' {}'.format(self.level)

        return content

    def print(self, indent=0):
        print('  ' * indent + str(self))
        for c in self.children:
            c.print(indent + 1)

    def analyze(self, mod_name, syms, refs):
        self._analyze_acquire(mod_name, syms, refs)
        self._analyze_expect(refs)

    def _error(self, msg, *args):
        msg = msg.format(*args)
        msg += '\n  in node {}'.format(self)
        raise RuntimeError(msg)

    def _expect_type(self, tp):
        if self.expr_type is not None:
            gens = {}
            if tp.accept(self.expr_type, gens) is None:
                self._error('{} cannot be converted to {}', self.expr_type, tp)

        self.target_type = tp

    def _decl(self, mod):
        if self.type == 'DEF':
            name = self.value
            ret = self.children[1]._type(mod)
            if ret is None:
                ret = symbols.NONE

            self.function = Function(name, ret)

            for p in self.children[0].children:
                name = p.value
                tp = p.children[0]._type(mod)
                self.function.add_variable(name, tp)

            mod.add_function(self.function)

        elif self.type == 'STRUCT':
            name = self.value
            self.struct = Struct(name)

            for f in self.children:
                name = f.value
                tp = f.children[0]._type(mod)
                self.struct.add_variable(name, tp)

            mod.add_struct(self.struct)

        else:
            assert False, 'unknown declaration'

    def _type(self, syms):
        if self.type == 'EMPTY':
            return None

        if self.type == 'TYPE':
            return syms.get(self.value, Symbol.Struct)

        elif self.type == 'REF':
            tp = self.children[0]._type(syms)

            if self.level > 0:
                tp = Reference(tp, self.level)

            return tp

        elif self.type == 'ARRAY':
            tp = self.children[0]._type(syms)

            return Array(tp)

    def _resolve_overload(self, refs):
        if self.function is not None:
            return

        args = [c.expr_type for c in self.args]
        ret = self.target_type

        self.overloads = symbols.resolve_overload(self.overloads, args, ret)

        if len(self.overloads) == 0:
            fn = '{}({}) {}'.format(self.value,
                    ', '.join(str(a) for a in args),
                    ret)
            self._error('no viable function overload for:\n  ' + fn)

        if len(self.overloads) > 1:
            return

        overload = self.overloads.pop()
        self.function = overload.function
        self.expr_type = self.function.ret.resolve(overload.gens)
        self.params = [p.type.resolve(overload.gens) for p in
                self.function.params]
        self.arg_size = sum(p.size() for p in self.params)

    def _analyze_acquire(self, mod_name, syms, refs):
        # symbol table
        if self.type == 'FILE':
            self.module = Module(mod_name)
            syms.add_module(self.module)
            syms = self.module

            for c in self.children:
                if c.type in ['DEF', 'STRUCT']:
                    c._decl(syms)

        elif self.type == 'DEF':
            syms = self.function

        elif self.type == 'STRUCT':
            syms = self.struct

        elif self.type == 'BLOCK':
            syms = Block(syms)
            self.block = syms

        # process children
        for c in self.children:
            c._analyze_acquire(mod_name, syms, refs)

        # expr type
        if self.type == 'VAR':
            self.sym = syms.get(self.value, Symbol.Variable, Symbol.Constant)
            self.expr_type = self.sym.var_type()

        elif self.type == 'NUM':
            self.expr_type = symbols.INT

        elif self.type == 'FLOAT':
            self.expr_type = symbols.FLOAT

        elif self.type == 'TEST':
            self.expr_type = symbols.BOOL

        elif self.type == 'OP':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.overloads = syms.overloads(self.value)
            self.args = self.children

            self._resolve_overload(refs)

        elif self.type == 'CALL':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.overloads = syms.overloads(self.value)
            self.args = self.children[0].children

            if len(self.overloads) == 0:
                self._error('no function "{}" defined', self.value)

            self._resolve_overload(refs)

        elif self.type == 'METHOD':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.overloads = syms.overloads(self.value)
            self.args = [self.children[0]] + self.children[1].children

            if len(self.overloads) == 0:
                self._error('no method "{}" defined', self.value)

            self._resolve_overload(refs)

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 0)

            if type(tp) is not Struct:
                self._error('member access requires struct type')

            self.field = tp.get(self.value, Symbol.Variable)
            self.expr_type = self.field.var_type()

        elif self.type == 'BLOCK':
            self.expr_type = self.children[-1].expr_type

        elif self.type == 'ALLOC':
            self.element_type = self.children[0]._type(syms)
            self.expr_type = Reference(Array(self.element_type), 1)

        elif self.type == 'IF':
            tps = [c.expr_type for c in self.children[1:]]
            self.expr_type = symbols.interpolate_types(tps)

        elif self.type == 'RETURN':
            self.return_type = syms.ancestor(Symbol.Function).ret
            self.expr_type = symbols.NONE

        elif self.type == 'LET':
            name = self.value
            tp = self.children[0]._type(syms)
            if tp is None:
                tp = self.children[1].expr_type

                if tp is None:
                    self._error('type is required when no initialization')

                tp = symbols.to_level(tp, self.level)

            self.sym = syms.add_variable(name, tp)

        elif self.type in ['ASSN', 'DEALLOC', 'WHILE', 'EMPTY']:
            self.expr_type = symbols.NONE

    def _analyze_expect(self, refs):
        if self.type == 'TEST':
            self.children[0]._expect_type(symbols.BOOL)
            self.children[1]._expect_type(symbols.BOOL)

        elif self.type == 'ASSN':
            tp = symbols.to_level(self.children[0].expr_type, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = symbols.to_level(self.children[0].expr_type, self.level)
            self.children[1]._expect_type(tp)

        elif self.type in ['CALL', 'METHOD', 'OP']:
            self._resolve_overload(refs)

            if self.function is None:
                self._error('cannot resolve function overload between:\n{}',
                        '\n'.join('  ' + str(fn) for fn in self.overloads))

            # record usage for ref generation
            if self.type in ['CALL', 'METHOD']:
                refs.add(self.function)

            for c, p in zip(self.args, self.params):
                c._expect_type(p)

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 1)
            self.children[0]._expect_type(tp)

        elif self.type == 'FILE':
            for c in self.children:
                c._expect_type(symbols.NONE)

        elif self.type == 'DEF':
            self.children[2]._expect_type(self.function.ret)

        elif self.type == 'BLOCK':
            for c in self.children[:-1]:
                c._expect_type(symbols.NONE)

            self.expr_type = self.target_type

            self.children[-1]._expect_type(self.expr_type)

        elif self.type == 'ALLOC':
            self.children[1]._expect_type(symbols.INT)

        elif self.type == 'DEALLOC':
            tp = self.children[0].expr_type
            if type(tp) is not Reference:
                self._error('expecting reference type')
            self.children[0]._expect_type(Reference(tp.type, 1))

        elif self.type == 'IF':
            self.children[0]._expect_type(symbols.BOOL)

            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.children[0]._expect_type(symbols.BOOL)
            self.children[1]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            self.children[0]._expect_type(self.return_type)

        elif self.type == 'LET':
            if self.children[1].type != 'EMPTY':
                if type(self.sym.type) is Reference:
                    lvl = self.sym.type.level
                else:
                    lvl = 0

                if lvl != self.level:
                    self._error('initialization level mismatch')

                tp = symbols.to_level(self.sym.type, lvl)
                self.children[1]._expect_type(tp)

        # recurse
        for c in self.children:
            c._analyze_expect(refs)
