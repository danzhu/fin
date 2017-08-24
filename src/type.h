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
    ~Type() noexcept = default;

    Type(const Type &other) = delete;
    Type(Type &&other) noexcept = default;

    Type &operator=(const Type &other) = delete;
    Type &operator=(Type &&other) noexcept = default;

    Member &addMember(std::string fieldName) noexcept
    {
        auto ptr = std::make_unique<Member>(
                std::move(fieldName), static_cast<Index>(_members.size()));
        auto &mem = *ptr;
        _members.emplace_back(std::move(ptr));
        return mem;
    }

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
