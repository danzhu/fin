#ifndef FIN_CONTRACT_H
#define FIN_CONTRACT_H

#include "function.h"
#include "log.h"
#include "type.h"
#include "typeinfo.h"
#include <memory>
#include <vector>

namespace Fin
{
struct Function;
struct Type;

struct Contract
{
    Library *library;
    std::string name;
    std::vector<TypeInfo> sizes;
    std::vector<Contract> contracts;
    std::vector<Offset> offsets;
    std::unique_ptr<Contract> refType;
    bool initialized{false};
    Pc init;
    Pc location;
    NativeFunction native;
    Offset argOffset;
    Offset localOffset;
    std::size_t localAlign{0};

    explicit Contract(Function &fn) noexcept
            : library{fn.library}, name{fn.name}, init{fn.init},
              location{fn.location}, native{fn.native}
    {
    }
    explicit Contract(Type &tp) noexcept
            : library{tp.library}, name{tp.name}, init{tp.location}
    {
    }

    Contract(const Contract &other) = delete;
    Contract(Contract &&other) = default;

    Contract &operator=(const Contract &other) = delete;
    Contract &operator=(Contract &&other) = default;

    void addContract(Contract ctr) noexcept
    {
        contracts.emplace_back(std::move(ctr));
    }

    void addOffset(Offset off) noexcept
    {
        LOG(2) << std::endl << "  + " << off << " [" << offsets.size() << "]";
        offsets.emplace_back(off);
    }
};
}

#endif
