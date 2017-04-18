#!/usr/bin/env python3

import instr

FORMAT = """#ifndef __OPCODE_H__
#define __OPCODE_H__

#include <array>

namespace Fin
{{
    enum class Opcode : char
    {{
{opcodes}
    }};

    std::array<const char *, 256> Opnames =
    {{
{opnames}
    }};
}}

#endif"""

def main():
    instrs = {ins.opcode: ins for ins in instr.load()}

    opcodes = []
    opnames = []
    for i in range(256):
        ins = instrs.get(i)
        if ins:
            opname = ''.join(s.title() for s in ins.opname.split('_'))
            opcodes.append('        {} = {},'.format(opname, hex(i)))
        opnames.append('        "{}",'.format(ins.opname if ins else hex(i)))

    print(FORMAT.format(
        opcodes='\n'.join(opcodes),
        opnames='\n'.join(opnames)))

if __name__ == '__main__':
    main()
