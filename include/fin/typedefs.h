#ifndef FIN_TYPEDEFS_H
#define FIN_TYPEDEFS_H

#include <cstddef>
#include <cstdint>

namespace Fin
{
// index of an item in a consecutively-indexed table
using Index = std::uint16_t;

// program counter location
using Pc = std::size_t;

// alignment requirement
using Alignment = std::size_t;
} // namespace Fin

#endif
