#ifndef __OPCODE_H__
#define __OPCODE_H__

namespace Fin
{
    enum class Opcode : char
    {
        error,
        module,
        method,
        module_ref,
        method_ref,
        call,
        ret,
        term,
        br,
        br_false,
        br_true,
        push,
        pop,
        const_i,
        load_i,
        store_i,
        add_i,
        sub_i,
        mult_i,
        div_i,
        mod_i,
        eq_i,
        ne_i,
        lt_i,
        gt_i,
        le_i,
        ge_i,
    };

    const char *OpcodeNames[] =
    {
        "error",
        "module",
        "method",
        "module_ref",
        "method_ref",
        "call",
        "ret",
        "term",
        "br",
        "br_false",
        "br_true",
        "push",
        "pop",
        "const_i",
        "load_i",
        "store_i",
        "add_i",
        "sub_i",
        "mult_i",
        "div_i",
        "mod_i",
        "eq_i",
        "ne_i",
        "lt_i",
        "gt_i",
        "le_i",
        "ge_i",
    };
}

#endif
