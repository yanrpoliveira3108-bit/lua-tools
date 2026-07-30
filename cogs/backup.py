import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
import shutil
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

class BackupSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.backup_auto.start()

    def cog_unload(self):
        self.backup_auto.cancel()

    @tasks.loop(hours=1)
    async def backup_auto(self):
        # Backup automático a cada 1h
        try:
            if os.path.exists(database.DB_PATH):
                os.makedirs("backups", exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
                dest = f"backups/database_backup_{timestamp}.db"
                # Mantém só últimos 10 backups
                backups = sorted([f for f in os.listdir("backups") if f.startswith("database_backup_")])
                if len(backups) >= 10:
                    for old in backups[:-9]:
                        try:
                            os.remove(os.path.join("backups", old))
                        except:
                            pass
                shutil.copy2(database.DB_PATH, dest)
                print(f"[BACKUP] Auto backup criado: {dest} - {TAG}")
        except Exception as e:
            print(f"[BACKUP] Erro auto backup: {e}")

    @backup_auto.before_loop
    async def before_backup(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="backup", description=f"[DONO] Crie backup manual do banco - {TAG}")
    @app_commands.default_permissions(administrator=True)
    async def backup_manual(self, interaction: discord.Interaction):
        owner_id = os.getenv("OWNER_ID")
        if owner_id and str(interaction.user.id) != str(owner_id) and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(f"❌ Só dono {TAG} ou ADM!", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        try:
            if not os.path.exists(database.DB_PATH):
                await interaction.followup.send("❌ Banco não existe ainda!", ephemeral=True)
                return
            
            os.makedirs("backups", exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            dest = f"backups/database_backup_manual_{timestamp}.db"
            shutil.copy2(database.DB_PATH, dest)
            
            # Stats do banco
            async with aiosqlite.connect(database.DB_PATH) as db:
                stats = {}
                for table in ["economia","rpg_users","pokemon_users","casamentos","casas","farm_users","inventario"]:
                    try:
                        async with db.execute(f"SELECT COUNT(*) FROM {table}") as cur:
                            row = await cur.fetchone()
                            stats[table] = row[0] if row else 0
                    except:
                        stats[table] = 0
            
            embed = discord.Embed(title="✅ Backup Criado!", description=f"Arquivo: `{dest}`\n\n**Dados salvos (não perde mais!):**\n💸 Economia: {stats.get('economia',0)} users\n⚔️ RPG: {stats.get('rpg_users',0)}\n🔮 Pokémon: {stats.get('pokemon_users',0)}\n💍 Casamentos: {stats.get('casamentos',0)}\n🏠 Casas: {stats.get('casas',0)}\n⛏️ Farm: {stats.get('farm_users',0)}\n🎒 Itens: {stats.get('inventario',0)}\n\n{MARCA}", color=config["cores"]["sucesso"])
            embed.set_footer(text=f"{MARCA} | Backups automáticos a cada 1h, mantém últimos 10")
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro backup: {e}", ephemeral=True)

    @app_commands.command(name="backups-lista", description="Liste backups disponíveis")
    @app_commands.default_permissions(administrator=True)
    async def backups_lista(self, interaction: discord.Interaction):
        if not os.path.exists("backups"):
            await interaction.response.send_message("Nenhum backup ainda! Backups automáticos a cada 1h.", ephemeral=True)
            return
        
        files = sorted([f for f in os.listdir("backups") if f.endswith(".db")], reverse=True)
        if not files:
            await interaction.response.send_message("Nenhum backup!", ephemeral=True)
            return
        
        desc = ""
        for fname in files[:10]:
            fpath = os.path.join("backups", fname)
            size = os.path.getsize(fpath) / 1024
            mtime = datetime.datetime.fromtimestamp(os.path.getmtime(fpath)).strftime("%d/%m %H:%M")
            desc += f"`{fname}` - {size:.1f}KB - {mtime}\n"
        
        embed = discord.Embed(title="💾 Backups", description=desc, color=config["cores"]["principal"])
        embed.set_footer(text=f"{MARCA} | Use /backup-restaurar para restaurar (DONO)")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="exportar-dados", description="Exporte seus dados de casamento, economia, pokemons")
    async def exportar_dados(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        try:
            async with aiosqlite.connect(database.DB_PATH) as db:
                # Economia
                async with db.execute("SELECT carteira, banco FROM economia WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    econ = await cur.fetchone()
                # RPG
                async with db.execute("SELECT classe, nivel, xp FROM rpg_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    rpg = await cur.fetchone()
                # Pokemons
                async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                    poke_row = await cur.fetchone()
                # Casamento
                async with db.execute("SELECT user2_id FROM casamentos WHERE guild_id=? AND (user1_id=? OR user2_id=?)", (interaction.guild.id, interaction.user.id, interaction.user.id)) as cur:
                    cas = await cur.fetchone()
                
                import json as js
                dados = {
                    "user_id": interaction.user.id,
                    "guild_id": interaction.guild.id,
                    "economia": {"carteira": econ[0] if econ else 0, "banco": econ[1] if econ else 0},
                    "rpg": {"classe": rpg[0] if rpg else None, "nivel": rpg[1] if rpg else 0, "xp": rpg[2] if rpg else 0} if rpg else None,
                    "pokemons_count": len(js.loads(poke_row[0])) if poke_row else 0,
                    "casado_com": cas[0] if cas else None,
                    "exportado_em": datetime.datetime.now().isoformat(),
                    "marca": MARCA
                }
            
            casado_txt = f"<@{dados['casado_com']}>" if dados['casado_com'] else "Solteiro"
            embed = discord.Embed(title="📤 Seus Dados", description=f"**Economia:** {dados['economia']['carteira']} carteira + {dados['economia']['banco']} banco\n**RPG:** {dados['rpg']}\n**Pokémons:** {dados['pokemons_count']}\n**Casado com:** {casado_txt}\n\nSeus dados NUNCA são apagados em atualizações! Backup automático a cada 1h em backups/\n{MARCA}", color=config["cores"]["principal"])
            await interaction.followup.send(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Erro: {e}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BackupSystem(bot))
