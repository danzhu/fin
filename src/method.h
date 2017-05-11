#ifndef __METHOD_H__
#define __METHOD_H__

#include <cstdint>
#include <string>
#include <vector>

namespace Fin
{
    class Runtime;
    class Stack;
    struct Module;

    typedef void (NativeMethod)(Runtime &rt, Stack &st);

    struct Method
    {
        std::string name;
        Module *module = nullptr;
        NativeMethod *nativeMethod = nullptr;
        uint32_t location;

        Method() {}
        Method(NativeMethod *method): nativeMethod{method} {}
        Method(uint32_t loc): location{loc} {}
    };
}

#endif
