#include "runtime.h"

#include <functional>
#include <iostream>
#include "opcode.h"

void Fin::Runtime::execute()
{
    pc = 0;
    fp = 0;

    while (true)
    {
        auto op = static_cast<Opcode>(instrs[pc]);
        ++pc;

        switch (op)
        {
            case Opcode::decl:
                {
                    std::string name = "<not implemented>";
                    auto argSize = readConst<uint16_t>();
                    auto localSize = readConst<uint16_t>();
                    auto len = readConst<uint32_t>();
                    methods.emplace_back(name, pc, argSize, localSize);
                    pc += len;
                }
                continue;

            case Opcode::call:
                {
                    auto idx = readConst<uint16_t>();
                    auto method = methods.at(idx);

                    // store current frame
                    opStack.push(idx);
                    opStack.push(pc);
                    opStack.push(fp);

                    // update frame
                    fp = opStack.size();
                    pc = method.location;
                    opStack.resize(opStack.size() + method.localSize);
                }
                continue;

            case Opcode::ret:
                {
                    auto idx = opStack.pop<uint16_t>();
                    auto method = methods.at(idx);

                    // restore previous frame
                    opStack.resize(fp);
                    opStack.pop(fp);
                    opStack.pop(pc);

                    opStack.resize(opStack.size() - method.argSize);
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

            case Opcode::print_i:
                std::cout << opStack.pop<int32_t>() << std::endl;
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
    execute();
}
