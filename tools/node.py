#!/usr/bin/env python3

import data
from data import Symbol, Type, Module, Function, Class, Block

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
        if self.value:
            content += ' {}'.format(self.value)
        if self.function:
            content += ' {}'.format(self.function)
        if self.expr_type:
            content += ' [{}]'.format(self.expr_type)
        if self.target_type:
            content += ' -> [{}]'.format(self.target_type)
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
        raise RuntimeError(msg)

    def _expect_type(self, tp):
        if tp.match(self.expr_type) == 0:
            self._error('{} cannot be converted to {}', self.expr_type, tp)

        self.target_type = tp

    def _expect_types(self, *tps):
        if self.expr_type.cls not in tps:
            self._error('expecting {}, but got {}',
                ' or '.join(tp.name for tp in tps),
                self.expr_type)

    def _decl(self, mod):
        if self.type == 'DEF':
            name = self.children[0].value
            ret = self.children[2]._type(mod)
            self.function = Function(name, ret)
            for p in self.children[1].children:
                name = p.children[0].value
                tp = p.children[1]._type(mod)
                self.function.add_variable(name, tp)
            mod.add_function(self.function)

        elif self.type == 'STRUCT':
            name = self.children[0].value
            self.struct = Class(name)
            for f in self.children[1].children:
                name = f.children[0].value
                tp = f.children[1]._type(mod)
                self.struct.add_variable(name, tp)
            mod.add_class(self.struct)

        else:
            assert False, 'unknown declaration'

    def _type(self, syms):
        if len(self.children) == 0:
            tp = data.NONE
            lvl = 0
        else:
            tp = syms.get(self.children[0].value, Symbol.Class)
            lvl = self.level

        return Type(tp, lvl)

    def _resolve_overload(self, refs, required=False):
        if self.function is not None:
            return

        args = [c.expr_type for c in self.children[1:]]
        ret = self.target_type

        self.overloads = data.resolve_overload(self.overloads, args, ret)

        if len(self.overloads) == 0:
            fn = '{}({}) {}'.format(self.children[0].value,
                    ', '.join(str(a or '?') for a in args),
                    ret or '?')
            raise LookupError('no viable function overload for:\n  ' + fn)

        if len(self.overloads) == 1:
            self.function = self.overloads.pop().function
            self.expr_type = self.function.ret
            self.arg_size = sum(c.type.size() for c in self.function.params)

            # record usage for ref generation
            refs.add(self.function)

            for i in range(len(self.function.params)):
                self.children[i + 1]._expect_type(self.function.params[i].type)

            return

        if not required:
            return

        raise LookupError('cannot resolve function overload between:\n'
                + '\n'.join('  ' + str(fn) for fn in self.overloads))

    def _analyze_acquire(self, mod_name, syms, refs):
        self.annotated = True

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

        # local variable symbol creation
        if self.type == 'LET':
            name = self.children[0].value
            tp = self.children[1]._type(syms)
            self.sym = syms.add_variable(name, tp)

        # process children
        for c in self.children:
            c._analyze_acquire(mod_name, syms, refs)

        # expr type
        if self.type == 'VAR':
            self.sym = syms.get(self.value, Symbol.Variable)
            self.expr_type = self.sym.var_type()

        elif self.type == 'NUM':
            self.expr_type = Type(data.INT)

        elif self.type == 'FLOAT':
            self.expr_type = Type(data.FLOAT)

        elif self.type == 'TEST':
            self.expr_type = Type(data.BOOL)

        elif self.type == 'BIN':
            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'UNARY':
            self.expr_type = Type(self.children[0].expr_type.cls)

        elif self.type == 'COMP':
            self.expr_type = Type(data.BOOL)

        elif self.type == 'ASSN':
            self.expr_type = Type(data.NONE)

        elif self.type == 'INC_ASSN':
            self.expr_type = Type(data.NONE)

        elif self.type == 'CALL':
            name = self.children[0].value
            self.overloads = syms.overloads(name)

            if len(self.overloads) == 0:
                raise LookupError('no function "{}" defined'.format(name))

        elif self.type == 'MEMBER':
            cls = self.children[0].expr_type.cls
            self.field = cls.get(self.children[1].value, Symbol.Variable)
            self.expr_type = self.field.var_type()

        elif self.type == 'BLOCK':
            self.expr_type = self.children[-1].expr_type

        elif self.type == 'IF':
            tps = [c.expr_type for c in self.children[1:]]
            self.expr_type = data.interpolate_types(tps)

        elif self.type == 'WHILE':
            self.expr_type = Type(data.NONE)

        elif self.type == 'RETURN':
            self.return_type = syms.ancestor(Symbol.Function).ret
            self.expr_type = Type(data.NONE)

        elif self.type == 'EMPTY':
            self.expr_type = Type(data.NONE)

    def _analyze_expect(self, refs):
        if self.type == 'TEST':
            self.children[0]._expect_type(Type(data.BOOL))
            self.children[1]._expect_type(Type(data.BOOL))

        elif self.type == 'BIN':
            self.children[0]._expect_types(*data.NUM_TYPES)

            tp = Type(self.children[0].expr_type.cls)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(tp)

        elif self.type == 'UNARY':
            self.children[0]._expect_types(*data.NUM_TYPES)

        elif self.type == 'COMP':
            self.children[0]._expect_types(*data.NUM_TYPES)

            tp = Type(self.children[0].expr_type.cls)
            self.children[0]._expect_type(tp)
            self.children[1]._expect_type(tp)

        elif self.type == 'ASSN':
            tp = Type(self.children[0].expr_type.cls, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = Type(self.children[0].expr_type.cls, self.level)
            self.children[1]._expect_type(tp)

        elif self.type == 'INC_ASSN':
            tp = Type(self.children[0].expr_type.cls, 1)
            self.children[0]._expect_type(tp)

            tp = Type(self.children[0].expr_type.cls)
            self.children[1]._expect_type(tp)

        elif self.type == 'CALL':
            self._resolve_overload(refs)

        elif self.type == 'MEMBER':
            tp = Type(self.children[0].expr_type.cls, 1)
            self.children[0]._expect_type(tp)

        elif self.type == 'FILE':
            for c in self.children:
                c._expect_type(Type(data.NONE))

        elif self.type == 'DEF':
            self.children[3]._expect_type(self.function.ret)

        elif self.type == 'BLOCK':
            self.expr_type = self.target_type

            for c in self.children[:-1]:
                c._expect_type(Type(data.NONE))

            self.children[-1]._expect_type(self.expr_type)

        elif self.type == 'IF':
            self.children[0]._expect_type(Type(data.BOOL))
            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.children[0]._expect_type(Type(data.BOOL))
            self.children[1]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            self.children[0]._expect_type(self.return_type)

        elif self.type == 'LET':
            if self.children[2].type != 'EMPTY':
                if self.sym.type.level != self.level:
                    raise TypeError('initialization level mismatch')
                tp = Type(self.sym.type.cls, self.level)
                self.children[2]._expect_type(tp)

        # recurse
        for c in self.children:
            c._analyze_expect(refs)

        if self.type == 'CALL':
            self._resolve_overload(refs, True)
