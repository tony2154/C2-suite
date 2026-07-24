#include "crypto.hpp"
#include <openssl/evp.h>
#include <openssl/aes.h>
#include <openssl/rand.h>
#include <openssl/sha.h>
#include <zlib.h>
#include <algorithm>
#include <random>
#include <sstream>
#include <iomanip>

namespace shadow_crypto {

std::string base64_encode(const std::vector<unsigned char>& data) {
    static const char* chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::string result;
    int val = 0, valb = -6;
    for (unsigned char c : data) {
        val = (val << 8) + c;
        valb += 8;
        while (valb >= 0) {
            result.push_back(chars[(val >> valb) & 0x3F]);
            valb -= 6;
        }
    }
    if (valb > -6) result.push_back(chars[((val << 8) >> (valb + 8)) & 0x3F]);
    while (result.size() % 4) result.push_back('=');
    return result;
}

std::vector<unsigned char> base64_decode(const std::string& data) {
    static const std::string chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    std::vector<unsigned char> result;
    std::vector<int> T(256, -1);
    for (int i = 0; i < 64; i++) T[chars[i]] = i;
    int val = 0, valb = -8;
    for (unsigned char c : data) {
        if (T[c] == -1) break;
        val = (val << 6) + T[c];
        valb += 6;
        if (valb >= 0) {
            result.push_back(char((val >> valb) & 0xFF));
            valb -= 8;
        }
    }
    return result;
}

std::vector<unsigned char> derive_key(const std::string& passphrase, 
                                      const std::vector<unsigned char>& salt) {
    std::vector<unsigned char> key(32);
    PKCS5_PBKDF2_HMAC(passphrase.c_str(), passphrase.length(),
                      salt.data(), salt.size(), 100000, EVP_sha256(), 32, key.data());
    return key;
}

std::string encrypt(const std::string& data, const std::string& passphrase) {
    std::vector<unsigned char> salt(16);
    RAND_bytes(salt.data(), salt.size());
    
    auto key = derive_key(passphrase, salt);
    std::vector<unsigned char> iv(16);
    RAND_bytes(iv.data(), iv.size());
    
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key.data(), iv.data());
    
    std::vector<unsigned char> ciphertext(data.size() + AES_BLOCK_SIZE);
    int len, ciphertext_len;
    EVP_EncryptUpdate(ctx, ciphertext.data(), &len, 
                      (unsigned char*)data.data(), data.size());
    ciphertext_len = len;
    EVP_EncryptFinal_ex(ctx, ciphertext.data() + len, &len);
    ciphertext_len += len;
    EVP_CIPHER_CTX_free(ctx);
    
    ciphertext.resize(ciphertext_len);
    
    // Combine: salt + iv + ciphertext
    std::vector<unsigned char> combined;
    combined.insert(combined.end(), salt.begin(), salt.end());
    combined.insert(combined.end(), iv.begin(), iv.end());
    combined.insert(combined.end(), ciphertext.begin(), ciphertext.end());
    
    return base64_encode(combined);
}

std::string decrypt(const std::string& data, const std::string& passphrase) {
    auto combined = base64_decode(data);
    if (combined.size() < 32) return "";
    
    std::vector<unsigned char> salt(combined.begin(), combined.begin() + 16);
    std::vector<unsigned char> iv(combined.begin() + 16, combined.begin() + 32);
    std::vector<unsigned char> ciphertext(combined.begin() + 32, combined.end());
    
    auto key = derive_key(passphrase, salt);
    
    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_DecryptInit_ex(ctx, EVP_aes_256_cbc(), NULL, key.data(), iv.data());
    
    std::vector<unsigned char> plaintext(ciphertext.size() + AES_BLOCK_SIZE);
    int len, plaintext_len;
    EVP_DecryptUpdate(ctx, plaintext.data(), &len, ciphertext.data(), ciphertext.size());
    plaintext_len = len;
    EVP_DecryptFinal_ex(ctx, plaintext.data() + len, &len);
    plaintext_len += len;
    EVP_CIPHER_CTX_free(ctx);
    
    return std::string((char*)plaintext.data(), plaintext_len);
}

