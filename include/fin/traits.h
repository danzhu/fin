#ifndef FIN_TRAITS_H
#define FIN_TRAITS_H

#include <type_traits>

namespace Fin
{
template <typename T>
struct IsPrimitive : std::false_type
{
};
} // namespace Fin

#endif
