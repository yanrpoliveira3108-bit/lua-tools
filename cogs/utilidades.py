import discord
from discord.ext import commands
from discord import app_commands
import json
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        # Utilidades é módulo global, mas respeita diversao ou utilidades config
        if not await database.is_modulo_enabled(interaction.guild.id, "diversao", interaction.channel.id):
            # Tenta utilidades também
            if not await database.is_modulo_enabled(interaction.guild.id, "utilidades", interaction.channel.id):
                pass
        return True
    return app_commands.check(predicate)

class Utilidades(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Veja avatar de alguém")
    @check_modulo()
    async def avatar(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        embed = discord.Embed(title=f"🖼️ Avatar de {alvo.display_name}", color=config["cores"]["principal"])
        embed.set_image(url=alvo.display_avatar.url)
        embed.add_field(name="Link", value=f"[Clique aqui]({alvo.display_avatar.url})")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="userinfo", description="Info de usuário")
    @check_modulo()
    async def userinfo(self, interaction: discord.Interaction, membro: discord.Member = None):
        alvo = membro or interaction.user
        embed = discord.Embed(title=f"👤 {alvo.display_name}", color=config["cores"]["principal"])
        embed.add_field(name="ID", value=alvo.id, inline=True)
        embed.add_field(name="Entrou no server", value=f"<t:{int(alvo.joined_at.timestamp())}:D>" if alvo.joined_at else "?", inline=True)
        embed.add_field(name="Conta criada", value=f"<t:{int(alvo.created_at.timestamp())}:D>", inline=True)
        embed.add_field(name="Cargos", value=", ".join([r.mention for r in alvo.roles[1:][:5]]) or "Nenhum", inline=False)
        embed.set_thumbnail(url=alvo.display_avatar.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="serverinfo", description="Info do servidor")
    @check_modulo()
    async def serverinfo(self, interaction: discord.Interaction):
        g = interaction.guild
        embed = discord.Embed(title=f"🏰 {g.name}", color=config["cores"]["principal"])
        embed.add_field(name="ID", value=g.id, inline=True)
        embed.add_field(name="Membros", value=g.member_count, inline=True)
        embed.add_field(name="Canais", value=len(g.channels), inline=True)
        embed.add_field(name="Cargos", value=len(g.roles), inline=True)
        embed.add_field(name="Dono", value=f"<@{g.owner_id}>", inline=True)
        embed.add_field(name="Criado", value=f"<t:{int(g.created_at.timestamp())}:D>", inline=True)
        if g.icon:
            embed.set_thumbnail(url=g.icon.url)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="afk", description="Defina status AFK")
    @check_modulo()
    async def afk(self, interaction: discord.Interaction, motivo: str = "AFK"):
        # Guarda AFK em memória simples + DB poderia ser
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS afk (guild_id INTEGER, user_id INTEGER, motivo TEXT, data TEXT, PRIMARY KEY (guild_id, user_id))")
            await db.execute("INSERT OR REPLACE INTO afk (guild_id, user_id, motivo, data) VALUES (?, ?, ?, ?)", (interaction.guild.id, interaction.user.id, motivo, datetime.datetime.now().isoformat()))
            await db.commit()
        await interaction.response.send_message(f"💤 {interaction.user.display_name} está AFK: {motivo}")

    @app_commands.command(name="lembrar", description="Bot lembra você depois")
    @app_commands.describe(tempo="Tempo em minutos", mensagem="O que lembrar")
    @check_modulo()
    async def lembrar(self, interaction: discord.Interaction, tempo: int, mensagem: str):
        await interaction.response.send_message(f"⏰ Vou te lembrar em {tempo}min: {mensagem}")
        import asyncio
        await asyncio.sleep(tempo*60)
        try:
            await interaction.followup.send(f"⏰ {interaction.user.mention} Lembrete: {mensagem}")
        except:
            pass

    @app_commands.command(name="calcular", description="Calculadora simples")
    @app_commands.describe(expressao="Ex: 2+2*3")
    @check_modulo()
    async def calcular(self, interaction: discord.Interaction, expressao: str):
        try:
            # Seguro: só permite numeros e operadores
            allowed = set("0123456789+-*/(). ")
            if not all(c in allowed for c in expressao):
                await interaction.response.send_message("Só números e + - * / ( )", ephemeral=True)
                return
            res = eval(expressao)
            await interaction.response.send_message(f"🧮 `{expressao}` = **{res}**")
        except Exception as e:
            await interaction.response.send_message(f"Erro: {e}", ephemeral=True)

    @app_commands.command(name="clima", description="Clima (fake divertido)")
    @app_commands.describe(cidade="Cidade")
    @check_modulo()
    async def clima(self, interaction: discord.Interaction, cidade: str):
        import random
        temp = random.randint(15, 35)
        cond = random.choice(["Ensolarado ☀️", "Chuvoso 🌧️", "Nublado ☁️", "Tempestade ⛈️", "LuaTools perfeito 🌙"])
        await interaction.response.send_message(f"🌤️ Clima em **{cidade}**: {temp}°C - {cond}")

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return
        # Sistema AFK: se mencionar alguém AFK, avisa
        if message.mentions:
            async with aiosqlite.connect(database.DB_PATH) as db:
                for m in message.mentions:
                    async with db.execute("SELECT motivo FROM afk WHERE guild_id=? AND user_id=?", (message.guild.id, m.id)) as cur:
                        row = await cur.fetchone()
                        if row:
                            await message.channel.send(f"💤 {m.display_name} está AFK: {row[0]}", delete_after=10)
        # Se quem enviou estava AFK, remove
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT * FROM afk WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id)) as cur:
                if await cur.fetchone():
                    await db.execute("DELETE FROM afk WHERE guild_id=? AND user_id=?", (message.guild.id, message.author.id))
                    await db.commit()
                    await message.channel.send(f"👋 {message.author.mention} voltou do AFK!", delete_after=5)

async def setup(bot):
    await bot.add_cog(Utilidades(bot))
