#ifndef FIN_FUNCTION_H
#define FIN_FUNCTION_H

#include "typedefs.h"
#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace Fin
{
class Runtime;
class Stack;
struct Contract;
struct Library;

using NativeFunction =
        std::function<void(Runtime &rt, Contract &ctr, Stack &st)>;

struct Function
{
    Library *library{nullptr};
    std::string name;
    Index generics;
    Index contracts;
    NativeFunction native;
    Pc init;
    Pc location;

    Function(std::string name, NativeFunction fn, Index gens = 0,
             Index ctrs = 0)
            : name{std::move(name)}, generics{gens}, contracts{ctrs},
              native{std::move(fn)}
    {
    }

    Function(std::string name, Pc init, Pc loc, Index gens = 0, Index ctrs = 0)
            : name{std::move(name)}, generics{gens}, contracts{ctrs},
              init{init}, location{loc}
    {
    }

    Function(const Function &other) = delete;
    Function(Function &&other) = default;

    Function &operator=(const Function &other) = delete;
    Function &operator=(Function &&other) = default;
};
}

#endif
