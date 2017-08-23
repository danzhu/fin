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
    ~RuntimeError() noexcept override;

    RuntimeError(const RuntimeError &other) noexcept = default;
    RuntimeError(RuntimeError &&other) noexcept = default;

    RuntimeError &operator=(const RuntimeError &other) noexcept = default;
    RuntimeError &operator=(RuntimeError &&other) noexcept = default;
};

class AllocationError : public std::bad_alloc
{
public:
    AllocationError() noexcept = default;
    ~AllocationError() noexcept override;

    AllocationError(const AllocationError &other) noexcept = default;
    AllocationError(AllocationError &&other) noexcept = default;

    AllocationError &operator=(const AllocationError &other) noexcept = default;
    AllocationError &operator=(AllocationError &&other) noexcept = default;
};
} // namespace Fin

#endif
