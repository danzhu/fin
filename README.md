# The Fin Project

A programming language / assembly language / compiler / assembler / runtime,
designed to support high-level language features while still exposing low-level
operations for efficiency in both development and runtime.

In short, it's "just another programming language" :)

## Compilation

Requires CMake and Python 3. To build, do (the usual CMake stuff)

```sh
mkdir build && cd build
cmake ..
```

To compile and run the sample program `test.fin`, build the target `run`. On
Make-based configurations this is

```sh
make run
```

To enable debug logging in runtime, pass `-DDEBUG=[level]` to CMake when
configuring, where `[level]` is the level of details for the log messages.

## Inspiration

When designing the Fin language, the following languages gave a lot of
inspiration:

- Rust
- Python
- C++
- C#
- Ruby
