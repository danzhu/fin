# Fin Project Todo List

## Language
- [ ] namespace
- [ ] dynamic allocation
- [ ] exception handling

## Compiler

### Lexer
- [ ] line continuation

### Parser
- [x] unary operations
- [ ] `continue` / `break`
- [ ] expression statements
- [ ] `let ... =`

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
- [ ] generate global code after function defs

## Runtime
- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [x] globals
- [ ] remove module index
