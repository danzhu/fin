#include "frame.h"

#include <cassert>
#include "contract.h"
#include "function.h"
#include "library.h"

std::ostream &Fin::operator<<(std::ostream &out, const Fin::Frame &fr)
{
    out << "  in ";
    if (!fr.contract)
    {
        // TODO: show full id (version in future)
        out << '<' << fr.library->id.name << '>';
    }
    else
    {
        // TODO: show info on types in contract
        out << fr.contract->name;
    }

    return out;
}
