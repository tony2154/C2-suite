#ifndef CRYPTO_HPP
#define CRYPTO_HPP

#include <string>
#include <vector>

namespace shadow_crypto {
    // AES-256 encryption/decryption
    std::string encrypt(const std::string& data, const std::string& passphrase);
    std::string decrypt(const std::string& data, const std::string& passphrase);
    
    // Base64 encoding/decoding
    std::string base64_encode(const std::vector<unsigned char>& data);
    std::vector<unsigned char> base64_decode(const std::string& data);
    
    // XOR obfuscation
    std::string xor_encrypt(const std::string& data, const std::string& key);
    
    // Polymorphic encoding
    std::string polymorphic_encode(const std::string& data);
    std::string polymorphic_decode(const std::string& data);
    
    // Compression
    std::string compress(const std::string& data);
    std::string decompress(const std::string& data);
    
    // Random string generation
    std::string random_string(size_t length);
    
    // Key derivation (PBKDF2)
    std::vector<unsigned char> derive_key(const std::string& passphrase, 
                                          const std::vector<unsigned char>& salt);
}

#endif
