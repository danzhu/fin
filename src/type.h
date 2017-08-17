#ifndef FIN_TYPE_H
#define FIN_TYPE_H

#include <memory>
#include <string>
#include <vector>
#include "member.h"
#include "typedefs.h"
#include "util.h"

namespace Fin
{
    struct Library;

    struct Type
    {
        Library *library;
        std::string name;
        Index generics;
        Pc location;
        std::vector<std::unique_ptr<Member>> members;

        Type(std::string name, Index gens, Pc loc):
            name{std::move(name)}, generics{gens}, location{loc} {}

        Type(const Type &other) = delete;
        Type(Type &&other) = default;

        Type &operator=(const Type &other) = delete;
        Type &operator=(Type &&other) = default;

        Member &addMember(std::string fieldName)
        {
            auto ptr = std::make_unique<Member>(std::move(fieldName),
                    static_cast<Index>(members.size()));
            auto &mem = *ptr;
            members.emplace_back(std::move(ptr));
            return mem;
        }
    };

    struct TypeInfo
    {
        Offset size;
        std::size_t alignment;
        Offset aligned;

        TypeInfo(Offset size, std::size_t alignment):
            size{size}, alignment{alignment},
            aligned{size.align(MAX_ALIGN)} {}

        template<typename T> static TypeInfo native()
        {
            return TypeInfo{Offset{sizeof(T)}, alignof(T)};
        }
    };
}

#endif
