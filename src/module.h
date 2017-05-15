#ifndef FIN_MODULE_H
#define FIN_MODULE_H

#include <string>
#include <unordered_map>
#include <vector>
#include "array.h"
#include "function.h"

namespace Fin
{
    struct Function;

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
        std::unordered_map<std::string, Function> functions;
        std::vector<Function *> refFunctions;

        Function &addFunction(const std::string &name, Function &&fn)
        {
            fn.name = name;
            fn.module = this;
            return functions.emplace(name, std::move(fn)).first->second;
        }
    };
}

#endif
