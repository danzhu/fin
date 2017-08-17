#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include <algorithm>
#include <cstdint>
#include <iostream>

namespace Fin
{
    // largest consecutive memory size, and memory offset in offset table
    struct Offset
    {
        std::uint32_t value;

        Offset operator+=(Offset other) noexcept
        {
            value += other.value;
            return *this;
        }

        Offset operator-=(Offset other) noexcept
        {
            value -= other.value;
            return *this;
        }

        constexpr Offset align(std::size_t aln) const noexcept
        {
            return Offset{static_cast<std::uint32_t>(
                    (value & ~(aln - 1))
                    + (value % aln ? aln : 0))};
        }
    };

    inline Offset operator+(Offset self, Offset other) noexcept
    {
        return Offset{self.value + other.value};
    }

    inline Offset operator-(Offset self, Offset other) noexcept
    {
        return Offset{self.value - other.value};
    }

    inline Offset operator*(Offset self, std::uint32_t mult) noexcept
    {
        return Offset{self.value * mult};
    }

    inline bool operator<(Offset self, Offset other) noexcept
    {
        return self.value < other.value;
    }

    inline bool operator>(Offset self, Offset other) noexcept
    {
        return self.value > other.value;
    }

    template<typename CharT, class Traits>
    std::basic_ostream<CharT, Traits> &operator<<(
            std::basic_ostream<CharT, Traits> &out, Offset off)
    {
        return out << off.value;
    }

    // index of an item in a consecutively-indexed table
    typedef std::uint16_t Index;

    // program counter location
    typedef std::size_t Pc;

    // primitive types
    typedef std::int32_t Int;
    typedef float Float;
    typedef bool Bool;

    struct Ptr
    {
        std::uint32_t block;
        Offset offset;

        Ptr &operator+=(Offset off) noexcept
        {
            offset += off;
            return *this;
        }

        Ptr &operator-=(Offset off) noexcept
        {
            offset -= off;
            return *this;
        }
    };

    inline Ptr operator+(Ptr self, Offset off) noexcept
    {
        return Ptr{self.block, self.offset + off};
    }

    inline Ptr operator-(Ptr self, Offset off) noexcept
    {
        return Ptr{self.block, self.offset - off};
    }

    template<typename CharT, class Traits>
    std::basic_ostream<CharT, Traits> &operator<<(
            std::basic_ostream<CharT, Traits> &out, const Ptr &ptr)
    {
        return out << ptr.block << ':' << ptr.offset;
    }

    constexpr std::size_t MAX_ALIGN = std::max({
            alignof(Int),
            alignof(Float),
            alignof(Bool),
            alignof(Ptr)});
}

#endif
