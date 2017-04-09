#ifndef __RUNTIME_H__
#define __RUNTIME_H__

#include <iosfwd>
#include <vector>
#include "stack.h"

namespace Fin
{
    class Runtime
    {
        Stack opStack;
        std::vector<char> instrs;
        size_t pc;

        template<typename T> void loadConst() noexcept
        {
            opStack.push(*reinterpret_cast<T*>(&instrs[pc]));
            pc += sizeof(T) / sizeof(char);
        }

        template<typename Op> void binaryOp() noexcept
        {
            Op op;
            typename Op::first_argument_type op1;
            typename Op::second_argument_type op2;

            opStack.pop(op2);
            opStack.pop(op1);
            opStack.push(op(op1, op2));
        }

        void execute();
    public:
        void run(std::istream &src);
    };
}

#endif
