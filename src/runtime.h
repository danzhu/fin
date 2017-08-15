#ifndef FIN_RUNTIME_H
#define FIN_RUNTIME_H

#include <iosfwd>
#include <map>
#include <memory>
#include <stack>
#include <vector>
#include "allocator.h"
#include "frame.h"
#include "library.h"
#include "log.h"
#include "stack.h"
#include "typedefs.h"

namespace Fin
{
    struct Contract;
    struct Function;
    struct Library;
    struct Type;

    class Runtime
    {
        Stack opStack;
        Allocator alloc;
        Frame frame;
        Ptr stackPtr;
        std::deque<Frame> rtStack;
        std::map<LibraryID, std::unique_ptr<Library>> libraries;
        std::vector<char> instrs;
        std::unique_ptr<Contract> mainContract;

        std::string readStr();
        Pc readTarget();
        Function &readFunction();
        Type &readType();
        Contract &readContract();
        TypeInfo readSize();
        Offset readOffset();
        void jump(std::size_t target);
        void ret();
        void call(Contract &ctr);
        void sign();
        void checkLibrary();
        void checkContract();
        void execute();

        template<typename T> T readInt()
        {
            T val = 0;

            char byte;
            while ((byte = instrs.at(frame.pc++)) & 0b10000000)
                val = static_cast<T>(val << 7) | (byte & 0b01111111);

            val = static_cast<T>(val << 6) | (byte & 0b00111111);

            if (byte & 0b01000000)
                val = ~val;

            LOG(1) << ' ' << val;
            return val;
        }

        template<typename T> T readConst()
        {
            // FIXME: unaligned access
            auto addr = &instrs.at(frame.pc);
            jump(frame.pc + sizeof(T));

            T val = *reinterpret_cast<T*>(addr);
            LOG(1) << ' ' << val;
            return val;
        }

        template<typename Op> void binaryOp()
        {
            auto op2 = opStack.pop<typename Op::second_argument_type>();
            auto op1 = opStack.pop<typename Op::first_argument_type>();
            opStack.push(Op{}(op1, op2));
        }
    public:
        Runtime(Size stackSize);
        void load(std::istream &src);
        void run();
        Library &createLibrary(const LibraryID &id);
        Library &getLibrary(const LibraryID &id);
        void backtrace(std::ostream &out) const noexcept;
        Allocator &allocator() noexcept { return alloc; }
        Stack &stack() noexcept { return opStack; }
    };
}

#endif
