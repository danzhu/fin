#ifndef FIN_TYPEINFO_H
#define FIN_TYPEINFO_H

#include "offset.h"
#include "primitives.h"
#include "type.h"

namespace Fin
{
class TypeInfo
{
public:
    constexpr TypeInfo(Offset size, std::size_t alignment)
            : _size{size}, _alignment{alignment}, _maxAligned{size.align(
                                                          MaxAlignment)}
    {
    }

    constexpr Offset size() const noexcept { return _size; }

    constexpr std::size_t alignment() const noexcept { return _alignment; }

    constexpr Offset alignedSize() const noexcept
    {
        return _size.align(_alignment);
    }

    constexpr Offset maxAlignedSize() const noexcept
    {
        // cached
        return _maxAligned;
    }

    template <typename T>
    constexpr static TypeInfo native()
    {
        return TypeInfo{Offset{sizeof(T)}, alignof(T)};
    }

    template <typename T>
    constexpr static Offset maxAlignedSize() noexcept
    {
        return Offset{sizeof(T)}.align(MaxAlignment);
    }

private:
    Offset _size;
    std::size_t _alignment;
    Offset _maxAligned;
};
} // namespace Fin

#endif
