#!/usr/bin/env python3

import instr

FORMAT = """#ifndef __OPCODE_H__
#define __OPCODE_H__

namespace Fin
{{
    enum class Opcode : char
    {{
{opcodes}
    }};

    const char *OpcodeNames[] =
    {{
{names}
    }};
}}

#endif"""

def main():
    instrs = instr.load()
    opcodes = '\n'.join(['        {},'.format(ins.opcode) for ins in instrs])
    names = '\n'.join(['        "{}",'.format(ins.opcode) for ins in instrs])
    print(FORMAT.format(opcodes=opcodes, names=names))

if __name__ == '__main__':
    main()
