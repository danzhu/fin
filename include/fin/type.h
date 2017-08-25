#ifndef FIN_TYPE_H
#define FIN_TYPE_H

#include "typedefs.h"
#include <memory>
#include <string>
#include <vector>

namespace Fin
{
class Library;

class Member
{
public:
    Member(std::string name, Index index) noexcept
            : _name{std::move(name)}, _index{index}
    {
    }

    std::string name() const noexcept { return _name; }
    Index index() const noexcept { return _index; }

private:
    std::string _name;
    Index _index;
};

class Type
{
public:
    Type(Library &lib, std::string name, Index gens, Pc loc) noexcept
            : _library{&lib}, _name{std::move(name)}, _generics{gens},
              _location{loc}
    {
    }

    Member &addMember(std::string fieldName) noexcept;

    Library &library() const noexcept { return *_library; }
    std::string name() const noexcept { return _name; }
    Index generics() const noexcept { return _generics; }
    Pc location() const noexcept { return _location; }

private:
    Library *_library;
    std::string _name;
    std::vector<std::unique_ptr<Member>> _members;
    Index _generics;
    Pc _location;
};
} // namespace Fin

#endif
