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
#include <sstream>

Fin::Runtime::Runtime() : _eval{_alloc}
{
    _instrs.emplace_back(static_cast<std::uint8_t>(Opcode::Term));
}

void Fin::Runtime::load(std::istream &src)
{
    LOG(1) << "Loading...";

    _frame = Frame{};
    _frame.local = _frame.param = _eval.size();
    _frame.pc = static_cast<Pc>(_instrs.size());

    _instrs.insert(_instrs.end(), std::istreambuf_iterator<char>{src},
                  std::istreambuf_iterator<char>{});
    _instrs.emplace_back(static_cast<std::uint8_t>(Opcode::Term));

    execute();

    LOG(1) << '\n';
}

void Fin::Runtime::run()
{
    LOG(1) << "Running...";

    checkLibrary();
    _mainContract =
            std::make_unique<Contract>(_frame.library->function("main()"));

    _frame.pc = 0;
    call(*_mainContract);
    execute();

    LOG(1) << '\n' << _alloc.summary();
}

Fin::Library &Fin::Runtime::createLibrary(LibraryID id)
{
    auto lib = std::make_unique<Library>(id);

    auto p = lib.get();
    _libraries.emplace(std::move(id), std::move(lib));
    return *p;
}

Fin::Library &Fin::Runtime::getLibrary(const LibraryID &id)
{
    // TODO: load library if not available
    return *_libraries.at(id);
}

std::string Fin::Runtime::backtrace() const noexcept
{
    std::ostringstream out{};
    out << "Backtrace:\n";

    for (const auto &fr : _frames)
        printFrame(out, fr);

    printFrame(out, _frame);
    return out.str();
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
    if (target > _instrs.size())
        throw RuntimeError{"jump target " + std::to_string(target) +
                           " out of range " + std::to_string(_instrs.size())};
    _frame.pc = target;
}

std::string Fin::Runtime::readStr()
{
    auto len = readInt<std::uint16_t>();
    auto val = std::string{reinterpret_cast<char *>(&_instrs.at(_frame.pc)), len};

    LOG(1) << " '" << val << "'";

    jump(_frame.pc + len);
    return val;
}

Fin::Pc Fin::Runtime::readTarget()
{
    auto offset = readInt<std::int32_t>();
    return _frame.pc + offset;
}

const Fin::Function &Fin::Runtime::readFunction()
{
    auto idx = readInt<std::uint32_t>();
    auto &fn = _frame.library->refFunction(idx);

    LOG(1) << " [" << fn.name() << "]";

    return fn;
}

const Fin::Type &Fin::Runtime::readType()
{
    auto idx = readInt<std::uint32_t>();
    auto &type = _frame.library->refType(idx);

    LOG(1) << " [" << type.name() << "]";

    return type;
}

Fin::Contract &Fin::Runtime::readContract()
{
    auto idx = readInt<Index>();
    auto &ctr = _frame.contract->contract(idx);

    LOG(1) << " [" << ctr.name() << "]";

    return ctr;
}

Fin::TypeInfo Fin::Runtime::readSize()
{
    auto idx = readInt<Index>();
    auto size = _frame.contract->size(idx);

    LOG(1) << " [" << size.size() << " | " << size.alignment() << "]";

    return size;
}

Fin::Offset Fin::Runtime::readOffset()
{
    auto idx = readInt<Index>();
    auto offset = _frame.contract->offset(idx);

    LOG(1) << " [" << offset << "]";

    return offset;
}

void Fin::Runtime::ret()
{
    _eval.resize(_frame.param);

    _frame = pop(_frames);
}

