#include "contract.h"

#include "exception.h"
#include "log.h"

Fin::Contract &Fin::Contract::callType(const Type &type)
{
    _typeContract = std::make_unique<Contract>(type);
    _typeContract->_sizes = popRange(_sizes, type.generics());
    return *_typeContract;
}

void Fin::Contract::addContract(const Function &fn) noexcept
{
    Contract ctr{fn};
    ctr._sizes = popRange(_sizes, fn.generics());
    ctr._contracts = popRange(_contracts, fn.contracts());
    _contracts.emplace_back(std::move(ctr));
}

void Fin::Contract::addArgOffset(const TypeInfo &info) noexcept
{
    addOffset(_argOffset);
    _argOffset += info.alignedSize();
}

void Fin::Contract::addLocalOffset(const TypeInfo &info) noexcept
{
    auto offset = _localOffset.align(info.alignment());
    addOffset(offset);
    _localOffset = offset + info.size();
    _localAlignment = std::max(_localAlignment, info.alignment());
}

void Fin::Contract::addMemberOffset(const Member &mem) noexcept
{
    if (!_typeContract)
        throw RuntimeError{"no type contract active"};

    auto offset = _typeContract->offset(mem.index());
    addOffset(offset);
}

bool Fin::Contract::initialize(Pc &target) noexcept
{
    if (_initialized)
    {
        target = _location;
        return false;
    }

    target = _init;
    return _initialized = true;
}

void Fin::Contract::sign() noexcept { _typeContract = nullptr; }

void Fin::Contract::addOffset(Offset off) noexcept
{
    LOG(2) << "\n  + " << off << " [" << _offsets.size() << "]";
    _offsets.emplace_back(off);
}
