#ifndef __METHOD_H__
#define __METHOD_H__

#include <cstdint>
#include <vector>

namespace Fin
{
    class Runtime;
    class Stack;
    struct Module;

    typedef void (NativeMethod)(Runtime &rt, Stack &st);

    struct Method
    {
        Module *module = nullptr;
        NativeMethod *nativeMethod = nullptr;
        uint32_t location;
        uint16_t argSize;

        Method() {}
        Method(NativeMethod *method): nativeMethod{method} {}
        Method(Module *module, uint32_t loc, uint16_t argSize):
            module{module}, location{loc}, argSize{argSize} {}
    };
}

#endif