void Fin::Runtime::call(Contract &ctr)
{
    // store current _frame
    _frames.emplace_back(_frame);

    // update _frame
    _frame.contract = &ctr;
    _frame.local = _frame.param = _eval.size();

    _frame.library = &ctr.library();

    if (ctr.native())
    {
        ctr.native()(*this, ctr);

        // emplace and pop even for native functions so that we can get full
        // backtrace
        _frame = pop(_frames);
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
    _frame.param = _frame.local - _frame.contract->argOffset();

    // reserve space for local
    _eval.resize(_eval.size() + _frame.contract->localOffset());
}

void Fin::Runtime::checkLibrary()
{
    if (_frame.library == nullptr)
        throw RuntimeError{"no library active"};
}

void Fin::Runtime::checkContract()
{
    if (_frame.contract == nullptr)
        throw RuntimeError{"no contract active"};
}

void Fin::Runtime::execute()
{
    Library *refLibrary = nullptr;
    Type *refType = nullptr;

    while (true)
    {
        LOG(2) << '\n';

        auto op = static_cast<Opcode>(_instrs.at(_frame.pc++));
        LOG(1) << "\n- " << op;

        switch (op)
        {
        case Opcode::Error:
            throw RuntimeError{"error instruction reached"};

        case Opcode::Cookie:
            // skip shebang
            while (_instrs.at(_frame.pc++) != '\n')
                ;
            break;

        case Opcode::Lib:
        {
            auto name = readStr();

            auto &lib = createLibrary(LibraryID{name});
            _frame.library = &lib;
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

            _frame.library->addFunction(name, _frame.pc, loc, gens, ctrs);
            jump(end);
            break;
        }

        case Opcode::Type:
        {
            auto name = readStr();
            auto gens = readInt<std::uint16_t>();
            auto end = readTarget();

            refType = &_frame.library->addType(name, gens, _frame.pc);
            jump(end);
            break;
        }

        case Opcode::Member:
        {
            if (refType == nullptr)
                throw RuntimeError{"no referencing type"};

            auto name = readStr();

            auto &mem = refType->addMember(name);
            _frame.library->addRefMember(mem);
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
            _frame.library->addRefFunction(fn);
            break;
        }

        case Opcode::RefType:
        {
            checkLibrary();

            if (refLibrary == nullptr)
                throw RuntimeError{"no referencing library"};

            auto name = readStr();

            auto &tp = refLibrary->type(name);
            _frame.library->addRefType(tp);
            break;
        }

        case Opcode::SizeI:
        {
            checkContract();

            auto size = TypeInfo::native<Int>();
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeF:
        {
            checkContract();

            auto size = TypeInfo::native<Float>();
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeB:
        {
            checkContract();

            auto size = TypeInfo::native<Bool>();
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeP:
        {
            checkContract();

            auto size = TypeInfo::native<Ptr>();
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeDup:
        {
            checkContract();

            auto idx = readInt<Index>();

            auto size = _frame.contract->size(idx);
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::SizeArr:
        {
            checkContract();

            auto len = readInt<Int>();

            auto size = _frame.contract->popSize();

            size = TypeInfo{size.alignedSize() * len, size.alignment()};
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::TypeCall:
        {
            checkLibrary();
            checkContract();

            auto &type = readType();

            auto &ctr = _frame.contract->callType(type);
            call(ctr);
            break;
        }

        case Opcode::TypeRet:
        {
            checkLibrary();
            checkContract();

            TypeInfo size{_frame.contract->localOffset(),
                          _frame.contract->localAlignment()};
            ret();
            _frame.contract->addSize(size);
            break;
        }

        case Opcode::TypeMem:
        {
            checkLibrary();
            checkContract();

            auto idx = readInt<Index>();

            auto mem = _frame.library->refMember(idx);
            _frame.contract->addMemberOffset(mem);
            break;
        }

        case Opcode::Param:
        {
            checkContract();

            auto size = readSize();

            _frame.contract->addArgOffset(size);
            break;
        }

        case Opcode::Local:
        case Opcode::Field:
        {
            checkContract();

            auto size = readSize();

            _frame.contract->addLocalOffset(size);
            break;
        }

        case Opcode::Contract:
        {
            checkLibrary();
            checkContract();

            auto &fn = readFunction();

            _frame.contract->addContract(fn);
            break;
        }

        case Opcode::Sign:
            finalizeCall();

            // cleanup unneeded data
            _frame.contract->sign();
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

            auto src = _eval.topSize(size);

            ret();

            auto dest = _eval.pushSize(size);
            src.move(dest, size);
            break;
        }

        case Opcode::Push:
        {
            auto size = readSize();

            _eval.pushSize(size);
            break;
        }

        case Opcode::Pop:
        {
            auto size = readSize();

            _eval.popSize(size);
            break;
        }

        case Opcode::Dup:
        {
            auto size = readSize();

            auto src = _eval.topSize(size);
            auto dest = _eval.pushSize(size);

            src.move(dest, size);
            break;
        }

        case Opcode::Load:
        {
            auto size = readSize();

            auto ptr = _eval.pop<Ptr>();
            auto src = _alloc.readSize(ptr, size);
            auto dest = _eval.pushSize(size);

            src.move(dest, size);
            break;
        }

        case Opcode::Store:
        {
            auto size = readSize();

            auto src = _eval.popSize(size);
            auto ptr = _eval.pop<Ptr>();
            auto dest = _alloc.writeSize(ptr, size);

            src.move(dest, size);
            break;
        }

        case Opcode::AddrOff:
        {
            auto size = readSize();

            auto idx = _eval.pop<Int>();
            auto addr = _eval.pop<Ptr>();

            _eval.push<Ptr>(addr + size.alignedSize() * idx);
            break;
        }

        case Opcode::AddrArg:
        {
            auto offset = readOffset();

            _eval.push<Ptr>(_eval.ptr() + _frame.param + offset);
            break;
        }

        case Opcode::AddrVar:
        {
            auto offset = readOffset();

            _eval.push<Ptr>(_eval.ptr() + _frame.local + offset);
            break;
        }

        case Opcode::AddrMem:
        {
            auto offset = readOffset();

            _eval.top<Ptr>() += offset;
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

            if (!_eval.pop<bool>())
                jump(target);
            break;
        }

        case Opcode::BrTrue:
        {
            auto target = readTarget();

            if (_eval.pop<bool>())
                jump(target);
            break;
        }

        case Opcode::ConstFalse:
            _eval.push(false);
            break;

        case Opcode::ConstTrue:
            _eval.push(true);
            break;

        case Opcode::Not:
            _eval.push(!_eval.pop<bool>());
            break;

        case Opcode::ConstI:
            _eval.push(readConst<Int>());
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
            _eval.push(-_eval.pop<Int>());
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
            _eval.push(readConst<Float>());
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
            auto op2 = _eval.pop<Float>();
            auto op1 = _eval.pop<Float>();
            _eval.push(std::fmod(op1, op2));
            break;
        }

        case Opcode::NegF:
            _eval.push(-_eval.pop<int32_t>());
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
            _eval.push(static_cast<Float>(_eval.pop<Int>()));
            break;

        case Opcode::CastFI:
            _eval.push(static_cast<Int>(_eval.pop<Float>()));
            break;

        default:
            throw RuntimeError{"invalid opcode " +
                               std::to_string(static_cast<std::uint8_t>(op))};
        }
    }
}
