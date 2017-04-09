#include "runtime.h"

#include <functional>
#include <iostream>
#include "opcode.h"

void Fin::Runtime::execute()
{
    while (pc < instrs.size())
    {
        auto op = static_cast<Opcode>(instrs[pc]);
        ++pc;

        switch (op)
        {
            case Opcode::const_i:
                loadConst<int32_t>();
                break;
            case Opcode::add_i:
                binaryOp<std::plus<int32_t>>();
                break;
            case Opcode::sub_i:
                binaryOp<std::minus<int32_t>>();
                break;
            case Opcode::mult_i:
                binaryOp<std::multiplies<int32_t>>();
                break;
            case Opcode::div_i:
                binaryOp<std::divides<int32_t>>();
                break;
            case Opcode::print_i:
                {
                    int32_t val;
                    opStack.pop(val);
                    std::cout << val << std::endl;
                }
                break;
            default:
                throw std::runtime_error{"invalid opcode "
                    + std::to_string(static_cast<char>(op))};
        }
    }
}

void Fin::Runtime::run(std::istream &src)
{
    // instrs.assign(std::istreambuf_iterator<char>(src),
    //         std::istreambuf_iterator<char>());
    char c;
    while (src.get(c))
        instrs.emplace_back(c);
    execute();
}
