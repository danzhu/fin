#ifndef FIN_EXCEPTION_H
#define FIN_EXCEPTION_H

#include <stdexcept>

namespace Fin
{
class RuntimeError : public std::runtime_error
{
    using std::runtime_error::runtime_error;

public:
    RuntimeError(const RuntimeError &other) = default;
    RuntimeError(RuntimeError &&other) = default;
    ~RuntimeError() noexcept;

    RuntimeError &operator=(const RuntimeError &other) = default;
    RuntimeError &operator=(RuntimeError &&other) = default;
};

class AllocationError : public std::bad_alloc
{
    using std::bad_alloc::bad_alloc;

public:
    AllocationError(const AllocationError &other) = default;
    AllocationError(AllocationError &&other) = default;
    ~AllocationError() noexcept;

    AllocationError &operator=(const AllocationError &other) = default;
    AllocationError &operator=(AllocationError &&other) = default;
};
}

#endif
