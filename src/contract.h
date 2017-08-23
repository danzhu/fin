#ifndef FIN_CONTRACT_H
#define FIN_CONTRACT_H

#include "exception.h"
#include "function.h"
#include "log.h"
#include "type.h"
#include "typeinfo.h"
#include <memory>
#include <vector>

namespace Fin
{
class Function;
class Type;

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
    ~Contract() noexcept = default;

    Contract(const Contract &other) = delete;
    Contract(Contract &&other) = default;

    Contract &operator=(const Contract &other) = delete;
    Contract &operator=(Contract &&other) = default;

    void addSize(TypeInfo info) noexcept { _sizes.emplace_back(info); }

    TypeInfo popSize() { return pop(_sizes); }

    Contract &callType(const Type &type)
    {
        _typeContract = std::make_unique<Contract>(type);
        _typeContract->_sizes = popRange(_sizes, type.generics());
        return *_typeContract;
    }

    void addOffset(Offset off) noexcept
    {
        LOG(2) << "\n  + " << off << " [" << _offsets.size() << "]";
        _offsets.emplace_back(off);
    }

    void addContract(const Function &fn) noexcept
    {
        Contract ctr{fn};
        ctr._sizes = popRange(_sizes, fn.generics());
        ctr._contracts = popRange(_contracts, fn.contracts());
        _contracts.emplace_back(std::move(ctr));
    }

    void addArgOffset(const TypeInfo &info)
    {
        addOffset(_argOffset);
        _argOffset += info.alignedSize();
    }

    void addLocalOffset(const TypeInfo &info)
    {
        auto offset = _localOffset.align(info.alignment());
        addOffset(offset);
        _localOffset = offset + info.size();
        _localAlignment = std::max(_localAlignment, info.alignment());
    }

    bool initialize(Pc &target) noexcept
    {
        if (_initialized)
        {
            target = _location;
            return false;
        }

        target = _init;
        return _initialized = true;
    }

    void sign() noexcept { _typeContract = nullptr; }

    Contract &contract(std::uint32_t idx) { return _contracts.at(idx); }

    Library &library() const noexcept { return *_library; }
    std::string name() const noexcept { return _name; }
    std::size_t sizes() const noexcept { return _sizes.size(); }
    std::size_t offsets() const noexcept { return _offsets.size(); }
    std::size_t contracts() const noexcept { return _contracts.size(); }
    const NativeFunction &native() const noexcept { return _native; }
    Offset argOffset() const noexcept { return _argOffset; }
    Offset localOffset() const noexcept { return _localOffset; }
    std::size_t localAlignment() const noexcept { return _localAlignment; }

    Contract &typeContract() const
    {
        if (!_typeContract)
            throw RuntimeError{"no type contract active"};

        return *_typeContract;
    }

    TypeInfo size(std::uint32_t idx) const { return _sizes.at(idx); }

    Offset offset(std::uint32_t idx) const { return _offsets.at(idx); }

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
    std::size_t _localAlignment{0};
};
} // namespace Fin

#endif
