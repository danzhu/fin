#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include <algorithm>
#include <cstdint>
#include <iostream>

namespace Fin
{
    // size of types, largest consecutive memory size
    typedef std::uint32_t Size;

    // offset into memory
    typedef std::uint32_t Offset;

    // index of an item in a (relatively small) table
    typedef std::uint16_t Index;
    typedef std::uint16_t Count;

    // program counter location
    typedef std::size_t Pc;

    // primitive types
    typedef std::int32_t Int;
    typedef float Float;
    typedef bool Bool;

    struct Ptr
    {
        std::uint32_t block;
        std::uint32_t offset;

        Ptr operator+(std::int32_t off) const noexcept
        {
            return Ptr{block, offset + off};
        }

        Ptr operator-(std::int32_t off) const noexcept
        {
            return Ptr{block, offset - off};
        }

        Ptr &operator+=(std::int32_t off) noexcept
        {
            offset += off;
            return *this;
        }
    };

    constexpr std::size_t MAX_ALIGN = std::max({
            alignof(Int),
            alignof(Float),
            alignof(Bool),
            alignof(Ptr)});

    template<typename CharT, class Traits>
    std::basic_ostream<CharT, Traits> &operator<<(
            std::basic_ostream<CharT, Traits> &out, const Ptr &ptr)
    {
        return out << ptr.block << ':' << ptr.offset;
    }
}

#endif
