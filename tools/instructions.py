#!/usr/bin/env python3

import instr

HEADER = """# Fin Instruction Set"""

FORMAT = """
## `{ins.opname}`

**Opcode**: 0x{ins.opcode:x}

**Format**: `{format}`

{ins.comment}"""

def main():
    instrs = instr.load()

    print(HEADER)

    for ins in instrs:
        print(FORMAT.format(
            ins=ins,
            format=ins.format()
            ), end='')

if __name__ == '__main__':
    main()
