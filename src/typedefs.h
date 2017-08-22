#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include "offset.h"
#include <algorithm>
#include <cstdint>
#include <iostream>

namespace Fin
{
// index of an item in a consecutively-indexed table
using Index = std::uint16_t;

// program counter location
using Pc = std::size_t;

// primitive types
using Int = std::int32_t;
using Float = float;
using Bool = bool;

class Ptr
{
public:
    constexpr Ptr() {}

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

constexpr std::size_t MaxAlignment =
        std::max({alignof(Int), alignof(Float), alignof(Bool), alignof(Ptr)});
}

#endif
