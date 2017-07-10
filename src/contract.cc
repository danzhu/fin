#include "contract.h"

#include "library.h"
#include "log.h"

Fin::Contract::Contract(Function &fn):
    library{fn.library}, name{fn.name}, init{fn.init},
    location{fn.location}, native{fn.native}
{}

Fin::Contract::Contract(Type &tp):
    library{tp.library}, name{tp.name}, init{tp.location}
{}

void Fin::Contract::addContract(Contract ctr)
{
    contracts.emplace_back(std::move(ctr));
}

void Fin::Contract::addOffset(Offset off)
{
    LOG(2) << std::endl << "  + " << off << " [" << offsets.size() << "]";
    offsets.emplace_back(off);
}
