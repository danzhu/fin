# Fin Instruction Set

## `error`

**Opcode**: 0x0

**Format**: `error`

Crash the runtime environment.

## `cookie`

**Opcode**: 0x23

**Format**: `cookie`

With opcode equal to `#`, this instruction will skip until past EOL, and is
used for shebang at the start of the program. This also allows comments
embedded in the binary.

## `module`

**Opcode**: 0x1

**Format**: `module name:s methodSize:H`

Declare new module, and set declaring module to this module.

## `method`

**Opcode**: 0x2

**Format**: `method index:H argSize:H skip:I`

Implement method at `index` of declaring module.

## `ref_module`

**Opcode**: 0x3

**Format**: `ref_module name:s`

Set referencing module.

## `ref_method`

**Opcode**: 0x4

**Format**: `ref_method index:H`

Add method at `index` of referencing module to list of references of
declaring module.

## `call`

**Opcode**: 0x5

**Format**: `call index:H`

Call method at `index` of references in executing module.

## `return`

**Opcode**: 0x6

**Format**: `return`

Return from the current method.

## `term`

**Opcode**: 0x7

**Format**: `term`

Stop program execution. Automatically added to the end of every module.

## `br`

**Opcode**: 0x8

**Format**: `br offset:h`

Unconditionally branch to `pc + offset`, where pc is at the end of the
instruction.

## `br_false`

**Opcode**: 0x9

**Format**: `br_false offset:h`

Pop boolean from stack and branch if false.

## `br_true`

**Opcode**: 0xa

**Format**: `br_true offset:h`

Pop boolean from stack and branch if true.

## `push`

**Opcode**: 0xb

**Format**: `push amount:H`

Push `amount` bytes onto stack.

## `pop`

**Opcode**: 0xc

**Format**: `pop amount:H`

Pop `amount` bytes from stack.

## `const_i`

**Opcode**: 0xd

**Format**: `const_i value:i`

Load constant `value` onto stack.

## `load_i`

**Opcode**: 0xe

**Format**: `load_i offset:h`

Load value on frame at `offset` onto stack.

## `store_i`

**Opcode**: 0xf

**Format**: `store_i offset:h`

Store value to frame at `offset` from stack.

## `return_i`

**Opcode**: 0x10

**Format**: `return_i`

Return from method with a return value.

## `add_i`

**Opcode**: 0x11

**Format**: `add_i`

Pop two values from stack and push the sum.

## `sub_i`

**Opcode**: 0x12

**Format**: `sub_i`

Pop two values from stack and push the difference.

## `mult_i`

**Opcode**: 0x13

**Format**: `mult_i`

Pop two values from stack and push the product.

## `div_i`

**Opcode**: 0x14

**Format**: `div_i`

Pop two values from stack and push the quotient.

## `mod_i`

**Opcode**: 0x15

**Format**: `mod_i`

Pop two values from stack and push the modulo.

## `eq_i`

**Opcode**: 0x16

**Format**: `eq_i`

Pop two values from stack and push the boolean representing if they are
equal.

## `ne_i`

**Opcode**: 0x17

**Format**: `ne_i`

Pop two values from stack and push the boolean representing if they are
not equal.

## `lt_i`

**Opcode**: 0x18

**Format**: `lt_i`

Pop two values from stack and push the boolean representing if less than.

## `le_i`

**Opcode**: 0x19

**Format**: `le_i`

Pop two values from stack and push the boolean representing if less than or
equal to.

## `gt_i`

**Opcode**: 0x1a

**Format**: `gt_i`

Pop two values from stack and push the boolean representing if greater than.

## `ge_i`

**Opcode**: 0x1b

**Format**: `ge_i`

Pop two values from stack and push the boolean representing if greater than
or equal to.
