#ifndef FIN_RUNTIME_H
#define FIN_RUNTIME_H

#include "allocator.h"
#include "stack.h"
#include "typedefs.h"
#include <iosfwd>
#include <map>
#include <memory>
#include <stack>
#include <vector>

namespace Fin
{
class Contract;
class Function;
class Library;
class LibraryID;
class Type;

class Runtime
{
public:
    Runtime();
    void load(std::istream &src);
    void run();
    Library &createLibrary(LibraryID id);
    Library &getLibrary(const LibraryID &id);
    std::string backtrace() const noexcept;
    Allocator &allocator() noexcept { return _alloc; }
    Stack &stack() noexcept { return _eval; }

private:
    struct Frame
    {
        Library *library{nullptr};
        Contract *contract{nullptr};
        Pc pc{0};
        Offset local;
        Offset param;
    };

    Allocator _alloc;
    Stack _eval;
    Frame _frame;

    std::deque<Frame> _frames;
    std::map<LibraryID, std::unique_ptr<Library>> _libraries;
    std::vector<std::uint8_t> _instrs;
    std::unique_ptr<Contract> _mainContract;

    void printFrame(std::ostream &out, const Frame &fr) const;
    std::string readStr();
    Pc readTarget();
    const Function &readFunction();
    const Type &readType();
    Contract &readContract();
    TypeInfo readSize();
    Offset readOffset();
    void jump(std::size_t target);
    void ret();
    void call(Contract &ctr);
    void finalizeCall();
    void checkLibrary();
    void checkContract();
    void execute();

    template <typename T>
    T readInt()
    {
        T val = 0;

        std::uint8_t byte;
        while ((byte = _instrs.at(_frame.pc++)) & 0b10000000)
            val = static_cast<T>(val << 7) | (byte & 0b01111111);

        val = static_cast<T>(val << 6) | (byte & 0b00111111);

        if (byte & 0b01000000)
            val = ~val;

        LOG(1) << ' ' << val;
        return val;
    }

    template <typename T>
    T readConst()
    {
        // FIXME: unaligned access
        auto addr = &_instrs.at(_frame.pc);
        jump(_frame.pc + sizeof(T));

        T val = *reinterpret_cast<T *>(addr);
        LOG(1) << ' ' << val;
        return val;
    }

    template <typename Op>
    void binaryOp()
    {
        auto op2 = _eval.pop<typename Op::second_argument_type>();
        auto op1 = _eval.pop<typename Op::first_argument_type>();
        _eval.push(Op{}(op1, op2));
    }
};
} // namespace Fin

#endif
