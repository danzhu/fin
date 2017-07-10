#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include <algorithm>
#include <cstdint>

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
    typedef std::uint64_t Ptr;

    constexpr std::size_t MAX_ALIGN = std::max({
            alignof(Int),
            alignof(Float),
            alignof(Bool),
            alignof(Ptr)});
}

#endif
