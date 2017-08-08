#include "runtime.h"

#include <cassert>
#include <cmath>
#include <functional>
#include <iostream>
#include "contract.h"
#include "function.h"
#include "library.h"
#include "opcode.h"
#include "type.h"
#include "util.h"

void move(const char *src, char *dest, Fin::Size size)
{
    LOG(2) << std::endl << "  = ";
    LOG_HEX(2, src, size);

    for (Fin::Size i = 0; i < size; ++i)
        dest[i] = src[i];
}

void Fin::Runtime::jump(Pc target)
{
    if (target > instrs.size())
        throw std::out_of_range{"jump target " + std::to_string(target)
            + " out of range " + std::to_string(instrs.size())};
    frame.pc = target;
}

std::string Fin::Runtime::readStr()
{
    auto len = readConst<std::uint16_t>();
    auto val = std::string{&instrs.at(frame.pc), len};

    LOG(1) << " '" << val << "'";

    jump(frame.pc + len);
    return val;
}

Fin::Function &Fin::Runtime::readFunction()
{
    auto idx = readConst<std::uint32_t>();
    auto &fn = *frame.library->refFunctions.at(idx);

    LOG(1) << " [" << fn.name << "]";

    return fn;
}

Fin::Contract &Fin::Runtime::readContract()
{
    auto idx = readConst<Index>();
    auto &ctr = frame.contract->contracts.at(idx);

    LOG(1) << " [" << ctr.name << "]";

    return ctr;
}

Fin::TypeInfo Fin::Runtime::readSize()
{
    auto idx = readConst<Index>();
    auto size = frame.contract->sizes.at(idx);

    LOG(1) << " [" << size.size << " | " << size.alignment << "]";

    return size;
}

Fin::Offset Fin::Runtime::readOffset()
{
    auto idx = readConst<Index>();
    auto offset = frame.contract->offsets.at(idx);

    LOG(1) << " [" << offset << "]";

    return offset;
}

void Fin::Runtime::ret()
{
    // TODO: looks a bit hacky
    opStack.resize(frame.param.offset);

    frame = pop(rtStack);
}

void Fin::Runtime::call(Contract &ctr)
{
    // store current frame
    rtStack.emplace_back(frame);

    // update frame
    frame.contract = &ctr;
    frame.local = frame.param = stackPtr + opStack.size();

    frame.library = ctr.library;

    if (ctr.native)
    {
        ctr.native(*this, ctr, opStack);

        // emplace and pop even for native functions so that we can get full
        // backtrace
        frame = pop(rtStack);
    }
    else
    {
        if (ctr.initialized)
        {
            jump(ctr.location);
            sign();
        }
        else
        {
            jump(ctr.init);
            ctr.initialized = true;
        }
    }
}

void Fin::Runtime::sign()
{
    frame.param = frame.local - frame.contract->argOffset;
    opStack.resize(opStack.size() + frame.contract->localOffset);

    // cleanup unneeded data
    frame.contract->refType = nullptr;
}

void Fin::Runtime::checkLibrary()
{
    if (!frame.library)
        throw std::runtime_error{"no library active"};
}

void Fin::Runtime::checkContract()
{
    if (!frame.contract)
        throw std::runtime_error{"no contract active"};
}

