#include "runtime.h"

#include <cmath>
#include <functional>
#include <iostream>
#include "opcode.h"

void Fin::Runtime::jump(int32_t target)
{
    pc = target;
    if (pc > instrs.size())
        throw std::out_of_range{"pc out of range"};
}

std::string Fin::Runtime::readStr()
{
    auto len = readConst<uint16_t>();
    auto val = std::string{&instrs.at(pc), len};
    jump(pc + len);
    return val;
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
#ifdef DEBUG
    std::cerr << "  calling " << fn.name << std::endl;
#endif
    if (fn.native)
    {
        // TODO: update runtime stack
        fn.native(*this, opStack);
    }
    else
    {
        // store current frame
        rtStack.emplace_back(Frame{execModule, execFunction, pc, fp, argSize});

        // update frame
        execModule = fn.module;
        execFunction = &fn;
        fp = opStack.size();
        jump(fn.location);
    }
}

void Fin::Runtime::execute()
{
    pc = 0;
    fp = 0;

    Module *declModule = nullptr;
    Module *refModule = nullptr;
    execModule = nullptr;
    execFunction = nullptr;

    while (true)
    {
        auto op = readConst<Opcode>();

#ifdef DEBUG
        std::cerr << "> " << Opnames.at(static_cast<uint8_t>(op)) << std::endl;
#endif

        switch (op)
        {
            case Opcode::Error:
                throw std::runtime_error{"error instruction reached"};

            case Opcode::Cookie:
                // skip shebang
                while (readConst<char>() != '\n');
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

                    auto idx = readConst<uint32_t>();
                    auto argSize = readConst<uint16_t>();

                    auto &fn = *execModule->refFunctions.at(idx);
                    call(fn, argSize);
                }
                continue;

            case Opcode::Return:
                ret();
                continue;

            case Opcode::Term:
                return;

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

            case Opcode::Alloc:
                opStack.push(alloc.alloc(opStack.pop<int32_t>()));
                continue;

            case Opcode::Dealloc:
                alloc.dealloc(opStack.pop<Ptr>());
                continue;

            case Opcode::Push:
                {
                    auto size = readConst<uint16_t>();
                    opStack.resize(opStack.size() + size);
                }
                continue;

            case Opcode::Pop:
                {
                    auto size = readConst<uint16_t>();
                    opStack.resize(opStack.size() - size);
                }
                continue;

            case Opcode::LoadArg:
                {
                    auto offset = readConst<int16_t>();
                    auto target = fp + offset;
                    auto size = readConst<uint16_t>();

                    opStack.push(opStack.at(target, size), size);
                }
                continue;

            case Opcode::StoreArg:
                {
                    auto offset = readConst<int16_t>();
                    auto target = fp + offset;
                    auto size = readConst<uint16_t>();

                    opStack.pop(opStack.at(target, size), size);
                }
                continue;

            case Opcode::LoadPtr:
                {
                    auto offset = readConst<uint32_t>();
                    auto size = readConst<uint16_t>();
                    auto ptr = opStack.pop<Ptr>();
                    opStack.push(alloc.deref(ptr + offset, size), size);
                }
                continue;

            case Opcode::StorePtr:
                {
                    auto offset = readConst<uint32_t>();
                    auto size = readConst<uint16_t>();
                    auto ptr = opStack.pop<Ptr>();
                    opStack.pop(alloc.deref(ptr + offset, size), size);
                }
                continue;

            case Opcode::AddrFrame:
                {
                    auto offset = readConst<int16_t>();
                    opStack.push(static_cast<Ptr>(fp + offset));
                }
                continue;

            case Opcode::ReturnVal:
                {
                    auto size = readConst<uint16_t>();
                    std::unique_ptr<char[]> val{new char[size]};
                    opStack.pop(val.get(), size);
                    ret();
                    opStack.push(val.get(), size);
                }
                continue;

            case Opcode::ConstFalse:
                opStack.push(false);
                continue;

            case Opcode::ConstTrue:
                opStack.push(true);
                continue;

            case Opcode::ConstI:
                loadConst<uint32_t>();
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
    {
        out << "  in ";
        if (frame.function)
            out << frame.function->name;
        else
            out << "<module>";
        out << std::endl;
    }
}
