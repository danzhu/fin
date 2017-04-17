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

    std::array<const char *, 256> OpcodeNames =
    {{
{names}
    }};
}}

#endif"""

def main():
    instrs = {ins.binary: ins for ins in instr.load()}

    opcodes = []
    names = []
    for i in range(256):
        ins = instrs.get(i)
        if ins is not None:
            opcodes.append('        {} = {},'.format(ins.opcode, hex(i)))
        names.append('        "{}",'.format(ins.opcode if ins else hex(i)))

    print(FORMAT.format(
        opcodes='\n'.join(opcodes),
        names='\n'.join(names),
        size=len(instrs)))

if __name__ == '__main__':
    main()
