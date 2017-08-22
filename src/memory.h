#ifndef FIN_MEMORY_H
#define FIN_MEMORY_H

#include "log.h"
#include "offset.h"
#include "typeinfo.h"
#include <cstdint>
#include <cstring>
#include <iostream>

namespace Fin
{
constexpr std::array<char, 16> HexMap{{'0', '1', '2', '3', '4', '5', '6', '7',
                                       '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'}};

class Memory
{
public:
    constexpr Memory() {}

    void move(Memory target, TypeInfo type) const noexcept
    {
        LOG(2) << "\n  = 0x";
        for (int i = type.size()._value - 1; i >= 0; --i)
        {
            LOG(2) << ' ' << HexMap[_data[i] >> 4 & 0xF]
                   << HexMap[_data[i] & 0xF];
        }

        std::memmove(target._data, _data, type.size()._value);
    }

    template <typename T>
    constexpr T &as() const noexcept
    {
        return *reinterpret_cast<T *>(_data);
    }

private:
    std::uint8_t *_data{nullptr};

    constexpr explicit Memory(std::uint8_t *data) : _data{data} {}

    friend class Allocator;

    friend constexpr Memory operator+(Memory self, Offset off) noexcept;
    friend constexpr Memory operator-(Memory self, Offset off) noexcept;
};

inline constexpr Memory operator+(Memory self, Offset off) noexcept
{
    return Memory{self._data + off._value};
}

inline constexpr Memory operator-(Memory self, Offset off) noexcept
{
    return Memory{self._data - off._value};
}
}

#endif
