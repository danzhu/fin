#ifndef FIN_EXCEPTION_H
#define FIN_EXCEPTION_H

#include <stdexcept>

namespace Fin
{
    class RuntimeError : public std::runtime_error
    {
        using std::runtime_error::runtime_error;
    };

    class AllocationError : public std::bad_alloc
    {
        using std::bad_alloc::bad_alloc;
    };
}

#endif
