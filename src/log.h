#ifndef FIN_LOG_H
#define FIN_LOG_H

#ifdef DEBUG
#define LOG(val) std::cerr << val
#else
#define LOG(val)
#endif

#endif
