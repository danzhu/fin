#ifndef FIN_MEMORY_H
#define FIN_MEMORY_H

#include <cstdint>
#include <iostream>
#include "log.h"
#include "offset.h"
#include "typeinfo.h"

namespace Fin
{
    constexpr char HexMap[] {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
        'A', 'B', 'C', 'D', 'E', 'F'};

    class Memory
    {
        public:
            constexpr Memory() {}

            void move(Memory target, TypeInfo type) const noexcept
            {
                LOG(2) << std::endl << "  = 0x";
                for (int i = type.size()._value - 1; i >= 0; --i)
                {
                    LOG(2) << ' '
                        << HexMap[_data[i] >> 4 & 0xF]
                        << HexMap[_data[i] & 0xF];
                }

                for (std::uint32_t i = 0; i < type.size()._value; ++i)
                    target._data[i] = _data[i];
            }

            template<typename T>
            constexpr T &as() const noexcept
            {
                return *reinterpret_cast<T *>(_data);
            }

        private:
            std::uint8_t *_data{nullptr};

            constexpr explicit Memory(std::uint8_t *data): _data{data} {}

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
