#!/usr/bin/env python3

import symbols
from symbols import Symbol, Module, Function, Struct, Block, Reference, Array

class Node:
    def __init__(self, tp, children, val=None, lvl=None):
        # basic data
        self.type = tp
        self.children = children
        self.value = val
        # TODO: maybe this should be stored somewhere else?
        self.level = lvl

        self.parent = None
        for c in children:
            c.parent = self

        # semantic analysis
        self.function = None
        self.match = None
        self.expr_type = None
        self.target_type = None
        self.stack_start = None
        self.stack_end = None

        # code generation
        self.context = None

    def __str__(self):
        content = self.type

        if self.match:
            content += ' {}'.format(self.match)
        elif self.function:
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

        if self.stack_end:
            content += ' [[{} ]]'.format(format_list(self.stack_end))

        return content

    def print(self, indent=0):
        print('  ' * indent + str(self))
        for c in self.children:
            c.print(indent + 1)

    def analyze(self, mod_name, syms, refs):
        self._analyze_acquire(mod_name, syms, refs)
        self._analyze_expect(refs, None)

    def ancestor(self, tp):
        if self.parent is None:
            raise LookupError(tp)

        if self.parent.type == tp:
            return self.parent
        else:
            return self.parent.ancestor(tp)

    def decedents(self, tp):
        res = set()
        for c in self.children:
            if c.type == tp:
                res.add(c)

            res |= c.decedents(tp)

        return res

    def _error(self, msg, *args):
        msg = msg.format(*args)

        if self.type == 'CALL':
            msg += '\n  in {}({}) {}'.format(self.value,
                    ', '.join(str(a) for a in self.args),
                    self.target_type)

        msg += '\n  in node {}'.format(self)
        raise Exception(msg)

    def _expect_type(self, tp):
        assert tp is not None

        if self.expr_type is not None:
            gens = {}
            if symbols.accept_type(tp, self.expr_type, gens) is None:
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

    def _resolve_overload(self, refs, required=False):
        if self.match is not None:
            return

        self.args = [c.expr_type for c in self.children]

        self.matches = symbols.resolve_overload(
                self.matches,
                self.args,
                self.target_type)

        if len(self.matches) == 0:
            self._error('no viable function overload')

        if len(self.matches) > 1:
            if not required:
                return

            self._error('cannot resolve function overload between\n{}',
                    '\n'.join('  ' + str(fn) for fn in self.matches))

        match = next(iter(self.matches))

        self.expr_type, self.params = match.resolve()

        if self.expr_type is None:
            if not required:
                return

            self._error('cannot resolve generic parameters\n  {}', match)

        self.match = match
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

        elif self.type == 'CALL':
            self.expr_type = symbols.UNKNOWN
            self.target_type = symbols.UNKNOWN
            self.matches = syms.overloads(self.value)

            if len(self.matches) == 0:
                self._error('no function "{}" defined', self.value)

            self._resolve_overload(refs)

        elif self.type == 'MEMBER':
            tp = symbols.to_level(self.children[0].expr_type, 0)

            if type(tp) is not Struct:
                self._error('member access requires struct type')

            self.field = tp.get(self.value, Symbol.Variable)
            self.expr_type = self.field.var_type()

        elif self.type == 'BLOCK':
            self.expr_type = self.children[-1].expr_type

        elif self.type == 'IF':
            tps = [c.expr_type for c in self.children[1:]]
            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type == 'RETURN':
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
            self.expr_type = symbols.NONE

        elif self.type == 'WHILE':
            bks = self.children[1].decedents('BREAK')
            tps = {node.children[0].expr_type for node in bks}
            tps.add(self.children[2].expr_type) # else

            self.expr_type = symbols.interpolate_types(tps, {})

        elif self.type in ['ASSN', 'EMPTY']:
            self.expr_type = symbols.NONE

        elif self.type in ['BREAK', 'CONTINUE', 'REDO']:
            # TODO: diverging type
            self.expr_type = symbols.NONE

    def _analyze_expect(self, refs, stack):
        self.stack_start = stack
        self.stack_next = stack

        if self.type == 'TEST':
            for c in self.children:
                c._expect_type(symbols.BOOL)

        elif self.type == 'ASSN':
            tp = symbols.to_level(self.children[0].expr_type, self.level + 1)
            self.children[0]._expect_type(tp)

            tp = symbols.to_level(self.children[0].expr_type, self.level)
            self.children[1]._expect_type(tp)

        elif self.type == 'CALL':
            self._resolve_overload(refs, True)

            # record usage for ref generation
            refs.add(self.match.function)

            for c, p in zip(self.children, self.params):
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
            self.expr_type = self.target_type

            for c in self.children[:-1]:
                c._expect_type(symbols.NONE)
            self.children[-1]._expect_type(self.expr_type)

        elif self.type == 'IF':
            self.children[0]._expect_type(symbols.BOOL)

            self.expr_type = self.target_type

            self.children[1]._expect_type(self.expr_type)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'WHILE':
            self.expr_type = self.target_type

            self.children[0]._expect_type(symbols.BOOL)
            self.children[1]._expect_type(symbols.NONE)
            self.children[2]._expect_type(self.expr_type)

        elif self.type == 'RETURN':
            tp = self.ancestor('DEF').function.ret
            self.children[0]._expect_type(tp)

        elif self.type == 'BREAK':
            tp = self.ancestor('WHILE').target_type
            self.children[0]._expect_type(tp)

        elif self.type == 'LET':
            if self.children[1].type != 'EMPTY':
                if type(self.sym.type) is Reference:
                    lvl = self.sym.type.level
                else:
                    lvl = 0

                if lvl != self.level:
                    self._error('initialization level mismatch')

                self.children[1]._expect_type(self.sym.type)

            self.stack_next = (self.sym.type, stack)

        if self.target_type is not None \
                and self.target_type != symbols.NONE:
            self.stack_next = (self.target_type, stack)

        # recurse
        # FIXME: incremental assignment has different stack rules
        if self.type in ['IF', 'WHILE', 'TEST']:
            # these nodes don't leave data on the stack
            for c in self.children:
                c._analyze_expect(refs, stack)

            # the result stack after children is the same as final result stack
            self.stack_end = self.stack_next
        else:
            for c in self.children:
                c._analyze_expect(refs, stack)
                stack = c.stack_next

            self.stack_end = stack


def format_list(l):
    if l is None:
        return ''

    return '{} {}'.format(format_list(l[1]), l[0])
