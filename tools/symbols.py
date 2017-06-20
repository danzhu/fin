from enum import Enum
import math

class Location(Enum):
    Global = 0
    Struct = 1
    Param  = 2
    Local  = 3


class Symbol(Enum):
    Module   = 0
    Struct   = 1
    Generic  = 2
    Function = 3
    Variable = 4
    Constant = 5


class Variable:
    TYPE = Symbol.Variable

    def __init__(self, name, tp, loc, off=None):
        self.name = name
        self.type = tp
        self.location = loc
        self.offset = off

    def __str__(self):
        return '{} {}'.format(self.name, self.type, self.location)

    def var_type(self):
        if type(self.type) is not Reference:
            return Reference(self.type, 1)
        else:
            return Reference(self.type.type, self.type.level + 1)


class Constant:
    TYPE = Symbol.Constant

    def __init__(self, name, tp, val):
        self.name = name
        self.type = tp
        self.value = val

    def var_type(self):
        return self.type


class Generic:
    TYPE = Symbol.Generic

    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def size(self):
        assert False, 'should not use size on generic'

    def resolve(self, gens):
        return gens[self.name]


class SymbolTable:
    def __init__(self, parent=None):
        self.parent = parent

        self.symbols = {}

    def _check_exists(self, name):
        if name in self.symbols:
            raise LookupError("symbol '{}' exists as {}".format(
                name, self.symbols[name].TYPE.name))

    def _add_symbol(self, sym):
        self._check_exists(sym.name)
        self.symbols[sym.name] = sym

    def _check_type(self, sym, tps):
        if sym.TYPE not in tps:
            raise LookupError("expecting {}, but got {} '{}'".format(
                ' or '.join(t.name for t in tps),
                sym.TYPE.name,
                sym))

    def find(self, name):
        if name in self.symbols:
            return self.symbols[name]

        if self.parent:
            return self.parent.find(name)

        return None

    def get(self, name, *tps):
        sym = self.find(name)

        if sym is None:
            raise LookupError("cannot find {} '{}'".format(
                ' or '.join(t.name for t in tps),
                name))

        self._check_type(sym, tps)

        return sym

    def ancestor(self, sym):
        if self.parent is None:
            raise LookupError('cannot find ancestor of type {}'.format(
                sym.name))

        if self.parent.TYPE == sym:
            return self.parent
        else:
            return self.parent.ancestor(sym)

    def module(self):
        return self.ancestor(Symbol.Module)

    def overloads(self, name):
        if self.parent is not None:
            res = self.parent.overloads(name)
        else:
            res = set()

        if name in self.symbols:
            fns = self.symbols[name]

            self._check_type(fns, [Symbol.Function, Symbol.Struct])

            if fns.TYPE == Symbol.Function:
                res |= {Match(fn) for fn in fns.functions}
            else:
                res.add(Match(fns))

        return res


class Module(SymbolTable):
    LOCATION = Location.Global
    TYPE = Symbol.Module

    def __init__(self, name):
        super().__init__()

        # TODO: version
        self.name = name

    def __str__(self):
        return self.name

    def __lt__(self, other):
        return self.name < other.name

    def fullname(self):
        return self.name

    def fullpath(self):
        if self.parent is not None:
            assert self.parent.TYPE == Symbol.Module

            # FIXME: use correct module hierarchy for this to work
            # return self.parent.path('.') + self.fullname()
            return self.fullname()
        else:
            return self.fullname()

    def path(self, sep=':'):
        path = self.fullpath()
        if path != '':
            path += sep

        return path

    def add_module(self, mod):
        self._add_symbol(mod)
        mod.parent = self

    def add_struct(self, struct):
        self._add_symbol(struct)
        struct.parent = self

    def add_function(self, fn):
        if fn.name not in self.symbols:
            group = FunctionGroup(fn.name)
            self.symbols[fn.name] = group

        else:
            group = self.symbols[fn.name]

            if group.TYPE != Symbol.Function:
                raise LookupError("redefining {} '{}' as {}".format(
                    group.TYPE.name,
                    group,
                    Symbol.Function.name))

        group.add(fn)
        fn.parent = self

    def add_variable(self, name, tp):
        raise NotImplementedError()

    def add_constant(self, const):
        self._add_symbol(const)


