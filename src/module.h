#ifndef __MODULE_H__
#define __MODULE_H__

#include <string>
#include <vector>
#include "array.h"

namespace Fin
{
    struct Method;

    struct ModuleID
    {
        std::string name;
        // TODO: version

        bool operator<(const ModuleID &other) const noexcept
        {
            return name < other.name;
        }
    };

    struct Module
    {
        uint32_t id;
        Array<Method> methods;
        std::vector<Method *> methodRefs;

        explicit Module(uint16_t methodSize):
            methods{methodSize} {}
    };
}

#endif
