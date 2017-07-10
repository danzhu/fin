#ifndef FIN_MEMBER_H
#define FIN_MEMBER_H

#include <string>
#include "typedefs.h"

namespace Fin
{
    struct Member
    {
        std::string name;
        Index index;

        Member(std::string name, Index index): name{name}, index{index} {}
    };
}

#endif
