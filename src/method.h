#ifndef __METHOD_H__
#define __METHOD_H__

#include <cstdint>
#include <vector>

struct Module;

struct Method
{
    Module *module = nullptr;
    uint32_t location;
    uint16_t argSize;

    Method() {}
    Method(Module *module, uint32_t loc, uint16_t argSize):
        module{module}, location{loc}, argSize{argSize} {}
};

#endif
