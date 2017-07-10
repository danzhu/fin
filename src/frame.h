#ifndef FIN_FRAME_H
#define FIN_FRAME_H

#include <cstdint>
#include <iostream>
#include "typedefs.h"

namespace Fin
{
    struct Contract;
    struct Library;

    struct Frame
    {
        Library *library = nullptr;
        Contract *contract = nullptr;
        Pc pc;
        Size local = 0;
        Size param = 0;
    };

    std::ostream &operator<<(std::ostream &out, const Frame &fr);
}

#endif