void Fin::Runtime::execute()
{
    Library *refLibrary = nullptr;
    Type *refType = nullptr;

    while (true)
    {
        LOG(2) << std::endl;
        LOG(1) << std::endl << '-';

        auto op = readConst<Opcode>();

        switch (op)
        {
            case Opcode::Error:
                throw std::runtime_error{"error instruction reached"};

            case Opcode::Cookie:
                // skip shebang
                while (instrs.at(frame.pc++) != '\n');
                continue;

            case Opcode::Lib:
                {
                    auto name = readStr();

                    auto &lib = createLibrary(name);
                    frame.library = &lib;
                }
                continue;

            case Opcode::Fn:
                {
                    checkLibrary();

                    auto name = readStr();
                    auto gens = readConst<std::uint16_t>();
                    auto ctrs = readConst<std::uint16_t>();
                    auto _loc = readConst<std::uint32_t>();
                    auto loc = frame.pc + _loc;
                    auto _end = readConst<std::uint32_t>();
                    auto end = frame.pc + _end;

                    frame.library->addFunction(
                            Function{name, frame.pc, loc, gens, ctrs});
                    jump(end);
                }
                continue;

            case Opcode::Type:
                {
                    auto name = readStr();
                    auto gens = readConst<std::uint16_t>();
                    auto _end = readConst<std::uint32_t>();
                    auto end = frame.pc + _end;

                    refType = &frame.library->addType(
                            Type{name, gens, frame.pc});
                    jump(end);
                }
                continue;

            case Opcode::Member:
                {
                    if (!refType)
                        throw std::runtime_error{"no referencing type"};

                    auto name = readStr();

                    auto &mem = refType->addMember(name);
                    frame.library->refMembers.emplace_back(&mem);
                }
                continue;

            case Opcode::RefLib:
                {
                    auto name = readStr();

                    refLibrary = &getLibrary(name);
                }
                continue;

            case Opcode::RefFn:
                {
                    checkLibrary();

                    if (!refLibrary)
                        throw std::runtime_error{"no referencing library"};

                    auto name = readStr();

                    auto it = refLibrary->functions.find(name);
                    if (it == refLibrary->functions.end())
                        throw std::runtime_error{"unable to find function '"
                            + name + "'"};

                    frame.library->refFunctions.emplace_back(&it->second);
                }
                continue;

            case Opcode::RefType:
                {
                    checkLibrary();

                    if (!refLibrary)
                        throw std::runtime_error{"no referencing library"};

                    auto name = readStr();

                    auto it = refLibrary->types.find(name);
                    if (it == refLibrary->types.end())
                        throw std::runtime_error{"unable to find type "
                            + name + "'"};

                    frame.library->refTypes.emplace_back(&it->second);
                }
                continue;

            case Opcode::SizeI:
                {
                    checkContract();

                    auto size = TypeInfo::native<Int>();
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::SizeF:
                {
                    checkContract();

                    auto size = TypeInfo::native<Float>();
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::SizeB:
                {
                    checkContract();

                    auto size = TypeInfo::native<Bool>();
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::SizeP:
                {
                    checkContract();

                    auto size = TypeInfo::native<Ptr>();
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::SizeDup:
                {
                    checkContract();

                    auto idx = readConst<std::uint16_t>();

                    auto size = frame.contract->sizes.at(idx);
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::SizeArr:
                {
                    checkContract();

                    auto len = readConst<Int>();

                    auto size = pop(frame.contract->sizes);

                    size.size = alignTo(size.size, size.alignment) * len;
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::TypeCall:
                {
                    checkLibrary();
                    checkContract();

                    // TODO: possibly move this to match readFunction()
                    auto idx = readConst<std::uint32_t>();

                    auto &type = *frame.library->refTypes.at(idx);

                    frame.contract->refType = std::make_unique<Contract>(type);
                    frame.contract->refType->sizes =
                        popRange(frame.contract->sizes, type.generics);
                    call(*frame.contract->refType);
                }
                continue;

            case Opcode::TypeRet:
                {
                    checkLibrary();
                    checkContract();

                    TypeInfo size{frame.contract->localOffset,
                        frame.contract->localAlign};
                    ret();
                    frame.contract->sizes.emplace_back(size);
                }
                continue;

            case Opcode::TypeMem:
                {
                    checkLibrary();
                    checkContract();

                    auto idx = readConst<std::uint32_t>();

                    auto mem = frame.library->refMembers.at(idx);
                    auto off = frame.contract->refType->offsets.at(mem->index);
                    frame.contract->addOffset(off);
                }
                continue;

            case Opcode::Param:
                {
                    checkContract();

                    auto size = readSize();

                    auto offset = frame.contract->argOffset;
                    frame.contract->addOffset(offset);
                    frame.contract->argOffset += size.aligned;
                }
                continue;

            case Opcode::Local:
                {
                    checkContract();

                    auto size = readSize();

                    auto offset = alignTo(frame.contract->localOffset,
                            size.alignment);
                    frame.contract->addOffset(offset);
                    frame.contract->localOffset = offset + size.size;
                }
                continue;

            case Opcode::Field:
                {
                    checkContract();

                    auto size = readSize();

                    auto offset = alignTo(frame.contract->localOffset,
                            size.alignment);
                    frame.contract->addOffset(offset);
                    frame.contract->localOffset = offset + size.size;
                    frame.contract->localAlign = std::max(
                            frame.contract->localAlign, size.alignment);
                }
                continue;

            case Opcode::Contract:
                {
                    checkLibrary();
                    checkContract();

                    auto &fn = readFunction();

                    Contract ctr{fn};
                    ctr.sizes = popRange(frame.contract->sizes, fn.generics);
                    ctr.contracts = popRange(frame.contract->contracts,
                            fn.contracts);

                    frame.contract->addContract(std::move(ctr));
                }
                continue;

            case Opcode::Sign:
                sign();
                continue;

            case Opcode::Call:
                {
                    checkLibrary();

                    auto &ctr = readContract();
                    call(ctr);
                }
                continue;

            case Opcode::Term:
                return;

            case Opcode::End:
                ret();
                continue;

            case Opcode::Ret:
                {
                    auto size = readSize();

                    auto src = opStack.topSize(size.aligned);

                    ret();

                    auto dest = opStack.pushSize(size.aligned);
                    move(src, dest, size.size);
                }
                continue;

            case Opcode::Push:
                {
                    auto size = readSize();

                    opStack.pushSize(size.aligned);
                }
                continue;

            case Opcode::Pop:
                {
                    auto size = readSize();

                    opStack.popSize(size.aligned);
                }
                continue;

            case Opcode::Dup:
                {
                    auto size = readSize();

                    auto src = opStack.topSize(size.aligned);
                    auto dest = opStack.pushSize(size.aligned);
                    move(src, dest, size.size);
                }
                continue;

            case Opcode::Load:
                {
                    auto size = readSize();

                    auto ptr = opStack.pop<Ptr>();
                    auto src = alloc.read(ptr, size.size);
                    auto dest = opStack.pushSize(size.aligned);
                    move(src, dest, size.size);
                }
                continue;

            case Opcode::Store:
                {
                    auto size = readSize();

                    auto src = opStack.popSize(size.aligned);
                    auto ptr = opStack.pop<Ptr>();
                    auto dest = alloc.write(ptr, size.size);
                    move(src, dest, size.size);
                }
                continue;

            case Opcode::AddrOff:
                {
                    auto size = readSize();

                    auto idx = opStack.pop<Int>();
                    auto addr = opStack.pop<Ptr>();

                    opStack.push<Ptr>(addr + idx * size.aligned);
                }
                continue;

            case Opcode::AddrArg:
                {
                    auto offset = readOffset();

                    opStack.push<Ptr>(frame.param + offset);
                }
                continue;

            case Opcode::AddrVar:
                {
                    auto offset = readOffset();

                    opStack.push<Ptr>(frame.local + offset);
                }
                continue;

            case Opcode::AddrMem:
                {
                    auto offset = readOffset();

                    opStack.top<Ptr>() += offset;
                }
                continue;

            case Opcode::Br:
                {
                    auto offset = readConst<int16_t>();
                    auto target = frame.pc + offset;

                    jump(target);
                }
                continue;

            case Opcode::BrFalse:
                {
                    auto offset = readConst<int16_t>();
                    auto target = frame.pc + offset;

                    if (!opStack.pop<bool>())
                        jump(target);
                }
                continue;

            case Opcode::BrTrue:
                {
                    auto offset = readConst<int16_t>();
                    auto target = frame.pc + offset;

                    if (opStack.pop<bool>())
                        jump(target);
                }
                continue;

            case Opcode::Not:
                opStack.push(!opStack.pop<bool>());
                continue;

            case Opcode::ConstFalse:
                opStack.push(false);
                continue;

            case Opcode::ConstTrue:
                opStack.push(true);
                continue;

            case Opcode::ConstI:
                loadConst<Int>();
                continue;

            case Opcode::AddI:
                binaryOp<std::plus<Int>>();
                continue;

            case Opcode::SubI:
                binaryOp<std::minus<Int>>();
                continue;

            case Opcode::MultI:
                binaryOp<std::multiplies<Int>>();
                continue;

            case Opcode::DivI:
                binaryOp<std::divides<Int>>();
                continue;

            case Opcode::ModI:
                binaryOp<std::modulus<Int>>();
                continue;

            case Opcode::NegI:
                opStack.push(-opStack.pop<Int>());
                continue;

            case Opcode::EqI:
                binaryOp<std::equal_to<Int>>();
                continue;

            case Opcode::NeI:
                binaryOp<std::not_equal_to<Int>>();
                continue;

            case Opcode::LtI:
                binaryOp<std::less<Int>>();
                continue;

            case Opcode::LeI:
                binaryOp<std::less_equal<Int>>();
                continue;

            case Opcode::GtI:
                binaryOp<std::greater<Int>>();
                continue;

            case Opcode::GeI:
                binaryOp<std::greater_equal<Int>>();
                continue;

            case Opcode::ConstF:
                loadConst<Float>();
                continue;

            case Opcode::AddF:
                binaryOp<std::plus<Float>>();
                continue;

            case Opcode::SubF:
                binaryOp<std::minus<Float>>();
                continue;

            case Opcode::MultF:
                binaryOp<std::multiplies<Float>>();
                continue;

            case Opcode::DivF:
                binaryOp<std::divides<Float>>();
                continue;

            case Opcode::ModF:
                {
                    auto op2 = opStack.pop<Float>();
                    auto op1 = opStack.pop<Float>();
                    opStack.push(std::fmod(op1, op2));
                }
                continue;

            case Opcode::NegF:
                opStack.push(-opStack.pop<int32_t>());
                continue;

            case Opcode::EqF:
                binaryOp<std::equal_to<Float>>();
                continue;

            case Opcode::NeF:
                binaryOp<std::not_equal_to<Float>>();
                continue;

            case Opcode::LtF:
                binaryOp<std::less<Float>>();
                continue;

            case Opcode::LeF:
                binaryOp<std::less_equal<Float>>();
                continue;

            case Opcode::GtF:
                binaryOp<std::greater<Float>>();
                continue;

            case Opcode::GeF:
                binaryOp<std::greater_equal<Float>>();
                continue;

            case Opcode::CastIF:
                opStack.push(static_cast<Float>(opStack.pop<Int>()));
                continue;

            case Opcode::CastFI:
                opStack.push(static_cast<Int>(opStack.pop<Float>()));
                continue;
        }

        throw std::runtime_error{"invalid opcode "
            + std::to_string(static_cast<char>(op))};
    }
}

Fin::Runtime::Runtime(Size stackSize): opStack{stackSize}
{
    stackPtr = alloc.add(opStack.content(), opStack.capacity());
    instrs.emplace_back(static_cast<char>(Opcode::Term));
}

void Fin::Runtime::load(std::istream &src)
{
    LOG(1) << "Loading...";

    frame = Frame{};
    frame.local = frame.param = stackPtr;
    frame.pc = static_cast<Pc>(instrs.size());

    instrs.insert(instrs.end(),
            std::istreambuf_iterator<char>(src),
            std::istreambuf_iterator<char>());
    instrs.emplace_back(static_cast<char>(Opcode::Term));

    execute();

    LOG(1) << std::endl;
}

void Fin::Runtime::run()
{
    LOG(1) << "Running...";

    checkLibrary();
    mainContract = std::make_unique<Contract>(
            frame.library->functions.at("main()"));

    frame = Frame{};
    frame.pc = 0;
    call(*mainContract);
    execute();

    LOG(1) << std::endl;
}

Fin::Library &Fin::Runtime::createLibrary(const std::string &name)
{
    LibraryID id{name};
    auto lib = std::make_unique<Library>(id);

    auto p = lib.get();
    libraries.emplace(std::move(id), std::move(lib));
    return *p;
}

Fin::Library &Fin::Runtime::getLibrary(const std::string &name)
{
    LibraryID id;
    id.name = name;

    // TODO: load library if not available
    return *libraries.at(id);
}

void Fin::Runtime::backtrace(std::ostream &out) const noexcept
{
    out << "Backtrace:" << std::endl;

    for (const auto &fr : rtStack)
        out << fr << std::endl;

    out << frame << std::endl;
}
