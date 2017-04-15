#include "runtime.h"

#include <functional>
#include <iostream>
#include "opcode.h"

std::string Fin::Runtime::readStr()
{
    auto len = readConst<uint16_t>();
    auto val = std::string{&instrs.at(pc), len};
    pc += len;
    return val;
}

void Fin::Runtime::execute()
{
    pc = 0;
    fp = 0;

    Module *declModule = nullptr;
    Module *refModule = nullptr;
    currentModule = nullptr;

    while (true)
    {
        auto op = static_cast<Opcode>(instrs.at(pc));
        ++pc;

        switch (op)
        {
            case Opcode::error:
                throw std::runtime_error{"error"};

            case Opcode::module:
                {
                    ModuleID id;
                    id.name = readStr();
                    auto methodSize = readConst<uint16_t>();

                    auto module = &createModule(id, methodSize);
                    currentModule = refModule = declModule = module;
                }
                continue;

            case Opcode::method:
                {
                    auto idx = readConst<uint16_t>();
                    auto argSize = readConst<decltype(Method::argSize)>();
                    auto skip = readConst<uint32_t>();

                    declModule->methods.at(idx) = Method{declModule, pc, argSize};
                    pc += skip;
                }
                continue;

            case Opcode::module_ref:
                {
                    ModuleID id;
                    id.name = readStr();
                    refModule = modulesByID.at(id);

                    // TODO: load module if not available
                }
                continue;

            case Opcode::method_ref:
                {
                    auto methodIdx = readConst<uint16_t>();

                    auto method = &refModule->methods.at(methodIdx);
                    declModule->methodRefs.emplace_back(method);
                }
                continue;

            case Opcode::call:
                {
                    auto idx = readConst<uint16_t>();

                    auto &method = *currentModule->methodRefs.at(idx);

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
                        pc = method.location;
                    }
                }
                continue;

            case Opcode::ret:
                {
                    // restore previous frame
                    opStack.resize(fp);

                    opStack.pop(fp);
                    opStack.pop(pc);
                    auto argSize = opStack.pop<decltype(Method::argSize)>();
                    auto id = opStack.pop<decltype(Module::id)>();

                    opStack.resize(opStack.size() - argSize);
                    currentModule = modules.at(id).get();
                }
                continue;

            case Opcode::term:
                return;

            case Opcode::const_i:
                loadConst<int32_t>();
                continue;

            case Opcode::load_i:
                load<int32_t>();
                continue;

            case Opcode::store_i:
                store<int32_t>();
                continue;

            case Opcode::add_i:
                binaryOp<std::plus<int32_t>>();
                continue;

            case Opcode::sub_i:
                binaryOp<std::minus<int32_t>>();
                continue;

            case Opcode::mult_i:
                binaryOp<std::multiplies<int32_t>>();
                continue;

            case Opcode::div_i:
                binaryOp<std::divides<int32_t>>();
                continue;
        }

        throw std::runtime_error{"invalid opcode "
            + std::to_string(static_cast<char>(op))};
    }
}

void Fin::Runtime::run(std::istream &src)
{
    instrs.assign(std::istreambuf_iterator<char>(src),
            std::istreambuf_iterator<char>());
    instrs.emplace_back(static_cast<char>(Opcode::term));
    execute();
}

uint32_t Fin::Runtime::programCounter() const noexcept
{
    return pc;
}

Fin::Module &Fin::Runtime::createModule(const ModuleID &id, uint16_t methodSize)
{
    auto module = std::make_unique<Module>(methodSize);
    module->id = modules.size();

    auto p = module.get();
    modules.emplace_back(std::move(module));
    modulesByID.emplace(id, p);
    return *p;
}
