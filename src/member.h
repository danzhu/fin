#ifndef FIN_MEMBER_H
#define FIN_MEMBER_H

#include "typedefs.h"
#include <string>

namespace Fin
{
struct Member
{
    std::string name;
    Index index;

    Member(std::string name, Index index) noexcept
            : name{std::move(name)}, index{index}
    {
    }
};
}

#endif
