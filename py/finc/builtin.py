from . import types
from . import symbols


def load_builtins() -> symbols.Module:
    mod = symbols.Module('', None, None)

    NUM_TYPES = [INT, FLOAT]

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
            fn.set_ret(tp)
            mod.add_function(fn)

        # unary
        for op in ['pos', 'neg']:
            fn = symbols.Function(op)
            fn.add_param('value', tp)
            fn.set_ret(tp)
            mod.add_function(fn)

        # comparison
        for op in ['equal', 'notEqual', 'less', 'lessEqual', 'greater',
                   'greaterEqual']:
            fn = symbols.Function(op)
            fn.add_param('left', tp)
            fn.add_param('right', tp)
            fn.set_ret(BOOL)
            mod.add_function(fn)

    for val in NUM_TYPES:
        for res in NUM_TYPES:
            if val is res:
                continue

            fn = symbols.Function('cast')
            fn.add_param('value', val)
            fn.set_ret(res)
            mod.add_function(fn)

    # array subscript
    fn = symbols.Function('subscript')
    t = fn.add_generic('T')
    fn.add_param('arr', types.Reference(types.Array(types.Generic(t))))
    fn.add_param('index', INT)
    fn.set_ret(types.Reference(types.Generic(t)))
    mod.add_function(fn)

    # alloc
    fn = symbols.Function('alloc')
    t = fn.add_generic('T')
    fn.set_ret(types.Reference(types.Generic(t)))
    mod.add_function(fn)

    fn = symbols.Function('alloc')
    t = fn.add_generic('T')
    fn.add_param('length', INT)
    fn.set_ret(types.Reference(types.Array(types.Generic(t))))
    mod.add_function(fn)

    # dealloc
    fn = symbols.Function('dealloc')
    t = fn.add_generic('T')
    fn.add_param('reference', types.Reference(types.Generic(t)))
    fn.set_ret(VOID)
    mod.add_function(fn)

    # realloc
    fn = symbols.Function('realloc')
    t = fn.add_generic('T')
    fn.add_param('array', types.Reference(types.Array(types.Generic(t))))
    fn.add_param('length', INT)
    fn.set_ret(types.Reference(types.Array(types.Generic(t))))
    mod.add_function(fn)

    return mod


# structs
BOOL_SYM = symbols.Struct('Bool')
INT_SYM = symbols.Struct('Int')
FLOAT_SYM = symbols.Struct('Float')

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
