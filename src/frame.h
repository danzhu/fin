#ifndef FIN_FRAME_H
#define FIN_FRAME_H

#include "contract.h"
#include "library.h"
#include "offset.h"
#include "typedefs.h"
#include <cstdint>
#include <iostream>

namespace Fin
{
struct Frame
{
    Library *library{nullptr};
    Contract *contract{nullptr};
    Pc pc;
    Offset local;
    Offset param;
};

template <typename CharT, class Traits>
std::basic_ostream<CharT, Traits> &
operator<<(std::basic_ostream<CharT, Traits> &out, const Frame &fr)
{
    out << "  in ";
    if (fr.contract)
    {
        // TODO: show info on types in contract
        out << fr.contract->name;
    }
    else if (fr.library)
    {
        out << '<' << fr.library->id << '>';
    }
    else
    {
        out << "<<anonymous>>";
    }

    return out;
}
}

#endif
