#ifndef FIN_FUNCTION_H
#define FIN_FUNCTION_H

#include "typedefs.h"
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace Fin
{
class Contract;
class Library;
class Runtime;
class Stack;

using NativeSignature = void(Runtime &rt, Contract &ctr);
using NativeFunction = std::function<NativeSignature>;

class Function
{
public:
    Function(Library &lib, std::string name, NativeFunction fn, Index gens = 0,
             Index ctrs = 0) noexcept
            : _library{&lib}, _name{std::move(name)}, _generics{gens},
              _contracts{ctrs}, _native{std::move(fn)}
    {
    }

    Function(Library &lib, std::string name, Pc init, Pc loc, Index gens = 0,
             Index ctrs = 0) noexcept
            : _library{&lib}, _name{std::move(name)}, _generics{gens},
              _contracts{ctrs}, _init{init}, _location{loc}
    {
    }

    Library &library() const noexcept { return *_library; }
    std::string name() const noexcept { return _name; }
    Index generics() const noexcept { return _generics; }
    Index contracts() const noexcept { return _contracts; }
    NativeFunction native() const noexcept { return _native; }
    Pc init() const noexcept { return _init; }
    Pc location() const noexcept { return _location; }

private:
    Library *_library;
    std::string _name;
    Index _generics;
    Index _contracts;
    NativeFunction _native;
    Pc _init{0};
    Pc _location{0};
};
} // namespace Fin

#endif
