from flask import Flask, render_template, request, redirect, url_for, jsonify
import aiosqlite
import asyncio
import json
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
import sqlite3

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json")

app = Flask(__name__)

with open(CONFIG_PATH, "r", encoding="utf-8") as f:
    config = json.load(f)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.route("/")
def index():
    db = get_db()
    try:
        cur = db.execute("SELECT guild_id FROM guild_config")
        guilds = cur.fetchall()
        # Também pega guilds que só tem modulos_config
        cur2 = db.execute("SELECT DISTINCT guild_id FROM modulos_config")
        guilds2 = cur2.fetchall()
        all_guilds = set([r["guild_id"] for r in guilds] + [r["guild_id"] for r in guilds2])
    except:
        all_guilds = []
    db.close()
    
    # Stats
    db = get_db()
    try:
        stats = {}
        cur = db.execute("SELECT COUNT(*) as total FROM economia")
        stats["usuarios_economia"] = cur.fetchone()["total"]
        cur = db.execute("SELECT COUNT(*) as total FROM rpg_users")
        stats["usuarios_rpg"] = cur.fetchone()["total"]
        cur = db.execute("SELECT COUNT(*) as total FROM pokemon_users")
        stats["treinadores"] = cur.fetchone()["total"]
        cur = db.execute("SELECT COUNT(*) as total FROM casamentos")
        stats["casamentos"] = cur.fetchone()["total"]
        cur = db.execute("SELECT COUNT(*) as total FROM casas WHERE nivel>0")
        stats["casas"] = cur.fetchone()["total"]
    except Exception as e:
        stats = {"erro": str(e)}
    db.close()
    
    return render_template("index.html", guilds=all_guilds, config=config, stats=stats)

@app.route("/guild/<int:guild_id>")
def guild_dashboard(guild_id):
    db = get_db()
    # Modulos status
    modulos = ["economia","rpg","pokemon","diversao","familia","casa","farm","eventos"]
    status = {}
    for modulo in modulos:
        status[modulo] = {"global": True, "canais": {}}
        try:
            cur = db.execute(f"SELECT {modulo}_enabled FROM guild_config WHERE guild_id=?", (guild_id,))
            row = cur.fetchone()
            if row:
                status[modulo]["global"] = bool(row[0])
        except:
            pass
        try:
            cur = db.execute("SELECT channel_id, habilitado FROM modulos_config WHERE guild_id=? AND modulo=?", (guild_id, modulo))
            for r in cur.fetchall():
                status[modulo]["canais"][r["channel_id"]] = bool(r["habilitado"])
        except:
            pass
    
    # Economia top
    try:
        cur = db.execute("SELECT user_id, carteira+banco as total FROM economia WHERE guild_id=? ORDER BY total DESC LIMIT 5", (guild_id,))
        top_ricos = cur.fetchall()
    except:
        top_ricos = []
    
    # Eventos ativos
    try:
        cur = db.execute("SELECT evento_id, multiplicador, fim FROM eventos_ativos WHERE guild_id=?", (guild_id,))
        eventos = cur.fetchall()
    except:
        eventos = []
    
    # Casamentos
    try:
        cur = db.execute("SELECT user1_id, user2_id, data FROM casamentos WHERE guild_id=?", (guild_id,))
        casamentos = cur.fetchall()
    except:
        casamentos = []
    
    db.close()
    return render_template("guild.html", guild_id=guild_id, status=status, config=config, top_ricos=top_ricos, eventos=eventos, casamentos=casamentos)

@app.route("/guild/<int:guild_id>/edit", methods=["POST"])
def edit_modulo(guild_id):
    data = request.form
    modulo = data.get("modulo")
    channel_id = data.get("channel_id")
    acao = data.get("acao")  # ativar/desativar/global
    
    db = get_db()
    if acao == "global_ativar" or acao == "global_desativar":
        habilitado = 1 if "ativar" in acao else 0
        try:
            db.execute("INSERT OR IGNORE INTO guild_config (guild_id) VALUES (?)", (guild_id,))
            db.execute(f"UPDATE guild_config SET {modulo}_enabled=? WHERE guild_id=?", (habilitado, guild_id))
            db.commit()
        except Exception as e:
            print(e)
    else:
        if not channel_id:
            return redirect(url_for("guild_dashboard", guild_id=guild_id))
        try:
            channel_id = int(channel_id)
            habilitado = 1 if acao=="ativar" else 0
            db.execute("INSERT OR REPLACE INTO modulos_config (guild_id, modulo, channel_id, habilitado) VALUES (?, ?, ?, ?)", (guild_id, modulo, channel_id, habilitado))
            db.commit()
        except Exception as e:
            print(e)
    db.close()
    return redirect(url_for("guild_dashboard", guild_id=guild_id))

@app.route("/api/guilds")
def api_guilds():
    db = get_db()
    try:
        cur = db.execute("SELECT * FROM guild_config")
        rows = [dict(r) for r in cur.fetchall()]
    except:
        rows = []
    db.close()
    return jsonify(rows)

@app.route("/api/modulos/<int:guild_id>")
def api_modulos(guild_id):
    db = get_db()
    result = {}
    modulos = ["economia","rpg","pokemon","diversao","familia","casa","farm","eventos"]
    for modulo in modulos:
        result[modulo] = {"global": True, "canais": {}}
        try:
            cur = db.execute(f"SELECT {modulo}_enabled FROM guild_config WHERE guild_id=?", (guild_id,))
            row = cur.fetchone()
            if row:
                result[modulo]["global"] = bool(row[0])
        except:
            pass
        cur = db.execute("SELECT channel_id, habilitado FROM modulos_config WHERE guild_id=? AND modulo=?", (guild_id, modulo))
        for r in cur.fetchall():
            result[modulo]["canais"][r["channel_id"]] = bool(r["habilitado"])
    db.close()
    return jsonify(result)

if __name__ == "__main__":
    print("🌙 Lua Tools Dashboard iniciado em http://localhost:5000")
    print("📊 Configure onde cada módulo é ativo pela web!")
    print("💡 Bot + Dashboard usam o mesmo database.db")
    app.run(host="0.0.0.0", port=5000, debug=True)