class Struct(SymbolTable):
    LOCATION = Location.Struct
    TYPE = Symbol.Struct

    def __init__(self, name, size=0):
        super().__init__()

        self.name = name
        self.generics = []
        self.fields = []
        self.size = size

    def __str__(self):
        return self.name

    def fullname(self):
        return self.name

    def fullpath(self):
        return self.module().path() + self.fullname()

    def add_generic(self, name):
        gen = Generic(name)
        self.generics.append(gen)
        self._add_symbol(gen)
        return gen

    def add_variable(self, name, tp):
        var = Variable(name, tp, Location.Struct)
        self.fields.append(var)
        self._add_symbol(var)
        return var

    def match(self, args, ret):
        if len(self.fields) != len(args):
            return None, None

        gens = {}
        lvls = [accept_type(p.type, a, gens) for p, a in zip(self.fields, args)]

        if ret is not None:
            cons = Construct(self)
            lvls.append(accept_type(ret, cons, gens))
        else:
            lvls.append(math.nan)

        if None in lvls:
            return None, None

        return lvls, gens

    def resolve(self, gens):
        params = [p.type.resolve(gens) for p in self.fields]
        ret = Construct(self).resolve(gens)
        return params, ret


class Function(SymbolTable):
    LOCATION = Location.Param
    TYPE = Symbol.Function

    def __init__(self, name, ret):
        super().__init__()

        self.name = name
        self.ret = ret

        self.params = []
        self.generics = []

    def __str__(self):
        return '{}{}({}){}'.format(
                self.name,
                '{' + ', '.join(str(g) for g in self.generics) + '}'
                    if self.generics else '',
                ', '.join(str(p) for p in self.params),
                ' ' + str(self.ret) if self.ret != VOID else '')

    def fullname(self):
        # TODO: generic parameters
        return '{}({}){}'.format(
                self.name,
                ','.join(p.type.fullpath() for p in self.params),
                self.ret.fullpath() if self.ret != VOID else '')

    def fullpath(self):
        return self.module().path() + self.fullname()

    def add_variable(self, name, tp):
        assert type(name) is str

        var = Variable(name, tp, Location.Param, 0)

        self._add_symbol(var)
        self.params.append(var)

        for param in self.params:
            param.offset -= tp.size()

        return var

    def add_generic(self, name):
        assert type(name) is str

        gen = Generic(name)

        self._add_symbol(gen)
        self.generics.append(gen)

        return gen

    def match(self, args, ret):
        if len(self.params) != len(args):
            return None, None

        # None: type mismatch
        # 1: casting to none
        # 2: level reduction
        # 3: exact match
        # nan: unknown

        gens = {}
        lvls = [accept_type(p.type, a, gens) for p, a in zip(self.params, args)]

        if ret is not None:
            lvls.append(accept_type(ret, self.ret, gens))
        else:
            lvls.append(math.nan)

        if None in lvls:
            return None, None

        return lvls, gens

    def resolve(self, gens):
        params = [p.type.resolve(gens) for p in self.params]
        ret = self.ret.resolve(gens)
        return params, ret


class Block(SymbolTable):
    LOCATION = Location.Local

    def __init__(self, parent):
        super().__init__(parent)

        self.offset = 0

        if parent.LOCATION == Location.Local:
            self.parent_offset = parent.offset
        else:
            self.parent_offset = 0

    def add_variable(self, name, tp):
        offset = self.parent_offset + self.offset
        var = Variable(name, tp, Location.Local, offset)
        self.offset += tp.size()

        self._add_symbol(var)

        return var


class Match:
    def __init__(self, src):
        self.source = src

    def __lt__(self, other):
        assert len(self.levels) == len(other.levels)

        # generic has lower precedence
        if len(self.source.generics) == 0 \
                and len(other.source.generics) > 0:
            return False

        less = False
        for s, o in zip(self.levels, other.levels):
            if s > o:
                return False
            if s < o:
                less = True

        return less

    def __str__(self):
        return '{} {}{}'.format(self.source,
                self.levels,
                ''.join(', {} = {}'.format(k, g)
                    for k, g in self.gens.items()))

    def update(self, args, ret):
        self.levels, self.gens = self.source.match(args, ret)
        return self.levels is not None

    def resolve(self):
        # check that all generic params are resolved
        if len(self.gens) != len(self.source.generics):
            return False

        self.params, self.ret = self.source.resolve(self.gens)
        return True


class FunctionGroup:
    TYPE = Symbol.Function

    def __init__(self, name):
        self.name = name
        self.functions = set()

    def __str__(self):
        return self.name

    def add(self, fn):
        self.functions.add(fn)


class Reference:
    def __init__(self, tp, lvl):
        assert type(tp) is not Reference

        self.type = tp
        self.level = lvl

    def __format(self, tp):
        return '{}{}'.format('&' * self.level, tp)

    def __str__(self):
        return self.__format(self.type)

    def fullname(self):
        return self.__format(self.type.fullname())

    def fullpath(self):
        return self.__format(self.type.fullpath())

    def size(self):
        return 8 # size of pointer

    def resolve(self, gens):
        return Reference(self.type.resolve(gens), self.level)


