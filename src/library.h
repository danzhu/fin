#ifndef FIN_LIBRARY_H
#define FIN_LIBRARY_H

#include <memory>
#include <string>
#include <unordered_map>
#include <vector>
#include "array.h"
#include "contract.h"
#include "function.h"
#include "type.h"

namespace Fin
{
    struct LibraryID
    {
        std::string name;

        bool operator<(const LibraryID &other) const
        {
            return name < other.name;
        }
    };

    struct Library
    {
        LibraryID id;
        std::unordered_map<std::string, Function> functions;
        std::unordered_map<std::string, Type> types;
        std::vector<Function *> refFunctions;
        std::vector<Type *> refTypes;
        std::vector<Member *> refMembers;

        explicit Library(LibraryID id): id{id} {}

        Library(const Library &other) = delete;
        Library(Library &&other) = default;

        Library &operator=(const Library &other) = delete;
        Library &operator=(Library &&other) = default;

        Function &addFunction(Function fn)
        {
            fn.library = this;
            auto name = fn.name;
            auto it = functions.emplace(std::move(name), std::move(fn)).first;
            auto &res = it->second;
            refFunctions.emplace_back(&res);
            return res;
        }

        Type &addType(Type tp)
        {
            tp.library = this;
            auto name = tp.name;
            auto it = types.emplace(std::move(name), std::move(tp)).first;
            auto &res = it->second;
            refTypes.emplace_back(&res);
            return res;
        }
    };
}

#endif
