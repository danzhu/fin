#include "fin/memory.h"

#include "fin/log.h"
#include "fin/offset.h"
#include "fin/typeinfo.h"
#include <cstring>

void Fin::Memory::move(Memory target, TypeInfo type) const noexcept
{
    LOG(2) << "\n  = 0x";
    for (auto p = &_data[type.size()._value - 1]; p != _data; --p)
    {
        LOG(2) << ' ' << HexMap[*p >> 4 & 0xF] << HexMap[*p & 0xF];
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
