#!/usr/bin/env python3

import sys

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

class Instr:
    def __init__(self, line):
        segs = line.split(' ')

        self.opcode = segs[0]
        self.params = [Param(param) for param in segs[1:]]


class Param:
    def __init__(self, val):
        segs = val.split(':')

        self.name = segs[0]
        self.type = segs[1]


def main():
    instrs = [Instr(line[:-1]) for line in sys.stdin]
    opcodes = '\n'.join(['        {},'.format(ins.opcode) for ins in instrs])
    names = '\n'.join(['        "{}",'.format(ins.opcode) for ins in instrs])
    print(FORMAT.format(opcodes=opcodes, names=names))

if __name__ == '__main__':
    main()
