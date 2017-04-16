# Fin Instruction Set

A brief reference of the Fin instruction set.

## Introduction

### Instruction Format

All instructions have 1-byte opcode, followed by a fixed or variable length of
bytes for its arguments. This reference use the following notation for the types
and format of the arguments:

`i16`: 16-bit signed integer

`i32`: 32-bit signed integer

`u16`: 16-bit unsigned integer

`u32`: 32-bit unsigned integer

`s`: string encoded as `length:u16`, followed by `length` bytes


### Stack

Local variables are accessed by positive offsets from the frame, and parameters
are accessed by negative offsets. This offset is used in the `load_i` and
`store_i` instructions.


### Linking

Modules can be linked just by `cat`ing them together. To achieve this feature,
the instruction set was specially designed to allow declaration and execution in
the same instruction format. For example:

```asm
module 'example' 1h

module_ref 'io'
method_ref 1h

const_i 123
call 0h
```

The first 3 instructions are declarative - that is, they indicate what the
module is, and which module and methods it requires to function. The last 2
instruction are executive - they indicate what the module does.

The module `example` is called the **declaring module**, which is the module that
all code and methods immediately after will belong to. The module `io` is a
**referencing module** of the declaring module, and is what the declaring module
will need to access. Finally, during the execution of the bottom 2 lines, the
**executing module** is also `example`. The executing module is the module that
the executing method belongs to, and is used to resolve method references - in
this case `call 0h` calls method 1 of `io` because `example` references that
method.


## Declarative Instructions

### `module`

`module name:s methodSize:u16`

Declare new module, and set declaring module to this module.


### `method`

`method index:u16 argSize:u16 skip:u32`

Implement method at `index` of declaring module.


### `module_ref`

`module_ref name:s`

Set referencing module.


### `method_ref`

`method_ref index:u16`

Add method at `index` of referencing module to list of references of declaring
module.


## Executive Instructions

### `error`

`error`

Crash the runtime environment.


### `call`

`call index:u16`

Call method at `index` of references in executing module.


### `ret`

`ret`

Return from the current method.


### `term`

`term`

Stop program execution. Automatically added to the end of every module.


### `const_i`

`const_i value:i32`

Load constant `value` onto stack.


### `load_i`

`load_i offset:i16`

Load value on frame at `offset` onto stack.


### `store_i`

`store_i offset:i16`

Store value to frame at `offset` from stack.


### `add_i`

`add_i`

Pop two values from stack and push the sum.


### `sub_i`

`sub_i`

Pop two values from stack and push the difference.


### `mult_i`

`mult_i`

Pop two values from stack and push the product.


### `div_i`

`div_i`

Pop two values from stack and push the quotient.
