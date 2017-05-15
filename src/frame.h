#ifndef FIN_FRAME_H
#define FIN_FRAME_H

#include <cstdint>

namespace Fin
{
    struct Function;
    struct Module;

    struct Frame
    {
        const Module *module;
        const Function *function;
        uint32_t returnAddress;
        uint32_t framePointer;
        uint16_t argSize;
    };
}

#endif