class Array:
    def __init__(self, tp, size=None):
        self.type = tp
        self._size = size

    def __format(self, tp):
        if self._size is None:
            return '[{}]'.format(tp)
        else:
            return '[{}; {}]'.format(tp, self._size)

    def __str__(self):
        return self.__format(self.type)

    def fullname(self):
        return self.__format(self.type.fullname())

    def fullpath(self):
        return self.__format(self.type.fullpath())

    def size(self):
        if self._size is None:
            raise TypeError('array is unsized')

        return self.type.size() * self._size

    def resolve(self, gens):
        return Array(self.type.resolve(gens))


class Construct:
    def __init__(self, struct, fields=None, gens=None):
        self.struct = struct
        self.fields = fields
        self.generics = gens

        if self.fields is None:
            self.fields = struct.fields

        if self.generics is None:
            self.generics = struct.generics

        self._finalized = False

    def __str__(self):
        res = str(self.struct)
        if len(self.generics) > 0:
            res += '{' + ', '.join(str(g) for g in self.generics) + '}'

        return res

    def fullname(self):
        res = self.struct.fullname()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullname() for g in self.generics) + '}'

        return res

    def fullpath(self):
        res = self.struct.fullpath()
        if len(self.generics) > 0:
            res += '{' + ','.join(g.fullpath() for g in self.generics) + '}'

        return res

    def member(self, name):
        self.finalize()

        if name not in self.symbols:
            raise LookupError("field '{}' does not exist in struct '{}'".format(
                name, self.struct))

        return self.symbols[name]

    def size(self):
        self.finalize()

        # note: struct size is only for builtins
        return self.struct.size + sum(f.type.size() for f in self.fields)

    def resolve(self, gens):
        fields = []
        for f in self.fields:
            var = Variable(f.name, f.type.resolve(gens), Location.Struct)
            fields.append(var)

        gen_args = []
        for g in self.generics:
            if type(g) is Generic:
                g = g.resolve(gens)

            gen_args.append(g)

        return Construct(self.struct,
                fields,
                gen_args)

    def finalize(self):
        if self._finalized:
            return

        size = 0
        self.symbols = {}
        for f in self.fields:
            f.offset = size
            size += f.type.size()
            self.symbols[f.name] = f

        self._finalized = True


class Special:
    def __init__(self, name):
        self.name = name

    def __str__(self):
        return self.name

    def size(self):
        assert False, 'should not use size on special'

    def resolve(self, gens):
        return self


def load_builtins():
    mod = Module('')

    # classes
    for struct in { BOOL, INT, FLOAT }:
        mod.add_struct(struct)

    # constants
    for const in { TRUE, FALSE }:
        mod.add_constant(const)

    # builtin operations
    for tp in { INT, FLOAT }:
        tp = Construct(tp)

        # binary
        for op in ['plus', 'minus', 'multiplies', 'divides', 'modulus']:
            fn = Function(op, tp)
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

        # unary
        for op in ['pos', 'neg']:
            fn = Function(op, tp)
            fn.add_variable('value', tp)
            mod.add_function(fn)

        # comparison
        for op in ['equal', 'notEqual', 'less', 'lessEqual', 'greater',
                'greaterEqual']:
            fn = Function(op, BOOL)
            fn.add_variable('left', tp)
            fn.add_variable('right', tp)
            mod.add_function(fn)

    # array subscript
    fn = Function('subscript', None)
    t = fn.add_generic('T')
    fn.add_variable('arr', Reference(Array(t), 1))
    fn.add_variable('index', Construct(INT))
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    # alloc
    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.ret = Reference(t, 1)
    mod.add_function(fn)

    fn = Function('alloc', None)
    t = fn.add_generic('T')
    fn.add_variable('length', Construct(INT))
    fn.ret = Reference(Array(t), 1)
    mod.add_function(fn)

    # dealloc
    fn = Function('dealloc', VOID)
    t = fn.add_generic('T')
    fn.add_variable('reference', Reference(t, 1))
    mod.add_function(fn)

    # realloc
    fn = Function('realloc', VOID)
    t = fn.add_generic('T')
    fn.add_variable('array', Reference(Array(t), 1))
    fn.add_variable('length', Construct(INT))
    mod.add_function(fn)

    return mod

def to_type(val, syms):
    if val[0] == '&':
        sub = val.lstrip('&')

        tp = to_type(sub, syms)
        lvl = len(val) - len(sub)
        return Reference(tp, lvl)
    elif val[0] == '[':
        sub = val[1:-1]

        # TODO: sized arrays
        # maybe we should use the lexer for this
        tp = to_type(sub, syms)
        return Array(tp)
    else:
        return Construct(syms.get(val, Symbol.Struct))

