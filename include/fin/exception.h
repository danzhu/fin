#ifndef FIN_EXCEPTION_H
#define FIN_EXCEPTION_H

#include <new>
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

private:
    // avoid weak vtables
    virtual void dummy();
};

class AllocationError : public std::bad_alloc
{
private:
    // avoid weak vtables
    virtual void dummy();
};
} // namespace Fin

#endif
