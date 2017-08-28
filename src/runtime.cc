#include "fin/runtime.h"

#include "fin/contract.h"
#include "fin/exception.h"
#include "fin/function.h"
#include "fin/library.h"
#include "fin/type.h"
#include "fin/typeinfo.h"
#include "fin/util.h"
#include "opcode.h"
#include <cassert>
#include <cmath>
#include <functional>
#include <iomanip>
#include <iostream>

namespace
{
} // end of anonymous namespace

Fin::Runtime::Runtime() : eval{alloc}
{
    instrs.emplace_back(static_cast<std::uint8_t>(Opcode::Term));
}

void Fin::Runtime::load(std::istream &src)
{
    LOG(1) << "Loading...";

    frame = Frame{};
    frame.local = frame.param = eval.size();
    frame.pc = static_cast<Pc>(instrs.size());

    instrs.insert(instrs.end(), std::istreambuf_iterator<char>{src},
                  std::istreambuf_iterator<char>{});
    instrs.emplace_back(static_cast<std::uint8_t>(Opcode::Term));

    execute();

    LOG(1) << '\n';
}

void Fin::Runtime::run()
{
    LOG(1) << "Running...";

    checkLibrary();
    mainContract =
            std::make_unique<Contract>(frame.library->function("main()"));

    frame.pc = 0;
    call(*mainContract);
    execute();

    LOG(1) << '\n';

#if FIN_DEBUG > 0
    alloc.summary(std::cerr);
#endif
}

Fin::Library &Fin::Runtime::createLibrary(LibraryID id)
{
    auto lib = std::make_unique<Library>(id);

    auto p = lib.get();
    libraries.emplace(std::move(id), std::move(lib));
    return *p;
}

Fin::Library &Fin::Runtime::getLibrary(const LibraryID &id)
{
    // TODO: load library if not available
    return *libraries.at(id);
}

void Fin::Runtime::backtrace(std::ostream &out) const noexcept
{
    out << "Backtrace:\n";

    for (const auto &fr : rtStack)
        printFrame(out, fr);

    printFrame(out, frame);
}

void Fin::Runtime::printFrame(std::ostream &out, const Frame &fr) const
{
    out << "  in ";
    if (fr.contract != nullptr)
    {
        // TODO: show info on types in contract
        out << fr.contract->name();
    }
    else if (fr.library != nullptr)
    {
        out << '<' << fr.library->id() << '>';
    }
    else
    {
        out << "<<anonymous>>";
    }

    out << '\n';
}
void Fin::Runtime::jump(Pc target)
{
    if (target > instrs.size())
        throw RuntimeError{"jump target " + std::to_string(target) +
                           " out of range " + std::to_string(instrs.size())};
    frame.pc = target;
}

std::string Fin::Runtime::readStr()
{
    auto len = readInt<std::uint16_t>();
    auto val = std::string{reinterpret_cast<char *>(&instrs.at(frame.pc)), len};

    LOG(1) << " '" << val << "'";

    jump(frame.pc + len);
    return val;
}

Fin::Pc Fin::Runtime::readTarget()
{
    auto offset = readInt<std::int32_t>();
    return frame.pc + offset;
}

const Fin::Function &Fin::Runtime::readFunction()
{
    auto idx = readInt<std::uint32_t>();
    auto &fn = frame.library->refFunction(idx);

    LOG(1) << " [" << fn.name() << "]";

    return fn;
}

const Fin::Type &Fin::Runtime::readType()
{
    auto idx = readInt<std::uint32_t>();
    auto &type = frame.library->refType(idx);

    LOG(1) << " [" << type.name() << "]";

    return type;
}

Fin::Contract &Fin::Runtime::readContract()
{
    auto idx = readInt<Index>();
    auto &ctr = frame.contract->contract(idx);

    LOG(1) << " [" << ctr.name() << "]";

    return ctr;
}

Fin::TypeInfo Fin::Runtime::readSize()
{
    auto idx = readInt<Index>();
    auto size = frame.contract->size(idx);

    LOG(1) << " [" << size.size() << " | " << size.alignment() << "]";

    return size;
}

Fin::Offset Fin::Runtime::readOffset()
{
    auto idx = readInt<Index>();
    auto offset = frame.contract->offset(idx);

    LOG(1) << " [" << offset << "]";

    return offset;
}

void Fin::Runtime::ret()
{
    eval.resize(frame.param);

    frame = pop(rtStack);
}

void Fin::Runtime::call(Contract &ctr)
{
    // store current frame
    rtStack.emplace_back(frame);

    // update frame
    frame.contract = &ctr;
    frame.local = frame.param = eval.size();

    frame.library = &ctr.library();

    if (ctr.native())
    {
        ctr.native()(*this, ctr);

        // emplace and pop even for native functions so that we can get full
        // backtrace
        frame = pop(rtStack);
    }
    else
    {
        Pc target;

        // if initialized then we don't need to wait for the Sign instruction
        if (!ctr.initialize(target))
            finalizeCall();

        jump(target);
    }
}

