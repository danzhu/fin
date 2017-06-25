# Fin Project Todo List

## Roadmap

- [x] Runtime
- [ ] Python Compiler
- [ ] Libraries
  - [ ] Language Builtins
  - [ ] Runtime Library
  - [ ] Standard Library
- [ ] Compiler Rewrite
- [ ] Debugger

## Language

- [x] functions
  - [x] function overloading
  - [x] operator overloading
  - [x] cast operator
- [x] type inference
  - [x] functions
  - [x] control flow
- [x] structs
- [x] arrays
  - [x] sized arrays
  - [x] unsized arrays
- [x] enums
- [ ] tuples
- [x] assignment
  - [x] level-based assignment
  - [ ] deconstruct assignment
- [ ] error handling
- [ ] ownership
  - [ ] copy / move assignment
  - [ ] optional ownership
  - [ ] RAII
- [ ] library
  - [ ] library version
- [x] modules
  - [x] import
  - [ ] encapsulation
  - [ ] export
- [ ] generics
  - [x] struct / enum
  - [ ] function
- [ ] pattern matching
  - [ ] constant
  - [ ] deconstruction
- [ ] traits
- [ ] iterators
  - [ ] continuation-based iteration

## Compiler

- [ ] line continuation
- [x] token variant
- [x] unary operations
- [x] expression statements
- [x] `let ... =`
- implicit conversion
  - [x] level reduction
  - [ ] level promotion
  - [x] remove conversion to `None`
  - [x] diverging type
  - [x] sized to unsized array
- [x] type checks
- [ ] include paths
- [x] ~~prevent calls to functions defined later~~
- [x] indent scope
- [x] function overloads
  - [x] operator overloads
  - [x] fix inc assignment
- [x] generate global code after function defs
- loop control
  - [x] `continue` / `break`
  - [x] `else`
  - [x] `redo`
  - [x] `break ...`
  - [ ] disallow jumps inside condition and else
  - [ ] loop labels
- [ ] levelled equality comparison
- [x] unify module / struct / function to symbol table
  - [x] remove context in symbol table
- structs
  - [x] declaration
  - [x] field access
  - [x] inline construction
  - [ ] destructor
  - [ ] partial replacement construction
- member function
  - [x] member call syntax
  - [ ] member call scope limit
- [x] symbol full path
  - [x] fix standard library hierarchy (import)
- [x] `let` type inference
- [x] function group no override
- [x] partial order overload
- dynamic (heap) allocation
  - [x] array allocation
  - [x] struct (single instance) allocation
- [x] fix incremental assignment stack inaccuracy
- [ ] fix level ambiguity in generics
- [x] change postfix to prefix for reference
- [ ] show token of unsized type error
  - [ ] first bring back recursive definition check
- [ ] optimize `and` / `or` short-circuit
- [ ] restrict struct construction to call syntax
- [ ] make parentheses after enum optional

## Runtime

- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [ ] globals
- [ ] remove module index
- [ ] template for automatic C++ binding
