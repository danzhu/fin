#!/usr/bin/env python3

import instr

FORMAT = """#include "opcode.h"

std::array<const char *, 256> Fin::Opnames
{{{{
{opnames}
}}}};

std::ostream &Fin::operator<<(std::ostream &out, Opcode op)
{{
    return out << Opnames.at(static_cast<uint8_t>(op));
}}"""

def main():
    opnames = [hex(i) for i in range(256)]
    for ins in instr.load():
        opnames[ins.opcode] = ins.opname

    print(FORMAT.format(opnames=',\n'.join('   "{}"'.format(e) for e in opnames)))

if __name__ == '__main__':
    main()
