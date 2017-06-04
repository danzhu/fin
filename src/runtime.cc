#include "runtime.h"

#include <cmath>
#include <functional>
#include <iostream>
#include "opcode.h"

void move(const char *src, char *dest, uint16_t size)
{
    LOG(2) << std::endl << "  = ";
    LOG_HEX(2, src, size);

    for (uint16_t i = 0; i < size; ++i)
        dest[i] = src[i];
}

void Fin::Runtime::jump(uint32_t target)
{
    if (target > instrs.size())
        throw std::out_of_range{"jump target " + std::to_string(target)
            + " out of range " + std::to_string(instrs.size())};
    pc = target;
}

std::string Fin::Runtime::readStr()
{
    auto len = readConst<uint16_t>();
    auto val = std::string{&instrs.at(pc), len};

    LOG(1) << " '" << val << "'";

    jump(pc + len);
    return val;
}

Fin::Function &Fin::Runtime::readFn()
{
    auto idx = readConst<uint32_t>();
    auto &fn = *execModule->refFunctions.at(idx);

    LOG(1) << " [" << fn.name << "]";

    return fn;
}

void Fin::Runtime::ret()
{
    auto frame = rtStack.back();
    rtStack.pop_back();

    // restore previous frame
    opStack.resize(fp - frame.argSize);

    execModule = frame.module;
    execFunction = frame.function;
    pc = frame.returnAddress;
    fp = frame.framePointer;
}

void Fin::Runtime::call(const Function &fn, uint16_t argSize)
{
    // store current frame
    auto frame = Frame{execModule, execFunction, pc, fp, argSize};
    rtStack.emplace_back(frame);

    // update frame
    execModule = fn.module;
    execFunction = &fn;

    if (fn.native)
    {
        fn.native(*this, opStack);

        // emplace and pop even for native functions so that we can get full
        // backtrace
        rtStack.pop_back();

        execModule = frame.module;
        execFunction = frame.function;
    }
    else
    {
        fp = opStack.size();
        jump(fn.location);
    }
}

void Fin::Runtime::printFrame(std::ostream &out, const Function *fn)
    const noexcept
{
    out << "  in ";
    if (!fn)
        out << "<module>";
    else if (fn->native)
        out << fn->name << " [native]";
    else
        out << fn->name;
    out << std::endl;
}

