# Fin Project Todo List

## Language
- [ ] tuple parameter
- [ ] static (stack) allocation
- [ ] invariant validation
- [ ] function call with blocks
- [ ] cast operator
- [ ] reference assignment
  - [x] ~~assign / rebind~~
  - [x] level-based assignment
  - [ ] tuple assignment
- [ ] namespace
- [ ] dynamic (heap) allocation
  - [ ] array allocation
  - [ ] class instance allocation
- [ ] exception / error handling
- [ ] owner
  - [ ] copy / move assignment
  - [ ] optional ownership
- [ ] module
  - [ ] module version

## Compiler

- [ ] line continuation
- [x] token variant
- [x] unary operations
- [x] expression statements
- [x] `let ... =`
- [ ] implicit conversion
- [x] type checks
- [ ] include paths
- [x] ~~prevent calls to functions defined later~~
- [x] indent scope
- [x] function overloads
  - [ ] operator overloads
  - [ ] level promotion
- [x] generate global code after function defs
- [ ] loop control
  - [ ] `continue` / `break`
  - [ ] `else`
  - [ ] `redo`
- [ ] levelled equality comparison
- [x] unify module / struct / function to symbol table
  - [x] remove context in symbol table
- [ ] struct
  - [x] declaration
  - [x] field access
  - [ ] initialization
  - [ ] member function
  - [ ] destructor
- [x] symbol full path
  - [ ] fix standard library hierarchy (import)
- [ ] `let` type inference
- [x] function group no override
- [x] partial order overload

## Runtime
- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [ ] globals
- [ ] remove module index
