# Fin Project Todo List

## Prototype

- [ ] tuple parameter
- [ ] static (stack) allocation
- [ ] invariant validation

## Language

- [ ] cast operator
- [ ] reference assignment
  - [x] ~~assign / rebind~~
  - [x] level-based assignment
  - [ ] tuple assignment
  - [ ] fix level ambiguity in generics
- [ ] exception / error handling
- [ ] owner
  - [ ] copy / move assignment
  - [ ] optional ownership
- [ ] library
  - [ ] library version
- [ ] modules
  - [ ] encapsulation (import / export)
- [ ] generics
  - [ ] struct
  - [ ] function
- [ ] iterators
  - [ ] continuation-based iteration

## Compiler

- [ ] line continuation
- [x] token variant
- [x] unary operations
- [x] expression statements
- [x] `let ... =`
- [ ] implicit conversion
  - [x] level reduction
  - [ ] level promotion
  - [ ] remove conversion to `None`
  - [ ] diverging type
- [x] type checks
- [ ] include paths
- [x] ~~prevent calls to functions defined later~~
- [x] indent scope
- [x] function overloads
  - [ ] operator overloads
- [x] generate global code after function defs
- [x] loop control
  - [x] `continue` / `break`
  - [ ] `else`
  - [x] `redo`
- [ ] levelled equality comparison
- [x] unify module / struct / function to symbol table
  - [x] remove context in symbol table
- [ ] struct
  - [x] declaration
  - [x] field access
  - [ ] inline initialization
  - [ ] destructor
- [ ] member function
  - [x] member call syntax
  - [ ] member call scope limit
- [x] symbol full path
  - [ ] fix standard library hierarchy (import)
- [x] `let` type inference
- [x] function group no override
- [x] partial order overload
- [x] dynamic (heap) allocation
  - [x] array allocation
  - [x] struct (single instance) allocation
- [ ] fix incremental assignment stack inaccuracy

## Runtime

- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [ ] globals
- [ ] remove module index
- [ ] template for automatic C++ binding
