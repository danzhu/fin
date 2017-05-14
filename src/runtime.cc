#include "runtime.h"

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
    auto frame = rtStack.top();
    rtStack.pop();

    // restore previous frame
    opStack.resize(fp - frame.argSize);

    execModule = &frame.module;
    pc = frame.returnAddress;
    fp = frame.framePointer;
}

void Fin::Runtime::call(const Method &method, uint16_t argSize)
{
#ifdef DEBUG
    std::cerr << "  calling " << method.name << std::endl;
#endif
    if (method.nativeMethod)
    {
        // TODO: update runtime stack
        method.nativeMethod(*this, opStack);
    }
    else
    {
        // store current frame
        rtStack.emplace(Frame{*method.module, pc, fp, argSize});

        // update frame
        fp = opStack.size();
        jump(method.location);
    }
}

void Fin::Runtime::execute()
{
    pc = 0;
    fp = 0;

    Module *declModule = nullptr;
    Module *refModule = nullptr;
    execModule = nullptr;

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
                    declModule = refModule = execModule = module;
                }
                continue;

            case Opcode::Method:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    auto name = readStr();
                    auto skip = readConst<uint32_t>();
                    auto target = pc + skip;

                    Method *method = &declModule->addMethod(name, Method{pc});
                    declModule->refMethods.emplace_back(method);
                    jump(target);
                }
                continue;

            case Opcode::RefModule:
                {
                    auto name = readStr();

                    refModule = &getModule(name);
                }
                continue;

            case Opcode::RefMethod:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    if (!refModule)
                        throw std::runtime_error{"no referencing module"};

                    auto name = readStr();

                    auto it = refModule->methods.find(name);
                    if (it == refModule->methods.end())
                        throw std::runtime_error{"unable to find method '"
                            + name + "'"};

                    declModule->refMethods.emplace_back(&it->second);
                }
                continue;

            case Opcode::Call:
                {
                    if (!execModule)
                        throw std::runtime_error{"no executing module"};

                    auto idx = readConst<uint32_t>();
                    auto argSize = readConst<uint16_t>();

                    auto &method = *execModule->refMethods.at(idx);
                    call(method, argSize);
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
