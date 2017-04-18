#ifndef __MODULE_H__
#define __MODULE_H__

#include <string>
#include <unordered_map>
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
        std::unordered_map<std::string, Method> methods;
        std::vector<Method *> refMethods;

        void addMethod(const std::string &name, Method &&method)
        {
            method.name = name;
            methods.emplace(name, std::move(method));
        }
    };
}

#endif
