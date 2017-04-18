# Introduction

A brief introduction to the Fin runtime and instruction set.

## Instruction Format

All instructions have 1-byte opcode, followed by a fixed or variable length of
bytes for its arguments. This reference use the following notation for the types
and format of the arguments:

`h`: 16-bit signed integer

`H`: 16-bit unsigned integer

`i`: 32-bit signed integer

`I`: 32-bit unsigned integer

`s`: string encoded as `length:H`, followed by `length` bytes

## Stack

Local variables are accessed by positive offsets from the frame, and parameters
are accessed by negative offsets. This offset is used in the `load_i` and
`store_i` instructions.

## Linking

Modules can be linked just by `cat`ing them together. To achieve this feature,
the instruction set was specially designed to allow declaration and execution in
the same instruction format. For example:

```asm
module 'example'

ref_module 'io'
ref_method 'write'

const_i 123
call 0
```

The first 3 instructions are declarative - that is, they indicate what the
module is, and which module and methods it requires to function. The last 2
instruction are executive - they indicate what the module does.

The module `example` is called the **declaring module**, which is the module
that all code and methods immediately after will belong to. The module `io` is a
**referencing module** of the declaring module, and is what the declaring module
will need to access. Finally, during the execution of the bottom 2 lines, the
**executing module** is also `example`. The executing module is the module that
the executing method belongs to, and is used to resolve method references - in
this case `call 0` calls method `write` of `io` because `example` references
that method at index 0.
