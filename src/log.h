#ifndef FIN_LOG_H
#define FIN_LOG_H

#ifdef DEBUG
#include <iostream>
#define LOG(val) std::cerr << val

constexpr char HEXMAP[] {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F'};

inline void LOG_HEX(const char val[], uint32_t size)
{
    std::cerr << "0x";
    for (int i = size - 1; i >= 0; --i)
    {
        std::cerr << HEXMAP[val[i] >> 4 & 0xF] << HEXMAP[val[i] & 0xF];
    }
}
#else
#define LOG(val)
#define LOG_HEX(val, size)
#endif

#endif