std::string xor_encrypt(const std::string& data, const std::string& key) {
    std::string result = key;
    for (size_t i = 0; i < data.size(); i++) {
        result += data[i] ^ key[i % key.size()];
    }
    return base64_encode(std::vector<unsigned char>(result.begin(), result.end()));
}

std::string random_string(size_t length) {
    static const char chars[] = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789";
    std::random_device rd;
    std::mt19937 gen(rd());
    std::uniform_int_distribution<> dis(0, sizeof(chars) - 2);
    std::string result;
    for (size_t i = 0; i < length; i++) {
        result += chars[dis(gen)];
    }
    return result;
}

std::string polymorphic_encode(const std::string& data) {
    std::vector<std::string> layers = {"base64", "hex", "reverse"};
    std::random_device rd;
    std::mt19937 gen(rd());
    std::shuffle(layers.begin(), layers.end(), gen);
    
    std::string result = data;
    for (const auto& layer : layers) {
        if (layer == "base64") {
            result = base64_encode(std::vector<unsigned char>(result.begin(), result.end()));
        } else if (layer == "hex") {
            std::stringstream ss;
            for (unsigned char c : result) {
                ss << std::hex << std::setw(2) << std::setfill('0') << (int)c;
            }
            result = ss.str();
        } else if (layer == "reverse") {
            std::reverse(result.begin(), result.end());
        }
    }
    
    std::string metadata;
    for (size_t i = 0; i < layers.size(); i++) {
        if (i > 0) metadata += ",";
        metadata += layers[i];
    }
    
    std::string combined = metadata + ":" + result;
    return base64_encode(std::vector<unsigned char>(combined.begin(), combined.end()));
}

std::string polymorphic_decode(const std::string& data) {
    auto decoded = base64_decode(data);
    std::string combined(decoded.begin(), decoded.end());
    
    size_t pos = combined.find(':');
    if (pos == std::string::npos) return "";
    
    std::string metadata = combined.substr(0, pos);
    std::string content = combined.substr(pos + 1);
    
    std::vector<std::string> layers;
    std::stringstream ss(metadata);
    std::string layer;
    while (std::getline(ss, layer, ',')) {
        layers.push_back(layer);
    }
    
    for (auto it = layers.rbegin(); it != layers.rend(); ++it) {
        if (*it == "base64") {
            auto decoded = base64_decode(content);
            content = std::string(decoded.begin(), decoded.end());
        } else if (*it == "hex") {
            std::string result;
            for (size_t i = 0; i < content.length(); i += 2) {
                std::string byte = content.substr(i, 2);
                result += (char)std::stoi(byte, nullptr, 16);
            }
            content = result;
        } else if (*it == "reverse") {
            std::reverse(content.begin(), content.end());
        }
    }
    
    return content;
}

std::string compress(const std::string& data) {
    z_stream zs;
    memset(&zs, 0, sizeof(zs));
    deflateInit(&zs, Z_BEST_COMPRESSION);
    
    zs.next_in = (Bytef*)data.data();
    zs.avail_in = data.size();
    
    std::string out;
    char outbuffer[32768];
    do {
        zs.next_out = reinterpret_cast<Bytef*>(outbuffer);
        zs.avail_out = sizeof(outbuffer);
        deflate(&zs, Z_FINISH);
        out.append(outbuffer, sizeof(outbuffer) - zs.avail_out);
    } while (zs.avail_out == 0);
    
    deflateEnd(&zs);
    return base64_encode(std::vector<unsigned char>(out.begin(), out.end()));
}

std::string decompress(const std::string& data) {
    auto decoded = base64_decode(data);
    std::string compressed(decoded.begin(), decoded.end());
    
    z_stream zs;
    memset(&zs, 0, sizeof(zs));
    inflateInit(&zs);
    
    zs.next_in = (Bytef*)compressed.data();
    zs.avail_in = compressed.size();
    
    std::string out;
    char outbuffer[32768];
    do {
        zs.next_out = reinterpret_cast<Bytef*>(outbuffer);
        zs.avail_out = sizeof(outbuffer);
        inflate(&zs, Z_NO_FLUSH);
        out.append(outbuffer, sizeof(outbuffer) - zs.avail_out);
    } while (zs.avail_out == 0);
    
    inflateEnd(&zs);
    return out;
}

} // namespace shadow_crypto
