from . import types
from . import symbols


def load_builtins() -> symbols.Module:
    mod = symbols.Module('', None, None)

    NUM_TYPES = {INT, FLOAT}

    # classes
    for struct in {BOOL_SYM, INT_SYM, FLOAT_SYM}:
        mod.add_struct(struct)

    # constants
    for const in {TRUE, FALSE}:
        mod.add_constant(const)

    # builtin operations
    for tp in NUM_TYPES:
        # binary
        for op in ['plus', 'minus', 'multiplies', 'divides', 'modulus']:
            fn = symbols.Function(op)
            fn.add_param('left', tp)
            fn.add_param('right', tp)
            fn.ret = tp
            mod.add_function(fn)

        # unary
        for op in ['pos', 'neg']:
            fn = symbols.Function(op)
            fn.add_param('value', tp)
            fn.ret = tp
            mod.add_function(fn)

        # comparison
        for op in ['equal', 'notEqual', 'less', 'lessEqual', 'greater',
                   'greaterEqual']:
            fn = symbols.Function(op)
            fn.add_param('left', tp)
            fn.add_param('right', tp)
            fn.ret = BOOL
            mod.add_function(fn)

    for val in NUM_TYPES:
        for res in NUM_TYPES:
            if val == res:
                continue

            fn = symbols.Function('cast')
            fn.add_param('value', val)
            fn.ret = res
            mod.add_function(fn)

    # array subscript
    fn = symbols.Function('subscript')
    t = fn.add_generic('T').type
    fn.add_param('arr', types.Reference(types.Array(t), 1))
    fn.add_param('index', INT)
    fn.ret = types.Reference(t, 1)
    mod.add_function(fn)

    # alloc
    fn = symbols.Function('alloc')
    t = fn.add_generic('T').type
    fn.ret = types.Reference(t, 1)
    mod.add_function(fn)

    fn = symbols.Function('alloc')
    t = fn.add_generic('T').type
    fn.add_param('length', INT)
    fn.ret = types.Reference(types.Array(t), 1)
    mod.add_function(fn)

    # dealloc
    fn = symbols.Function('dealloc')
    t = fn.add_generic('T').type
    fn.add_param('reference', types.Reference(t, 1))
    fn.ret = VOID
    mod.add_function(fn)

    # realloc
    fn = symbols.Function('realloc')
    t = fn.add_generic('T').type
    fn.add_param('array', types.Reference(types.Array(t), 1))
    fn.add_param('length', INT)
    fn.ret = VOID
    mod.add_function(fn)

    return mod


# structs
BOOL_SYM = symbols.Struct('Bool', 1)
INT_SYM = symbols.Struct('Int', 4)
FLOAT_SYM = symbols.Struct('Float', 4)

# types
BOOL = types.StructType(BOOL_SYM)
INT = types.StructType(INT_SYM)
FLOAT = types.StructType(FLOAT_SYM)
UNKNOWN = types.Special('?')
DIVERGE = types.Special('Diverge')
VOID = types.Special('Void')

# constants
TRUE = symbols.Constant('TRUE', BOOL, True)
FALSE = symbols.Constant('FALSE', BOOL, False)
