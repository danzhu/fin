#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include <algorithm>
#include <cstdint>
#include <iostream>
#include "offset.h"

namespace Fin
{
    // index of an item in a consecutively-indexed table
    typedef std::uint16_t Index;

    // program counter location
    typedef std::size_t Pc;

    // primitive types
    typedef std::int32_t Int;
    typedef float Float;
    typedef bool Bool;

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

            constexpr explicit Ptr(std::uint32_t block, Offset off):
                _block{block}, _offset{off} {}

            friend class Allocator;
            friend class Stack;

            friend constexpr Ptr operator+(Ptr self, Offset off) noexcept;
            friend constexpr Ptr operator-(Ptr self, Offset off) noexcept;

            template<typename CharT, class Traits>
            friend std::basic_ostream<CharT, Traits> &operator<<(
                    std::basic_ostream<CharT, Traits> &out, const Ptr &ptr);
    };

    inline constexpr Ptr operator+(Ptr self, Offset off) noexcept
    {
        return Ptr{self._block, self._offset + off};
    }

    inline constexpr Ptr operator-(Ptr self, Offset off) noexcept
    {
        return Ptr{self._block, self._offset - off};
    }

    template<typename CharT, class Traits>
    std::basic_ostream<CharT, Traits> &operator<<(
            std::basic_ostream<CharT, Traits> &out, const Ptr &ptr)
    {
        return out << ptr._block << ':' << ptr._offset;
    }

    constexpr std::size_t MaxAlignment = std::max({
            alignof(Int),
            alignof(Float),
            alignof(Bool),
            alignof(Ptr)});
}

#endif
