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

### Analyzer
- [ ] implicit conversion
- [ ] type checks
- [ ] include paths
- [ ] prevent calls to functions defined later
- [ ] indent scope
- [ ] function overloads

### Generator
- [ ] implement `while ... else`
- [ ] module version

## Runtime
- [ ] recycle unused ptrs
- [x] rename method to function
- [x] use `std::function` instead of native function ptr
- [ ] globals
