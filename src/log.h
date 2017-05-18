#ifndef FIN_LOG_H
#define FIN_LOG_H

#ifndef DEBUG
#define DEBUG 0
#endif

#include <iostream>
#define LOG(lvl) DEBUG < lvl ? std::cerr : std::cerr

constexpr char HEXMAP[] {'0', '1', '2', '3', '4', '5', '6', '7', '8', '9',
    'A', 'B', 'C', 'D', 'E', 'F'};

inline void LOG_HEX(const int lvl, const char val[], uint32_t size)
{
    LOG(lvl) << "0x";
    for (int i = size - 1; i >= 0; --i)
    {
        LOG(lvl) << HEXMAP[val[i] >> 4 & 0xF] << HEXMAP[val[i] & 0xF];
    }
}

#endif