void Fin::Runtime::finalizeCall()
{
    // update param and local ptr
    frame.param = frame.local - frame.contract->argOffset();

    // reserve space for local
    eval.resize(eval.size() + frame.contract->localOffset());
}

void Fin::Runtime::checkLibrary()
{
    if (frame.library == nullptr)
        throw RuntimeError{"no library active"};
}

void Fin::Runtime::checkContract()
{
    if (frame.contract == nullptr)
        throw RuntimeError{"no contract active"};
}

void Fin::Runtime::execute()
{
    Library *refLibrary = nullptr;
    Type *refType = nullptr;

    while (true)
    {
        LOG(2) << '\n';

        auto op = static_cast<Opcode>(instrs.at(frame.pc++));
        LOG(1) << "\n- " << op;

        switch (op)
        {
        case Opcode::Error:
            throw RuntimeError{"error instruction reached"};

        case Opcode::Cookie:
            // skip shebang
            while (instrs.at(frame.pc++) != '\n')
                ;
            break;

        case Opcode::Lib:
        {
            auto name = readStr();

            auto &lib = createLibrary(LibraryID{name});
            frame.library = &lib;
            break;
        }

        case Opcode::Fn:
        {
            checkLibrary();

            auto name = readStr();
            auto gens = readInt<std::uint16_t>();
            auto ctrs = readInt<std::uint16_t>();
            auto loc = readTarget();
            auto end = readTarget();

            frame.library->addFunction(name, frame.pc, loc, gens, ctrs);
            jump(end);
            break;
        }

        case Opcode::Type:
        {
            auto name = readStr();
            auto gens = readInt<std::uint16_t>();
            auto end = readTarget();

            refType = &frame.library->addType(name, gens, frame.pc);
            jump(end);
            break;
        }

        case Opcode::Member:
        {
            if (refType == nullptr)
                throw RuntimeError{"no referencing type"};

            auto name = readStr();

            auto &mem = refType->addMember(name);
            frame.library->addRefMember(mem);
            break;
        }

        case Opcode::RefLib:
        {
            auto name = readStr();

            refLibrary = &getLibrary(LibraryID{name});
            break;
        }

        case Opcode::RefFn:
        {
            checkLibrary();

            if (refLibrary == nullptr)
                throw RuntimeError{"no referencing library"};

            auto name = readStr();

            auto &fn = refLibrary->function(name);
            frame.library->addRefFunction(fn);
            break;
        }

        case Opcode::RefType:
        {
            checkLibrary();

            if (refLibrary == nullptr)
                throw RuntimeError{"no referencing library"};

            auto name = readStr();

            auto &tp = refLibrary->type(name);
            frame.library->addRefType(tp);
            break;
        }

        case Opcode::SizeI:
        {
            checkContract();

            auto size = TypeInfo::native<Int>();
            frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeF:
        {
            checkContract();

            auto size = TypeInfo::native<Float>();
            frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeB:
        {
            checkContract();

            auto size = TypeInfo::native<Bool>();
            frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeP:
        {
            checkContract();

            auto size = TypeInfo::native<Ptr>();
            frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeDup:
        {
            checkContract();

            auto idx = readInt<Index>();

            auto size = frame.contract->size(idx);
            frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeArr:
        {
            checkContract();

            auto len = readInt<Int>();

            auto size = frame.contract->popSize();

            size = TypeInfo{size.alignedSize() * len, size.alignment()};
            frame.contract->addSize(size);
            break;
        }

        case Opcode::TypeCall:
        {
            checkLibrary();
            checkContract();

            auto &type = readType();

            auto &ctr = frame.contract->callType(type);
            call(ctr);
            break;
        }

        case Opcode::TypeRet:
        {
            checkLibrary();
            checkContract();

            TypeInfo size{frame.contract->localOffset(),
                          frame.contract->localAlignment()};
            ret();
            frame.contract->addSize(size);
            break;
        }

        case Opcode::TypeMem:
        {
            checkLibrary();
            checkContract();

            auto idx = readInt<Index>();

            auto mem = frame.library->refMember(idx);
            frame.contract->addMemberOffset(mem);
            break;
        }

        case Opcode::Param:
        {
            checkContract();

            auto size = readSize();

            frame.contract->addArgOffset(size);
            break;
        }

        case Opcode::Local:
        case Opcode::Field:
        {
            checkContract();

            auto size = readSize();

            frame.contract->addLocalOffset(size);
            break;
        }

        case Opcode::Contract:
        {
            checkLibrary();
            checkContract();

            auto &fn = readFunction();

            frame.contract->addContract(fn);
            break;
        }

        case Opcode::Sign:
            finalizeCall();

            // cleanup unneeded data
            frame.contract->sign();
            break;

        case Opcode::Call:
        {
            checkLibrary();

            auto &ctr = readContract();
            call(ctr);
            break;
        }

        case Opcode::Term:
            return;

        case Opcode::End:
            ret();
            break;

        case Opcode::Ret:
        {
            auto size = readSize();

            auto src = eval.topSize(size);

            ret();

            auto dest = eval.pushSize(size);
            src.move(dest, size);
            break;
        }

        case Opcode::Push:
        {
            auto size = readSize();

            eval.pushSize(size);
            break;
        }

        case Opcode::Pop:
        {
            auto size = readSize();

            eval.popSize(size);
            break;
        }

        case Opcode::Dup:
        {
            auto size = readSize();

            auto src = eval.topSize(size);
            auto dest = eval.pushSize(size);

            src.move(dest, size);
            break;
        }

        case Opcode::Load:
        {
            auto size = readSize();

            auto ptr = eval.pop<Ptr>();
            auto src = alloc.readSize(ptr, size);
            auto dest = eval.pushSize(size);

            src.move(dest, size);
            break;
        }

        case Opcode::Store:
        {
            auto size = readSize();

            auto src = eval.popSize(size);
            auto ptr = eval.pop<Ptr>();
            auto dest = alloc.writeSize(ptr, size);

            src.move(dest, size);
            break;
        }

        case Opcode::AddrOff:
        {
            auto size = readSize();

            auto idx = eval.pop<Int>();
            auto addr = eval.pop<Ptr>();

            eval.push<Ptr>(addr + size.alignedSize() * idx);
            break;
        }

        case Opcode::AddrArg:
        {
            auto offset = readOffset();

            eval.push<Ptr>(eval.ptr() + frame.param + offset);
            break;
        }

        case Opcode::AddrVar:
        {
            auto offset = readOffset();

            eval.push<Ptr>(eval.ptr() + frame.local + offset);
            break;
        }

        case Opcode::AddrMem:
        {
            auto offset = readOffset();

            eval.top<Ptr>() += offset;
            break;
        }

        case Opcode::Br:
        {
            auto target = readTarget();

            jump(target);
            break;
        }

        case Opcode::BrFalse:
        {
            auto target = readTarget();

            if (!eval.pop<bool>())
                jump(target);
            break;
        }

        case Opcode::BrTrue:
        {
            auto target = readTarget();

            if (eval.pop<bool>())
                jump(target);
            break;
        }

        case Opcode::ConstFalse:
            eval.push(false);
            break;

        case Opcode::ConstTrue:
            eval.push(true);
            break;

        case Opcode::Not:
            eval.push(!eval.pop<bool>());
            break;

        case Opcode::ConstI:
            eval.push(readConst<Int>());
            break;

        case Opcode::AddI:
            binaryOp<std::plus<Int>>();
            break;

        case Opcode::SubI:
            binaryOp<std::minus<Int>>();
            break;

        case Opcode::MultI:
            binaryOp<std::multiplies<Int>>();
            break;

        case Opcode::DivI:
            binaryOp<std::divides<Int>>();
            break;

        case Opcode::ModI:
            binaryOp<std::modulus<Int>>();
            break;

        case Opcode::NegI:
            eval.push(-eval.pop<Int>());
            break;

        case Opcode::EqI:
            binaryOp<std::equal_to<Int>>();
            break;

        case Opcode::NeI:
            binaryOp<std::not_equal_to<Int>>();
            break;

        case Opcode::LtI:
            binaryOp<std::less<Int>>();
            break;

        case Opcode::LeI:
            binaryOp<std::less_equal<Int>>();
            break;

        case Opcode::GtI:
            binaryOp<std::greater<Int>>();
            break;

        case Opcode::GeI:
            binaryOp<std::greater_equal<Int>>();
            break;

        case Opcode::ConstF:
            eval.push(readConst<Float>());
            break;

        case Opcode::AddF:
            binaryOp<std::plus<Float>>();
            break;

        case Opcode::SubF:
            binaryOp<std::minus<Float>>();
            break;

        case Opcode::MultF:
            binaryOp<std::multiplies<Float>>();
            break;

        case Opcode::DivF:
            binaryOp<std::divides<Float>>();
            break;

        case Opcode::ModF:
        {
            auto op2 = eval.pop<Float>();
            auto op1 = eval.pop<Float>();
            eval.push(std::fmod(op1, op2));
            break;
        }

        case Opcode::NegF:
            eval.push(-eval.pop<int32_t>());
            break;

        case Opcode::EqF:
            binaryOp<std::equal_to<Float>>();
            break;

        case Opcode::NeF:
            binaryOp<std::not_equal_to<Float>>();
            break;

        case Opcode::LtF:
            binaryOp<std::less<Float>>();
            break;

        case Opcode::LeF:
            binaryOp<std::less_equal<Float>>();
            break;

        case Opcode::GtF:
            binaryOp<std::greater<Float>>();
            break;

        case Opcode::GeF:
            binaryOp<std::greater_equal<Float>>();
            break;

        case Opcode::CastIF:
            eval.push(static_cast<Float>(eval.pop<Int>()));
            break;

        case Opcode::CastFI:
            eval.push(static_cast<Int>(eval.pop<Float>()));
            break;

        default:
            throw RuntimeError{"invalid opcode " +
                               std::to_string(static_cast<std::uint8_t>(op))};
        }
    }
}
