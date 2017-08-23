#ifndef FIN_LIBRARY_H
#define FIN_LIBRARY_H

#include "contract.h"
#include "function.h"
#include "type.h"
#include <memory>
#include <string>
#include <unordered_map>
#include <vector>

namespace Fin
{
class LibraryID
{
public:
    explicit LibraryID(std::string name) noexcept : _name{std::move(name)} {}

    bool operator<(const LibraryID &other) const noexcept
    {
        return _name < other._name;
    }

private:
    std::string _name;

    template <typename CharT, class Traits>
    friend std::basic_ostream<CharT, Traits> &
    operator<<(std::basic_ostream<CharT, Traits> &out, const LibraryID &id);
};

class Library
{
public:
    explicit Library(LibraryID id) noexcept : _id{std::move(id)} {}
    ~Library() noexcept = default;

    Library(const Library &other) = delete;
    Library(Library &&other) noexcept = default;

    Library &operator=(const Library &other) = delete;
    Library &operator=(Library &&other) noexcept = default;

    template <typename... Args>
    Function &addFunction(std::string name, Args &&... args) noexcept
    {
        Function fn{*this, name, std::forward<Args>(args)...};
        auto it = _functions.emplace(std::move(name), std::move(fn)).first;
        auto &res = it->second;
        _refFunctions.emplace_back(&res);
        return res;
    }

    template <typename... Args>
    Type &addType(std::string name, Args &&... args) noexcept
    {
        Type tp{*this, name, std::forward<Args>(args)...};
        auto it = _types.emplace(std::move(name), std::move(tp)).first;
        auto &res = it->second;
        addRefType(res);
        return res;
    }

    void addRefFunction(const Function &fn) noexcept
    {
        _refFunctions.emplace_back(&fn);
    }

    void addRefType(const Type &type) noexcept
    {
        _refTypes.emplace_back(&type);
    }

    void addRefMember(const Member &mem) noexcept
    {
        _refMembers.emplace_back(&mem);
    }

    const Function &function(const std::string &name) const
    {
        return _functions.at(name);
    }

    const Type &type(const std::string &name) const { return _types.at(name); }

    const Function &refFunction(std::uint32_t idx) const
    {
        return *_refFunctions.at(idx);
    }

    const Type &refType(std::uint32_t idx) const { return *_refTypes.at(idx); }

    const Member &refMember(std::uint32_t idx) const
    {
        return *_refMembers.at(idx);
    }

    LibraryID id() const noexcept { return _id; }

private:
    LibraryID _id;
    std::unordered_map<std::string, Function> _functions;
    std::unordered_map<std::string, Type> _types;
    std::vector<const Function *> _refFunctions;
    std::vector<const Type *> _refTypes;
    std::vector<const Member *> _refMembers;
};

template <typename CharT, class Traits>
std::basic_ostream<CharT, Traits> &
operator<<(std::basic_ostream<CharT, Traits> &out, const LibraryID &id)
{
    return out << id._name;
}
} // namespace Fin

#endif