def to_level(tp, lvl):
    if tp == UNKNOWN:
        return UNKNOWN

    if type(tp) is Reference:
        tp = tp.type

    if lvl > 0:
        tp = Reference(tp, lvl)

    return tp

def to_ref(tp):
    if type(tp) is not Reference:
        tp = Reference(tp, 0)

    return tp

def interpolate_types(tps, gens):
    assert len(tps) > 0

    res = DIVERGE
    unknown = False
    for other in tps:
        if other == UNKNOWN:
            unknown = True
            continue

        # diverge does not affect any type
        if res == DIVERGE:
            res = other
            continue
        elif other == DIVERGE:
            continue

        if type(res) is Reference:
            if type(other) is not Reference:
                other = Reference(other, 0)

            if not match_type(res.type, other.type, gens):
                return VOID

            lvl = min(res.level, other.level)
            res = to_level(res.type, lvl)
            continue

        if type(other) is Reference:
            other = other.type

        if not match_type(res, other, gens):
            return VOID

    if unknown:
        return UNKNOWN

    return res

def load_module(mod_name, glob):
    # TODO: a better way to locate
    filename = 'ref/{}.fd'.format(mod_name)
    mod = Module(mod_name)
    glob.add_module(mod)
    with open(filename) as f:
        for line in f:
            segs = line.split()
            tp = segs[0]

            if tp == 'def':
                if len(segs) % 2 == 0: # void
                    [tp, name, *params] = segs
                    ret = VOID
                else:
                    [tp, name, *params, ret] = segs
                    ret = to_type(ret, mod)

                fn = Function(name, ret)
                for i in range(len(params) // 2):
                    name = params[i * 2]
                    tp = to_type(params[i * 2 + 1], mod)
                    fn.add_variable(name, tp)
                mod.add_function(fn)

            else:
                raise ValueError('invalid declaration type')

    return mod

def resolve_overload(overloads, args, ret):
    res = set()

    for match in overloads:
        if not match.update(args, ret):
            continue

        res = {r for r in res if not r < match}

        for r in res:
            if match < r:
                break
        else:
            res.add(match)

    return res

def match_type(self, other, gens):
    if type(other) is Generic:
        if other.name not in gens:
            gens[other.name] = self
            return True

        other = gens[other.name]

    if type(self) is Generic:
        if self.name not in gens:
            gens[self.name] = other
            return True

        self = gens[self.name]

    if type(self) is not type(other):
        return False

    if type(self) is Reference:
        return self.level == other.level \
                and match_unsized(self.type, other.type, gens)

    if type(self) is Array:
        return self._size == other._size \
                and match_type(self.type, other.type, gens)

    if type(self) is Construct:
        if self.struct != other.struct:
            return False

        for f, o in zip(self.fields, other.fields):
            if not match_type(f.type, o.type, gens):
                return False

        return True

    assert False, 'unknown type'

def match_unsized(self, other, gens):
    if type(self) is Array and type(other) is Array:
        if not match_type(self.type, other.type, gens):
            return False

        return self._size is None or self._size == other._size

    return match_type(self, other, gens)

def accept_type(self, other, gens):
    if other == DIVERGE:
        return MATCH_PERFECT

    if self == UNKNOWN or other == UNKNOWN:
        return math.nan

    if self == VOID:
        if other == VOID:
            return MATCH_PERFECT
        else:
            return MATCH_TO_VOID

    if type(other) is Generic:
        if other.name not in gens:
            gens[other.name] = self
            return MATCH_PERFECT

        other = gens[other.name]

    if type(self) is Generic:
        if self.name not in gens:
            gens[self.name] = other
            return MATCH_PERFECT

        self = gens[self.name]

    if type(self) is Reference:
        if type(other) is not Reference or self.level > other.level:
            return None

        if not match_unsized(self.type, other.type, gens):
            return None

        return MATCH_PERFECT - 1.0 + self.level / other.level

    if type(other) is Reference:
        # auto reduction to level 0
        other = other.type
        reduction = 1.0
    else:
        reduction = 0.0

    if type(self) is not type(other):
        return None

    if type(self) is Array or type(self) is Construct:
        if not match_type(self, other, gens):
            return None

        return MATCH_PERFECT - reduction

    assert False, 'unknown type'

BOOL = Struct('Bool', 1)
INT = Struct('Int', 4)
FLOAT = Struct('Float', 4)
UNKNOWN = Special('?')
DIVERGE = Special('Diverge')
VOID = Special('Void')

TRUE = Constant('TRUE', BOOL, True)
FALSE = Constant('FALSE', BOOL, False)

MATCH_PERFECT = 3.0
MATCH_TO_VOID = 1.0
