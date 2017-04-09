#ifndef __METHOD_H__
#define __METHOD_H__

#include <string>

struct Method
{
    std::string name;
    uint32_t location;
    uint32_t argSize;
    uint32_t localSize;

    Method(const std::string &name, uint32_t loc, uint16_t as, uint16_t ls):
        name{name}, location{loc}, argSize{as}, localSize{ls} {}
};

#endif
