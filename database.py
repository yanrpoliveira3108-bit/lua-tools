import aiosqlite
import json

DB_PATH = "database.db"

async def init_db():
    # BACKUP AUTOMÁTICO ANTES DE QUALQUER COISA - yna.019 anti-perda
    try:
        import os, shutil, datetime
        if os.path.exists(DB_PATH):
            os.makedirs("backups", exist_ok=True)
            # Só faz backup se o DB tem mais de 1 minuto desde último backup pra não spam
            backups = sorted([os.path.join("backups", f) for f in os.listdir("backups") if f.startswith("database_backup_")] if os.path.exists("backups") else [])
            should_backup = True
            if backups:
                last_backup = max(backups, key=os.path.getmtime)
                age = (datetime.datetime.now().timestamp() - os.path.getmtime(last_backup)) / 60
                if age < 10:  # Se último backup tem menos de 10min, não faz novo
                    should_backup = False
            if should_backup:
                ts = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                dst = f"backups/database_backup_auto_{ts}.db"
                shutil.copy2(DB_PATH, dst)
                print(f"[BACKUP] Backup pré-init criado: {dst} - yna.019")
                # Limpa antigos, mantém 15
                all_backups = sorted([os.path.join("backups", f) for f in os.listdir("backups") if f.startswith("database_backup_")], key=os.path.getmtime)
                if len(all_backups) > 15:
                    for old in all_backups[:-15]:
                        try:
                            os.remove(old)
                        except:
                            pass
    except Exception as e:
        print(f"[BACKUP] Erro backup pré-init: {e}")

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS economia (
                user_id INTEGER,
                guild_id INTEGER,
                carteira INTEGER DEFAULT 0,
                banco INTEGER DEFAULT 0,
                last_daily TEXT,
                last_work TEXT,
                total_trabalhos INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                user_id INTEGER,
                guild_id INTEGER,
                item_id TEXT,
                quantidade INTEGER DEFAULT 0,
                tipo TEXT DEFAULT 'geral',
                PRIMARY KEY (user_id, guild_id, item_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS trabalhos_users (
                user_id INTEGER,
                guild_id INTEGER,
                job_id TEXT,
                nivel INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS rpg_users (
                user_id INTEGER,
                guild_id INTEGER,
                classe TEXT,
                nivel INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                vida INTEGER DEFAULT 100,
                vida_max INTEGER DEFAULT 100,
                ataque INTEGER DEFAULT 10,
                defesa INTEGER DEFAULT 5,
                inventario TEXT DEFAULT '[]',
                equipamentos TEXT DEFAULT '{}',
                buffs TEXT DEFAULT '{}',
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_users (
                user_id INTEGER,
                guild_id INTEGER,
                pokemons TEXT DEFAULT '[]',
                pokemons_time TEXT DEFAULT '{}',
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_spawns (
                guild_id INTEGER,
                channel_id INTEGER,
                pokemon_nome TEXT,
                pokemon_id INTEGER,
                raridade TEXT DEFAULT 'comum',
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS modulos_config (
                guild_id INTEGER,
                modulo TEXT,
                channel_id INTEGER,
                habilitado INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, modulo, channel_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS guild_config (
                guild_id INTEGER PRIMARY KEY,
                economia_enabled INTEGER DEFAULT 1,
                rpg_enabled INTEGER DEFAULT 1,
                pokemon_enabled INTEGER DEFAULT 1,
                diversao_enabled INTEGER DEFAULT 1,
                familia_enabled INTEGER DEFAULT 1,
                casa_enabled INTEGER DEFAULT 1,
                farm_enabled INTEGER DEFAULT 1,
                eventos_enabled INTEGER DEFAULT 1,
                utilidades_enabled INTEGER DEFAULT 1,
                moderacao_enabled INTEGER DEFAULT 1,
                prefix TEXT DEFAULT '!'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS message_counter (
                guild_id INTEGER,
                channel_id INTEGER,
                count INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, channel_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS casamentos (
                guild_id INTEGER,
                user1_id INTEGER,
                user2_id INTEGER,
                data TEXT,
                anel_tipo TEXT DEFAULT 'anel_casamento',
                PRIMARY KEY (guild_id, user1_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS casamentos_pedidos (
                guild_id INTEGER,
                de_id INTEGER,
                para_id INTEGER,
                data TEXT,
                PRIMARY KEY (guild_id, de_id, para_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS filhos (
                guild_id INTEGER,
                filho_id INTEGER PRIMARY KEY,
                parent1_id INTEGER,
                parent2_id INTEGER,
                nome TEXT,
                nascimento TEXT
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cargos_loja (
                guild_id INTEGER,
                cargo_id INTEGER,
                preco INTEGER,
                duracao_dias INTEGER,
                tipo TEXT,
                PRIMARY KEY (guild_id, cargo_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS cargos_users (
                guild_id INTEGER,
                user_id INTEGER,
                cargo_id INTEGER,
                expira TEXT,
                PRIMARY KEY (guild_id, user_id, cargo_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS casas (
                user_id INTEGER,
                guild_id INTEGER,
                nivel INTEGER DEFAULT 0,
                conforto INTEGER DEFAULT 0,
                moveis TEXT DEFAULT '{}',
                ultima_coleta TEXT,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS farm_users (
                user_id INTEGER,
                guild_id INTEGER,
                nivel INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0,
                ferramenta TEXT DEFAULT 'picareta_madeira',
                recursos TEXT DEFAULT '{}',
                last_farm TEXT,
                total_minerado INTEGER DEFAULT 0,
                PRIMARY KEY (user_id, guild_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS eventos_ativos (
                guild_id INTEGER,
                evento_id TEXT,
                tipo TEXT,
                multiplicador REAL,
                inicio TEXT,
                fim TEXT,
                PRIMARY KEY (guild_id, evento_id)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pokemon_batalhas (
                guild_id INTEGER,
                canal_id INTEGER,
                desafiante_id INTEGER,
                oponente_id INTEGER,
                pokemon_desafiante TEXT,
                pokemon_oponente TEXT,
                status TEXT DEFAULT 'pendente',
                PRIMARY KEY (guild_id, desafiante_id, oponente_id)
            )
        """)
        # ===== NOVO SISTEMA DE TICS E PINGS =====
        await db.execute("""
            CREATE TABLE IF NOT EXISTS spawn_tics (
                guild_id INTEGER,
                channel_id INTEGER,
                modulo TEXT,
                mensagens INTEGER DEFAULT 20,
                tempo_seg INTEGER DEFAULT 300,
                chance INTEGER DEFAULT 20,
                PRIMARY KEY (guild_id, channel_id, modulo)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS pings_config (
                guild_id INTEGER,
                channel_id INTEGER,
                modulo TEXT,
                role_id INTEGER,
                habilitado INTEGER DEFAULT 1,
                PRIMARY KEY (guild_id, channel_id, modulo)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS mundo_spawns (
                guild_id INTEGER,
                channel_id INTEGER,
                tipo TEXT,
                dados TEXT,
                expira TEXT,
                PRIMARY KEY (guild_id, channel_id, tipo)
            )
        """)

        # Migrações
        migrations = [
            "ALTER TABLE rpg_users ADD COLUMN vida_max INTEGER DEFAULT 100",
            "ALTER TABLE rpg_users ADD COLUMN equipamentos TEXT DEFAULT '{}'",
            "ALTER TABLE rpg_users ADD COLUMN buffs TEXT DEFAULT '{}'",
            "ALTER TABLE economia ADD COLUMN total_trabalhos INTEGER DEFAULT 0",
            "ALTER TABLE pokemon_spawns ADD COLUMN raridade TEXT DEFAULT 'comum'",
            "ALTER TABLE pokemon_users ADD COLUMN pokemons_time TEXT DEFAULT '{}'",
            "ALTER TABLE guild_config ADD COLUMN familia_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_config ADD COLUMN casa_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_config ADD COLUMN farm_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_config ADD COLUMN eventos_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_config ADD COLUMN utilidades_enabled INTEGER DEFAULT 1",
            "ALTER TABLE guild_config ADD COLUMN moderacao_enabled INTEGER DEFAULT 1",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except:
                pass

        await db.commit()
    print("[DB V3] Banco Lua Tools yna.019 - 18 tabelas (inclui spawn_tics, pings, mundo_spawns) + migrações OK!")

async def get_economia(user_id, guild_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT carteira, banco FROM economia WHERE user_id=? AND guild_id=?", (user_id, guild_id)) as cur:
            row = await cur.fetchone()
            if row:
                return {"carteira": row[0], "banco": row[1]}
            else:
                await db.execute("INSERT INTO economia (user_id, guild_id, carteira, banco) VALUES (?, ?, 1000, 0)", (user_id, guild_id))
                await db.commit()
                return {"carteira": 1000, "banco": 0}

async def get_inventario(user_id, guild_id, tipo=None):
    async with aiosqlite.connect(DB_PATH) as db:
        if tipo:
            async with db.execute("SELECT item_id, quantidade FROM inventario WHERE user_id=? AND guild_id=? AND tipo=?", (user_id, guild_id, tipo)) as cur:
                rows = await cur.fetchall()
                return {item: qtd for item, qtd in rows}
        else:
            async with db.execute("SELECT item_id, quantidade, tipo FROM inventario WHERE user_id=? AND guild_id=?", (user_id, guild_id)) as cur:
                rows = await cur.fetchall()
                return rows

async def add_item(user_id, guild_id, item_id, quantidade, tipo="geral"):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantidade FROM inventario WHERE user_id=? AND guild_id=? AND item_id=?", (user_id, guild_id, item_id)) as cur:
            row = await cur.fetchone()
            if row:
                await db.execute("UPDATE inventario SET quantidade = quantidade + ? WHERE user_id=? AND guild_id=? AND item_id=?", (quantidade, user_id, guild_id, item_id))
            else:
                await db.execute("INSERT INTO inventario (user_id, guild_id, item_id, quantidade, tipo) VALUES (?, ?, ?, ?, ?)", (user_id, guild_id, item_id, quantidade, tipo))
        await db.commit()

async def remove_item(user_id, guild_id, item_id, quantidade):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantidade FROM inventario WHERE user_id=? AND guild_id=? AND item_id=?", (user_id, guild_id, item_id)) as cur:
            row = await cur.fetchone()
            if not row or row[0] < quantidade:
                return False
            nova_qtd = row[0] - quantidade
            if nova_qtd <= 0:
                await db.execute("DELETE FROM inventario WHERE user_id=? AND guild_id=? AND item_id=?", (user_id, guild_id, item_id))
            else:
                await db.execute("UPDATE inventario SET quantidade=? WHERE user_id=? AND guild_id=? AND item_id=?", (nova_qtd, user_id, guild_id, item_id))
            await db.commit()
            return True

async def has_item(user_id, guild_id, item_id, quantidade=1):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT quantidade FROM inventario WHERE user_id=? AND guild_id=? AND item_id=?", (user_id, guild_id, item_id)) as cur:
            row = await cur.fetchone()
            return row and row[0] >= quantidade

async def is_modulo_enabled(guild_id, modulo, channel_id):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT habilitado FROM modulos_config WHERE guild_id=? AND modulo=? AND channel_id=?", (guild_id, modulo, channel_id)) as cur:
            row = await cur.fetchone()
            if row:
                return bool(row[0])
        mod_check = modulo
        if modulo in ["utilidades", "jogos"]:
            mod_check = "diversao"
        try:
            async with db.execute(f"SELECT {mod_check}_enabled FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    return bool(row[0])
        except:
            pass
        return True

async def set_modulo_config(guild_id, modulo, channel_id, habilitado):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO modulos_config (guild_id, modulo, channel_id, habilitado) VALUES (?, ?, ?, ?)", (guild_id, modulo, channel_id, 1 if habilitado else 0))
        await db.commit()

async def get_modulos_status(guild_id):
    modulos = ["economia", "rpg", "pokemon", "familia", "casa", "farm", "eventos", "diversao", "utilidades", "moderacao"]
    result = {}
    async with aiosqlite.connect(DB_PATH) as db:
        for modulo in modulos:
            result[modulo] = {"global": True, "canais": {}}
            try:
                col = modulo
                if modulo == "utilidades":
                    col = "diversao"
                async with db.execute(f"SELECT {col}_enabled FROM guild_config WHERE guild_id=?", (guild_id,)) as cur:
                    row = await cur.fetchone()
                    if row:
                        result[modulo]["global"] = bool(row[0])
            except:
                pass
            try:
                async with db.execute("SELECT channel_id, habilitado FROM modulos_config WHERE guild_id=? AND modulo=?", (guild_id, modulo)) as cur:
                    rows = await cur.fetchall()
                    for ch_id, hab in rows:
                        result[modulo]["canais"][ch_id] = bool(hab)
            except:
                pass
    return result

# ===== FUNÇÕES TICS E PINGS =====
async def get_spawn_tic(guild_id, channel_id, modulo):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT mensagens, tempo_seg, chance FROM spawn_tics WHERE guild_id=? AND channel_id=? AND modulo=?", (guild_id, channel_id, modulo)) as cur:
            row = await cur.fetchone()
            if row:
                return {"mensagens": row[0], "tempo_seg": row[1], "chance": row[2]}
        # Tenta global do modulo nesta guild
        async with db.execute("SELECT mensagens, tempo_seg, chance FROM spawn_tics WHERE guild_id=? AND channel_id=0 AND modulo=?", (guild_id, 0, modulo)) as cur:
            row = await cur.fetchone()
            if row:
                return {"mensagens": row[0], "tempo_seg": row[1], "chance": row[2]}
    return None

async def set_spawn_tic(guild_id, channel_id, modulo, mensagens, tempo_seg, chance):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO spawn_tics (guild_id, channel_id, modulo, mensagens, tempo_seg, chance) VALUES (?, ?, ?, ?, ?, ?)", (guild_id, channel_id, modulo, mensagens, tempo_seg, chance))
        await db.commit()

async def get_ping_role(guild_id, channel_id, modulo):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT role_id FROM pings_config WHERE guild_id=? AND channel_id=? AND modulo=? AND habilitado=1", (guild_id, channel_id, modulo)) as cur:
            row = await cur.fetchone()
            if row:
                return row[0]
        async with db.execute("SELECT role_id FROM pings_config WHERE guild_id=? AND channel_id=0 AND modulo=? AND habilitado=1", (guild_id, 0, modulo)) as cur:
            row = await cur.fetchone()
            if row:
                return row[0]
    return None

async def set_ping_role(guild_id, channel_id, modulo, role_id):
    async with aiosqlite.connect(DB_PATH) as db:
        if role_id is None:
            await db.execute("DELETE FROM pings_config WHERE guild_id=? AND channel_id=? AND modulo=?", (guild_id, channel_id, modulo))
        else:
            await db.execute("INSERT OR REPLACE INTO pings_config (guild_id, channel_id, modulo, role_id, habilitado) VALUES (?, ?, ?, ?, 1)", (guild_id, channel_id, modulo, role_id))
        await db.commit()
