#ifndef FIN_RUNTIME_H
#define FIN_RUNTIME_H

#include <iosfwd>
#include <map>
#include <memory>
#include <stack>
#include <vector>
#include "allocator.h"
#include "frame.h"
#include "function.h"
#include "module.h"
#include "stack.h"

namespace Fin
{
    class Runtime
    {
        Stack opStack;
        Allocator alloc;
        std::deque<Frame> rtStack;
        std::vector<std::unique_ptr<Module>> modules;
        std::map<ModuleID, Module *> modulesByID;
        std::vector<char> instrs;
        Module *execModule;
        const Function *execFunction;
        uint32_t pc;
        uint32_t fp;

        std::string readStr();
        void jump(int32_t target);
        void ret();
        void execute();
        void call(const Function &fn, uint16_t argSize);

        template<typename T> T readConst()
        {
            T val = *reinterpret_cast<T*>(&instrs.at(pc));
            jump(pc + sizeof(T));
            return val;
        }
        template<typename T> void readConst(T &val)
        {
            val = readConst<T>();
        }

        template<typename T> void loadConst()
        {
            opStack.push(readConst<T>());
        }

        template<typename Op> void binaryOp()
        {
            auto op2 = opStack.pop<typename Op::second_argument_type>();
            auto op1 = opStack.pop<typename Op::first_argument_type>();
            opStack.push(Op{}(op1, op2));
        }
    public:
        Runtime();
        void run(std::istream &src);
        Module &createModule(const std::string &name);
        Module &getModule(const std::string &name);
        void backtrace(std::ostream &out) const noexcept;
        uint32_t programCounter() const noexcept;
    };
}

#endif
