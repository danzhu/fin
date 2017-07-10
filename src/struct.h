#ifndef FIN_STRUCT_H
#define FIN_STRUCT_H

#include <string>

namespace Fin
{
    struct Library;

    struct Struct
    {
        std::string name;
        Library *library;
        std::size_t location;
    };
}

#endif
