#ifndef FIN_PRIMITIVES_H
#define FIN_PRIMITIVES_H

#include "offset.h"
#include "traits.h"
#include "typedefs.h"
#include <algorithm>
#include <cstdint>
#include <iostream>

namespace Fin
{
// primitive types
using Int = std::int32_t;
using Float = float;
using Bool = bool;

class Ptr
{
public:
    constexpr Ptr() noexcept {}

    Ptr &operator+=(Offset off) noexcept
    {
        _offset += off;
        return *this;
    }

    Ptr &operator-=(Offset off) noexcept
    {
        _offset -= off;
        return *this;
    }

private:
    std::uint32_t _block = 0;
    Offset _offset;

    constexpr Ptr(std::uint32_t block, Offset off) : _block{block}, _offset{off}
    {
    }

    friend class Allocator;
    friend class Stack;

    friend constexpr Ptr operator+(Ptr self, Offset off) noexcept;
    friend constexpr Ptr operator-(Ptr self, Offset off) noexcept;

    template <typename CharT, class Traits>
    friend std::basic_ostream<CharT, Traits> &
    operator<<(std::basic_ostream<CharT, Traits> &out, const Ptr &ptr);
};

template <>
struct IsPrimitive<Int> : std::true_type
{
};

template <>
struct IsPrimitive<Float> : std::true_type
{
};

template <>
struct IsPrimitive<Bool> : std::true_type
{
};

template <>
struct IsPrimitive<Ptr> : std::true_type
{
};

inline constexpr Ptr operator+(Ptr self, Offset off) noexcept
{
    return Ptr{self._block, self._offset + off};
}

inline constexpr Ptr operator-(Ptr self, Offset off) noexcept
{
    return Ptr{self._block, self._offset - off};
}

template <typename CharT, class Traits>
std::basic_ostream<CharT, Traits> &
operator<<(std::basic_ostream<CharT, Traits> &out, const Ptr &ptr)
{
    return out << ptr._block << ':' << ptr._offset;
}

constexpr Alignment MaxAlignment{
        std::max({alignof(Int), alignof(Float), alignof(Bool), alignof(Ptr)})};
} // namespace Fin

#endif
