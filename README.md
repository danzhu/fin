# The Fin Project

A programming language / assembly language / compiler / assembler / runtime,
designed to support high-level language features while still exposing low-level
operations for efficiency in both development and runtime.

In short, it's "just another programming language" :)

## Runtime

Requires CMake, a C++14 compiler, and Python 3.6. To build the runtime:

```sh
mkdir build && cd build
cmake ..
cmake --build .
```

To compile and run the test program `test.fin`, build the target `run`:

```sh
cmake --build . --target run
```

To enable debug logging in runtime, pass `-DDEBUG=[level]` to CMake when
configuring, where `[level]` is the level of details for the log messages.

## Compiler

Basic usage:

```sh
py/compiler.py [-o <output>] [-s <stage>] input
```

Where `<stage>` can be one of `lex`, `parse`, `ast`, `asm`, `exec`, which will
print the intermediate info to stdout (except `exec` which only writes to output
file).

Example:

```sh
py/compiler.py test.fin -o test.fm
```

## Inspiration

When designing the Fin language, the following languages gave a lot of
inspiration:

- Rust
- Python
- C++
- C#
- Ruby
