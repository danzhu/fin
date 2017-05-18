# Fin Project Todo List

## Prototype
- [ ] tuple parameter
- [ ] static (stack) allocation
- [ ] invariant validation
- [ ] function call with blocks
- [ ] cast operator

## Language
- [ ] reference assignment
  - [x] ~~assign / rebind~~
  - [x] level-based assignment
  - [ ] tuple assignment
- [ ] namespace
- [ ] dynamic (heap) allocation
  - [ ] array allocation
  - [ ] class instance allocation
- [ ] exception / error handling
- [ ] owner assignment
  - [ ] copying / moving
- [ ] class

## Compiler

### Lexer
- [ ] line continuation
- [x] token variant

### Parser
- [x] unary operations
- [ ] `continue` / `break`
- [ ] expression statements
- [x] `let ... =`

### Analyzer
- [ ] implicit conversion
- [ ] type checks
- [ ] include paths
- [x] ~~prevent calls to functions defined later~~
- [x] indent scope
- [ ] function overloads

### Generator
- [ ] implement `while ... else`
- [ ] module version
- [x] generate global code after function defs

## Runtime
- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [x] globals
- [ ] remove module index
