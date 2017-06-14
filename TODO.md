# Fin Project Todo List

## Language

- [x] functions
  - [x] function overloading
  - [x] operator overloading
  - [ ] cast operator
- [x] type inference
  - [x] functions
  - [x] control flow
- [x] structs
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
- [ ] modules
  - [ ] encapsulation (import / export)
- [ ] generics
  - [ ] struct
  - [ ] function
- [ ] iterators
  - [ ] continuation-based iteration
- [ ] traits

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
- [ ] levelled equality comparison
- [x] unify module / struct / function to symbol table
  - [x] remove context in symbol table
- structs
  - [x] declaration
  - [x] field access
  - [ ] inline construction
  - [ ] destructor
  - [ ] partial replacement construction
- member function
  - [x] member call syntax
  - [ ] member call scope limit
- [x] symbol full path
  - [ ] fix standard library hierarchy (import)
- [x] `let` type inference
- [x] function group no override
- [x] partial order overload
- dynamic (heap) allocation
  - [x] array allocation
  - [x] struct (single instance) allocation
- [x] fix incremental assignment stack inaccuracy
- [ ] fix level ambiguity in generics

## Runtime

- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [ ] globals
- [ ] remove module index
- [ ] template for automatic C++ binding
