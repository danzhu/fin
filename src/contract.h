#ifndef FIN_CONTRACT_H
#define FIN_CONTRACT_H

#include "function.h"
#include "offset.h"
#include "type.h"
#include "typedefs.h"
#include "typeinfo.h"
#include "util.h"
#include <cstdint>
#include <memory>
#include <string>
#include <vector>

namespace Fin
{
class Library;
class Member;

class Contract
{
public:
    explicit Contract(const Function &fn) noexcept
            : _library{&fn.library()}, _name{fn.name()}, _init{fn.init()},
              _location{fn.location()}, _native{fn.native()}
    {
    }

    explicit Contract(const Type &tp) noexcept
            : _library{&tp.library()}, _name{tp.name()}, _init{tp.location()}
    {
    }

    Contract &callType(const Type &type);
    void addContract(const Function &fn) noexcept;
    void addArgOffset(const TypeInfo &info) noexcept;
    void addLocalOffset(const TypeInfo &info) noexcept;
    void addMemberOffset(const Member &mem);
    bool initialize(Pc &target) noexcept;
    void sign() noexcept;

    void addSize(TypeInfo info) noexcept { _sizes.emplace_back(info); }
    TypeInfo popSize() { return pop(_sizes); }
    TypeInfo size(std::uint32_t idx) const { return _sizes.at(idx); }
    Offset offset(std::uint32_t idx) const { return _offsets.at(idx); }
    Contract &contract(std::uint32_t idx) { return _contracts.at(idx); }

    Library &library() const noexcept { return *_library; }
    std::string name() const noexcept { return _name; }
    const NativeFunction &native() const noexcept { return _native; }
    Offset argOffset() const noexcept { return _argOffset; }
    Offset localOffset() const noexcept { return _localOffset; }
    Alignment localAlignment() const noexcept { return _localAlignment; }

private:
    Library *_library;
    std::string _name;
    std::vector<TypeInfo> _sizes;
    std::vector<Offset> _offsets;
    std::vector<Contract> _contracts;
    std::unique_ptr<Contract> _typeContract;
    bool _initialized{false};
    Pc _init{0};
    Pc _location{0};
    NativeFunction _native;
    Offset _argOffset;
    Offset _localOffset;
    Alignment _localAlignment{0};

    void addOffset(Offset off) noexcept;
};
} // namespace Fin

#endif
