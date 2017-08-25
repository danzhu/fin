#ifndef FIN_MEMORY_H
#define FIN_MEMORY_H

#include <array>
#include <cstdint>

namespace Fin
{
class Offset;
class TypeInfo;

constexpr std::array<char, 16> HexMap{{'0', '1', '2', '3', '4', '5', '6', '7',
                                       '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'}};

class Memory
{
public:
    constexpr Memory() noexcept {}

    void move(Memory target, TypeInfo type) const noexcept;

    template <typename T>
    constexpr T &as() const noexcept
    {
        return *reinterpret_cast<T *>(_data);
    }

    Memory operator+(Offset off) const noexcept;
    Memory operator-(Offset off) const noexcept;

private:
    std::uint8_t *_data{nullptr};

    constexpr explicit Memory(std::uint8_t *data) noexcept : _data{data} {}

    friend class Allocator;
};
} // namespace Fin

#endif
