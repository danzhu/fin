#!/usr/bin/env python3

import instr

FORMAT = """#include "opcode.h"

#include <iostream>

std::array<const char *, 256> Fin::Opnames
{{{{
{opnames}
}}}};

std::ostream &Fin::operator<<(std::ostream &out, Opcode op)
{{
    return out << Opnames.at(static_cast<uint8_t>(op));
}}"""


def main() -> None:
    opnames = [hex(i) for i in range(256)]
    for ins in instr.load():
        opnames[ins.opcode] = ins.opname

    names = ',\n'.join('   "{}"'.format(e) for e in opnames)
    print(FORMAT.format(opnames=names))


if __name__ == '__main__':
    main()
