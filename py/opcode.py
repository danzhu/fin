#!/usr/bin/env python3

import instr

FORMAT = """#ifndef FIN_OPCODE_H
#define FIN_OPCODE_H

#include <array>

namespace Fin
{{
    enum class Opcode : char
    {{
{opcodes}
    }};

    extern std::array<const char *, 256> Opnames;

    std::ostream &operator<<(std::ostream &out, Opcode op);
}} // namespace Fin

#endif"""


def main() -> None:
    opcodes = sorted((ins.opcode, ins.opname) for ins in instr.load())

    print(FORMAT.format(opcodes=',\n'.join(
        '        {} = {}'.format(
            ''.join(s.title() for s in e[1].split('_')),
            hex(e[0]))
        for e in opcodes)))


if __name__ == '__main__':
    main()
