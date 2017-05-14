#ifndef FIN_FRAME_H
#define FIN_FRAME_H

#include <cstdint>

namespace Fin
{
    struct Module;

    struct Frame
    {
        Module &module;
        uint32_t returnAddress;
        uint32_t framePointer;
        uint16_t argSize;
    };
}

#endif
