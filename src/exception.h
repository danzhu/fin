#ifndef FIN_EXCEPTION_H
#define FIN_EXCEPTION_H

#include <stdexcept>

namespace Fin
{
class RuntimeError : public std::runtime_error
{
public:
    explicit RuntimeError(const std::string &msg) noexcept
            : std::runtime_error{msg}
    {
    }

    RuntimeError(const RuntimeError &other) = default;
    RuntimeError(RuntimeError &&other) = default;
    ~RuntimeError() noexcept;

    RuntimeError &operator=(const RuntimeError &other) = default;
    RuntimeError &operator=(RuntimeError &&other) = default;
};

class AllocationError : public std::bad_alloc
{
public:
    AllocationError() noexcept {}

    AllocationError(const AllocationError &other) = default;
    AllocationError(AllocationError &&other) = default;
    ~AllocationError() noexcept;

    AllocationError &operator=(const AllocationError &other) = default;
    AllocationError &operator=(AllocationError &&other) = default;
};
}

#endif
