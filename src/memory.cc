#include "memory.h"

#include "log.h"
#include "offset.h"
#include "typeinfo.h"
#include <cstring>

void Fin::Memory::move(Memory target, TypeInfo type) const noexcept
{
    LOG(2) << "\n  = 0x";
    for (int i = type.size()._value - 1; i >= 0; --i)
    {
        LOG(2) << ' ' << HexMap[_data[i] >> 4 & 0xF] << HexMap[_data[i] & 0xF];
    }

    std::memmove(target._data, _data, type.size()._value);
}

Fin::Memory Fin::Memory::operator+(Offset off) const noexcept
{
    return Memory{_data + off._value};
}

Fin::Memory Fin::Memory::operator-(Offset off) const noexcept
{
    return Memory{_data - off._value};
}
