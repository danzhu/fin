#ifndef FIN_FUNCTION_H
#define FIN_FUNCTION_H

#include <cstdint>
#include <functional>
#include <string>
#include <vector>

namespace Fin
{
    class Runtime;
    class Stack;
    struct Module;

    typedef std::function<void(Runtime &rt, Stack &st)> NativeFunction;

    struct Function
    {
        std::string name;
        Module *module = nullptr;
        NativeFunction native = nullptr;
        uint32_t location;

        Function() {}
        Function(NativeFunction fn): native{fn} {}
        Function(uint32_t loc): location{loc} {}
    };
}

#endif