void Fin::Runtime::execute()
{
    pc = 0;
    fp = 0;

    Module *declModule = nullptr;
    Module *refModule = nullptr;
    execModule = nullptr;
    execFunction = nullptr;

    LOG(1) << "Logging at level " << DEBUG << "...";

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
                while (instrs.at(pc++) != '\n');
                continue;

            case Opcode::Module:
                {
                    auto name = readStr();

                    auto module = &createModule(name);
                    execModule = refModule = declModule = module;
                }
                continue;

            case Opcode::Function:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    auto name = readStr();
                    auto skip = readConst<uint32_t>();
                    auto target = pc + skip;

                    Function *fn = &declModule->addFunction(name, Function{pc});
                    declModule->refFunctions.emplace_back(fn);
                    jump(target);
                }
                continue;

            case Opcode::RefModule:
                {
                    auto name = readStr();

                    refModule = &getModule(name);
                }
                continue;

            case Opcode::RefFunction:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    if (!refModule)
                        throw std::runtime_error{"no referencing module"};

                    auto name = readStr();

                    auto it = refModule->functions.find(name);
                    if (it == refModule->functions.end())
                        throw std::runtime_error{"unable to find functions '"
                            + name + "'"};

                    declModule->refFunctions.emplace_back(&it->second);
                }
                continue;

            case Opcode::Call:
                {
                    if (!execModule)
                        throw std::runtime_error{"no executing module"};

                    auto &fn = readFn();
                    auto argSize = readConst<uint16_t>();

                    call(fn, argSize);
                }
                continue;

            case Opcode::Reduce:
                {
                    auto size = readConst<uint16_t>();
                    auto amount = readConst<uint16_t>();

                    auto loc = opStack.size() - size;
                    auto src = opStack.at(loc, size);
                    auto dest = opStack.at(loc - amount, size);
                    move(src, dest, size);
                    opStack.pop(amount);
                }
                continue;

            case Opcode::Return:
                ret();
                continue;

            case Opcode::ReturnVal:
                {
                    auto size = readConst<uint16_t>();

                    auto src = opStack.pop(size);
                    ret();
                    auto dest = opStack.push(size);
                    move(src, dest, size);
                }
                continue;

            case Opcode::Term:
                LOG(1) << std::endl << "Terminating..." << std::endl;
                return;

            case Opcode::Alloc:
                opStack.push(alloc.alloc(opStack.pop<int32_t>()));
                continue;

            case Opcode::Dealloc:
                alloc.dealloc(opStack.pop<Ptr>());
                continue;

            case Opcode::Push:
                {
                    auto size = readConst<uint16_t>();

                    opStack.push(size);
                }
                continue;

            case Opcode::Pop:
                {
                    auto size = readConst<uint16_t>();

                    opStack.pop(size);
                }
                continue;

            case Opcode::Dup:
                {
                    auto size = readConst<uint16_t>();

                    auto src = opStack.top(size);
                    auto dest = opStack.push(size);
                    move(src, dest, size);
                }
                continue;

            case Opcode::Load:
                {
                    auto size = readConst<uint16_t>();

                    auto ptr = opStack.pop<Ptr>();
                    auto src = alloc.read(ptr, size);
                    auto dest = opStack.push(size);
                    move(src, dest, size);
                }
                continue;

            case Opcode::Store:
                {
                    auto size = readConst<uint16_t>();

                    auto src = opStack.pop(size);
                    auto ptr = opStack.pop<Ptr>();
                    auto dest = alloc.write(ptr, size);
                    move(src, dest, size);
                }
                continue;

            case Opcode::AddrFrame:
                {
                    auto offset = readConst<int16_t>();
                    opStack.push(static_cast<Ptr>(fp + offset));
                }
                continue;

            case Opcode::AddrOffset:
                {
                    auto size = readConst<uint16_t>();

                    auto offset = opStack.pop<uint32_t>();
                    auto ptr = opStack.pop<Ptr>();
                    opStack.push(ptr + offset * size);
                }
                continue;

            case Opcode::Offset:
                {
                    auto offset = readConst<uint32_t>();
                    opStack.push(opStack.pop<uint64_t>() + offset);
                }
                continue;

            case Opcode::Br:
                {
                    auto offset = readConst<int16_t>();
                    auto target = pc + offset;

                    jump(target);
                }
                continue;

            case Opcode::BrFalse:
                {
                    auto offset = readConst<int16_t>();
                    auto target = pc + offset;

                    if (!opStack.pop<bool>())
                        jump(target);
                }
                continue;

            case Opcode::BrTrue:
                {
                    auto offset = readConst<int16_t>();
                    auto target = pc + offset;

                    if (opStack.pop<bool>())
                        jump(target);
                }
                continue;

            case Opcode::ConstFalse:
                opStack.push(false);
                continue;

            case Opcode::ConstTrue:
                opStack.push(true);
                continue;

            case Opcode::ConstI:
                loadConst<int32_t>();
                continue;

            case Opcode::AddI:
                binaryOp<std::plus<int32_t>>();
                continue;

            case Opcode::SubI:
                binaryOp<std::minus<int32_t>>();
                continue;

            case Opcode::MultI:
                binaryOp<std::multiplies<int32_t>>();
                continue;

            case Opcode::DivI:
                binaryOp<std::divides<int32_t>>();
                continue;

            case Opcode::ModI:
                binaryOp<std::modulus<int32_t>>();
                continue;

            case Opcode::NegI:
                opStack.push(-opStack.pop<int32_t>());
                continue;

            case Opcode::EqI:
                binaryOp<std::equal_to<int32_t>>();
                continue;

            case Opcode::NeI:
                binaryOp<std::not_equal_to<int32_t>>();
                continue;

            case Opcode::LtI:
                binaryOp<std::less<int32_t>>();
                continue;

            case Opcode::LeI:
                binaryOp<std::less_equal<int32_t>>();
                continue;

            case Opcode::GtI:
                binaryOp<std::greater<int32_t>>();
                continue;

            case Opcode::GeI:
                binaryOp<std::greater_equal<int32_t>>();
                continue;

            case Opcode::ConstF:
                loadConst<float>();
                continue;

            case Opcode::AddF:
                binaryOp<std::plus<float>>();
                continue;

            case Opcode::SubF:
                binaryOp<std::minus<float>>();
                continue;

            case Opcode::MultF:
                binaryOp<std::multiplies<float>>();
                continue;

            case Opcode::DivF:
                binaryOp<std::divides<float>>();
                continue;

            case Opcode::ModF:
                {
                    auto op2 = opStack.pop<float>();
                    auto op1 = opStack.pop<float>();
                    opStack.push(std::fmod(op1, op2));
                }
                continue;

            case Opcode::NegF:
                opStack.push(-opStack.pop<int32_t>());
                continue;

            case Opcode::EqF:
                binaryOp<std::equal_to<float>>();
                continue;

            case Opcode::NeF:
                binaryOp<std::not_equal_to<float>>();
                continue;

            case Opcode::LtF:
                binaryOp<std::less<float>>();
                continue;

            case Opcode::LeF:
                binaryOp<std::less_equal<float>>();
                continue;

            case Opcode::GtF:
                binaryOp<std::greater<float>>();
                continue;

            case Opcode::GeF:
                binaryOp<std::greater_equal<float>>();
                continue;
        }

        throw std::runtime_error{"invalid opcode "
            + std::to_string(static_cast<char>(op))};
    }
}

Fin::Runtime::Runtime()
{
    alloc.add(opStack.content(), opStack.capacity());
}

void Fin::Runtime::run(std::istream &src)
{
    instrs.assign(std::istreambuf_iterator<char>(src),
            std::istreambuf_iterator<char>());
    instrs.emplace_back(static_cast<char>(Opcode::Term));
    execute();
}

uint32_t Fin::Runtime::programCounter() const noexcept
{
    return pc;
}

Fin::Module &Fin::Runtime::createModule(const std::string &name)
{
    ModuleID id;
    id.name = name;

    auto module = std::make_unique<Module>();
    module->id = static_cast<decltype(Module::id)>(modules.size());

    auto p = module.get();
    modules.emplace_back(std::move(module));
    modulesByID.emplace(id, p);
    return *p;
}

Fin::Module &Fin::Runtime::getModule(const std::string &name)
{
    ModuleID id;
    id.name = name;

    // TODO: load module if not available
    return *modulesByID.at(id);
}

void Fin::Runtime::backtrace(std::ostream &out) const noexcept
{
    out << "Backtrace:" << std::endl;

    for (const auto &frame : rtStack)
        printFrame(out, frame.function);
    printFrame(out, execFunction);
}
