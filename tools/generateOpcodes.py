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

    std::array<const char *, {size}> OpcodeNames =
    {{
{names}
    }};
}}

#endif"""

def main():
    instrs = instr.load()
    opcodes = '\n'.join(['        {},'.format(ins.opcode) for ins in instrs])
    names = '\n'.join(['        "{}",'.format(ins.opcode) for ins in instrs])
    print(FORMAT.format(opcodes=opcodes, names=names, size=len(instrs)))

if __name__ == '__main__':
    main()
