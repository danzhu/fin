#include "runtime.h"

#include <functional>
#include <iostream>
#include "opcode.h"

void Fin::Runtime::jump(int16_t target)
{
    pc = target;
    if (pc > instrs.size())
        throw std::out_of_range{"pc out of range"};
}

int16_t Fin::Runtime::frameOffset()
{
    auto offset = readConst<int16_t>();
    if (offset < 0)
    {
        offset -= (sizeof(Module::id) + sizeof(Method::argSize)
                + sizeof(pc) + sizeof(fp));
    }
    return offset;
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
    // restore previous frame
    opStack.resize(fp);

    opStack.pop(fp);
    opStack.pop(pc);
    auto argSize = opStack.pop<decltype(Method::argSize)>();
    auto id = opStack.pop<decltype(Module::id)>();

    opStack.resize(opStack.size() - argSize);
    execModule = modules.at(id).get();
}

void Fin::Runtime::call(const Method &method)
{
#ifdef DEBUG
    std::cerr << "  calling " << method.name << std::endl;
#endif
    if (method.nativeMethod)
    {
        method.nativeMethod(*this, opStack);
    }
    else
    {
        auto &module = *method.module;

        // store current frame
        opStack.push(module.id);
        opStack.push(method.argSize);
        opStack.push(pc);
        opStack.push(fp);

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
    std::vector<Module *> refModules;
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
                    execModule = declModule = module;
                    refModules.clear();
                    refModules.emplace_back(module);
                }
                continue;

            case Opcode::Method:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    auto name = readStr();
                    auto argSize = readConst<decltype(Method::argSize)>();
                    auto skip = readConst<uint32_t>();

                    declModule->addMethod(name, Method{declModule, pc, argSize});
                    jump(pc + skip);
                }
                continue;

            case Opcode::RefModule:
                {
                    auto name = readStr();

                    refModules.emplace_back(&getModule(name));
                }
                continue;

            case Opcode::RefMethod:
                {
                    if (!declModule)
                        throw std::runtime_error{"no declaring module"};

                    auto name = readStr();

                    Method *method = nullptr;
                    for (auto itModule : refModules)
                    {
                        auto itMethod = itModule->methods.find(name);
                        if (itMethod == itModule->methods.end())
                            continue;
                        method = &itMethod->second;
                        break;
                    }

                    if (!method)
                        throw std::runtime_error{"unable to find method '" + name + "'"};
                    declModule->refMethods.emplace_back(method);
                }
                continue;

            case Opcode::Call:
                {
                    if (!execModule)
                        throw std::runtime_error{"no executing module"};

                    auto idx = readConst<uint16_t>();
                    const auto &method = *execModule->refMethods.at(idx);
                    call(method);
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
                    jump(pc + offset);
                }
                continue;

            case Opcode::BrFalse:
                {
                    auto offset = readConst<int16_t>();
                    if (!opStack.pop<bool>())
                        jump(pc + offset);
                }
                continue;

            case Opcode::BrTrue:
                {
                    auto offset = readConst<int16_t>();
                    if (opStack.pop<bool>())
                        jump(pc + offset);
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
                    auto size = readConst<uint16_t>();
                    opStack.push(opStack.at(fp + frameOffset(), size), size);
                }
                continue;

            case Opcode::StoreArg:
                {
                    auto size = readConst<uint16_t>();
                    opStack.pop(opStack.at(fp + frameOffset(), size), size);
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
                    auto offset = readConst<uint32_t>();
                    opStack.push(static_cast<Ptr>(offset));
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
    module->id = modules.size();

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
