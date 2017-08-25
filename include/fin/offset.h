#ifndef FIN_OFFSET_H
#define FIN_OFFSET_H

#include <cstdint>
#include <iostream>

namespace Fin
{
class Memory;

// largest consecutive memory size, and memory offset in offset table
class Offset
{
public:
    constexpr Offset() noexcept {}

    Offset operator+=(Offset other) noexcept
    {
        _value += other._value;
        return *this;
    }

    Offset operator-=(Offset other) noexcept
    {
        _value -= other._value;
        return *this;
    }

    constexpr Offset align(std::size_t aln) const noexcept
    {
        return Offset{static_cast<std::uint32_t>(
                (_value & ~(aln - 1)) + ((_value % aln) != 0u ? aln : 0))};
    }

private:
    std::uint32_t _value = 0;

    constexpr explicit Offset(std::uint32_t value) : _value{value} {}

    friend class Allocator;
    friend class Memory;
    friend class Stack;
    friend class TypeInfo;

    friend constexpr Offset operator+(Offset self, Offset other) noexcept;
    friend constexpr Offset operator-(Offset self, Offset other) noexcept;
    friend constexpr Offset operator*(Offset self, std::uint32_t mult) noexcept;
    friend constexpr bool operator<(Offset self, Offset other) noexcept;
    friend constexpr bool operator>(Offset self, Offset other) noexcept;
    friend constexpr bool operator<=(Offset self, Offset other) noexcept;
    friend constexpr bool operator>=(Offset self, Offset other) noexcept;

    template <typename CharT, class Traits>
    friend std::basic_ostream<CharT, Traits> &
    operator<<(std::basic_ostream<CharT, Traits> &out, Offset off);
};

inline constexpr Offset operator+(Offset self, Offset other) noexcept
{
    return Offset{self._value + other._value};
}

inline constexpr Offset operator-(Offset self, Offset other) noexcept
{
    return Offset{self._value - other._value};
}

inline constexpr Offset operator*(Offset self, std::uint32_t mult) noexcept
{
    return Offset{self._value * mult};
}

inline constexpr bool operator<(Offset self, Offset other) noexcept
{
    return self._value < other._value;
}

inline constexpr bool operator>(Offset self, Offset other) noexcept
{
    return self._value > other._value;
}

inline constexpr bool operator<=(Offset self, Offset other) noexcept
{
    return self._value <= other._value;
}

inline constexpr bool operator>=(Offset self, Offset other) noexcept
{
    return self._value >= other._value;
}

template <typename CharT, class Traits>
std::basic_ostream<CharT, Traits> &
operator<<(std::basic_ostream<CharT, Traits> &out, Offset off)
{
    return out << off._value;
}
} // namespace Fin

#endif
