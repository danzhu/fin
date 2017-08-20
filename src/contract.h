#ifndef FIN_CONTRACT_H
#define FIN_CONTRACT_H

#include <memory>
#include <vector>
#include "function.h"
#include "type.h"
#include "typeinfo.h"

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

        Contract(Function &fn);
        Contract(Type &tp);

        Contract(const Contract &other) = delete;
        Contract(Contract &&other) = default;

        Contract &operator=(const Contract &other) = delete;
        Contract &operator=(Contract &&other) = default;

        void addContract(Contract ctr);
        void addOffset(Offset off);
    };
}

#endif
