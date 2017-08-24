#include "type.h"

Fin::Member &Fin::Type::addMember(std::string fieldName) noexcept
{
    auto ptr = std::make_unique<Member>(std::move(fieldName),
                                        static_cast<Index>(_members.size()));
    auto &mem = *ptr;
    _members.emplace_back(std::move(ptr));
    return mem;
}
