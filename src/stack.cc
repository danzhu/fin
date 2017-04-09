#include "stack.h"

Fin::Stack::Stack(uint32_t cap): _content{new char[cap]}, _cap{cap} {}

Fin::Stack::~Stack()
{
    delete[] _content;
}
