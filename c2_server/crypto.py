import base64
import json
import hashlib
import os
import random
import string
import zlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MASTER_PASSPHRASE = "ShadowC2_Lab_2026_Secret_Key"

def derive_key(passphrase, salt=None):
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key, salt

def encrypt_data(data, passphrase=MASTER_PASSPHRASE):
    key, salt = derive_key(passphrase)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(salt + encrypted).decode()

def decrypt_data(token, passphrase=MASTER_PASSPHRASE):
    try:
        decoded = base64.urlsafe_b64decode(token.encode())
        salt = decoded[:16]
        encrypted = decoded[16:]
        key, _ = derive_key(passphrase, salt)
        f = Fernet(key)
        return f.decrypt(encrypted).decode()
    except:
        return None

def polymorphic_encode(data):
    layers = ['base64', 'hex', 'rot13', 'reverse']
    random.shuffle(layers)
    result = data
    for layer in layers:
        if layer == 'base64':
            result = base64.b64encode(result.encode()).decode()
        elif layer == 'hex':
            result = result.encode().hex()
        elif layer == 'rot13':
            result = result.translate(str.maketrans('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz', 'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'))
        elif layer == 'reverse':
            result = result[::-1]
    return base64.b64encode(f"{','.join(layers)}:{result}".encode()).decode()

def polymorphic_decode(data):
    try:
        decoded = base64.b64decode(data).decode()
        metadata, content = decoded.split(':', 1)
        layers = metadata.split(',')
        for layer in reversed(layers):
            if layer == 'base64':
                content = base64.b64decode(content).decode()
            elif layer == 'hex':
                content = bytes.fromhex(content).decode()
            elif layer == 'rot13':
                content = content.translate(str.maketrans('NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm', 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))
            elif layer == 'reverse':
                content = content[::-1]
        return content
    except:
        return None

def compress_and_encrypt(data):
    compressed = zlib.compress(data.encode())
    return encrypt_data(base64.b64encode(compressed).decode())

def decrypt_and_decompress(data):
    decrypted = decrypt_data(data)
    if decrypted:
        compressed = base64.b64decode(decrypted)
        return zlib.decompress(compressed).decode()
    return None

def encrypt_command(command, passphrase=MASTER_PASSPHRASE):
    json_data = json.dumps(command)
    poly = polymorphic_encode(json_data)
    return encrypt_data(poly, passphrase)

def decrypt_command(encrypted, passphrase=MASTER_PASSPHRASE):
    poly = decrypt_data(encrypted, passphrase)
    if poly:
        json_data = polymorphic_decode(poly)
        if json_data:
            return json.loads(json_data)
    return None

def encrypt_response(data, passphrase=MASTER_PASSPHRASE):
    json_data = json.dumps(data)
    return compress_and_encrypt(json_data)

def decrypt_response(encrypted, passphrase=MASTER_PASSPHRASE):
    json_data = decrypt_and_decompress(encrypted)
    if json_data:
        return json.loads(json_data)
    return None
