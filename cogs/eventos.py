import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import datetime
import random
import aiosqlite
import database
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

EVENTOS = config["eventos"]

class Eventos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.verifica_eventos.start()

    def cog_unload(self):
        self.verifica_eventos.cancel()

    @tasks.loop(minutes=1)
    async def verifica_eventos(self):
        # Remove expirados
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT guild_id, evento_id, fim FROM eventos_ativos") as cur:
                rows = await cur.fetchall()
                for guild_id, evento_id, fim in rows:
                    if fim:
                        try:
                            fim_dt = datetime.datetime.fromisoformat(fim)
                            if datetime.datetime.now() >= fim_dt:
                                await db.execute("DELETE FROM eventos_ativos WHERE guild_id=? AND evento_id=?", (guild_id, evento_id))
                                await db.commit()
                                # Avisa guild
                                guild = self.bot.get_guild(guild_id)
                                if guild:
                                    # Tenta achar canal geral
                                    for ch in guild.text_channels:
                                        if ch.permissions_for(guild.me).send_messages:
                                            try:
                                                await ch.send(f"⏰ Evento **{EVENTOS.get(evento_id,{}).get('nome',evento_id)}** acabou!")
                                            except:
                                                pass
                                            break
                        except:
                            pass

    @verifica_eventos.before_loop
    async def before_verifica(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="eventos", description="Veja eventos ativos na guild")
    async def eventos_ativos(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT evento_id, multiplicador, inicio, fim FROM eventos_ativos WHERE guild_id=?", (interaction.guild.id,)) as cur:
                rows = await cur.fetchall()
        
        if not rows:
            embed = discord.Embed(title="📅 Nenhum evento ativo", description="ADMs podem iniciar com `/iniciar-evento`\nEventos disponíveis:\n" + "\n".join([f"{info['emoji']} **{info['nome']}** - {info['multiplicador']}x - {info['duracao_min']}min" for info in EVENTOS.values()]), color=config["cores"]["evento"])
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        embed = discord.Embed(title="🎉 Eventos Ativos!", color=config["cores"]["evento"])
        for evento_id, mult, inicio, fim in rows:
            info = EVENTOS.get(evento_id, {"nome": evento_id, "emoji":"🎉"})
            try:
                fim_dt = datetime.datetime.fromisoformat(fim)
                fim_ts = int(fim_dt.timestamp())
                desc = f"{info['emoji']} **{info['nome']}** - {mult}x\nTermina <t:{fim_ts}:R>"
            except:
                desc = f"{info['emoji']} {info['nome']} - {mult}x"
            embed.add_field(name=info['nome'], value=desc, inline=False)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="iniciar-evento", description="[ADM] Inicie um evento na guild")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(evento="Qual evento", duracao_min="Duração custom em minutos (opcional)")
    @app_commands.choices(evento=[
        app_commands.Choice(name="🎉 Hora Feliz 2x Dinheiro", value="hora_feliz"),
        app_commands.Choice(name="🌧️ Chuva de Pokémon 3x", value="chuva_pokemon"),
        app_commands.Choice(name="👹 Invasão RPG 2x XP", value="invasao_monstros"),
        app_commands.Choice(name="💼 Bônus Trabalho 1.5x", value="bonus_trabalho"),
    ])
    async def iniciar_evento(self, interaction: discord.Interaction, evento: str, duracao_min: int = None):
        if evento not in EVENTOS:
            await interaction.response.send_message("Evento inválido!", ephemeral=True)
            return
        
        info = EVENTOS[evento]
        duracao = duracao_min or info["duracao_min"]
        agora = datetime.datetime.now()
        fim = agora + datetime.timedelta(minutes=duracao)
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO eventos_ativos (guild_id, evento_id, tipo, multiplicador, inicio, fim) VALUES (?, ?, ?, ?, ?, ?)",
                             (interaction.guild.id, evento, info.get("tipo", evento), info["multiplicador"], agora.isoformat(), fim.isoformat()))
            await db.commit()
        
        embed = discord.Embed(title=f"{info['emoji']} Evento iniciado!", description=f"**{info['nome']}**\nMultiplicador: **{info['multiplicador']}x**\nDuração: {duracao} min (até <t:{int(fim.timestamp())}:t>)", color=config["cores"]["evento"])
        embed.add_field(name="O que faz?", value={
            "hora_feliz": "Todo dinheiro ganho (trabalho, caçada, venda farm) vale 2x!",
            "chuva_pokemon": "Spawn de pokémon 3x mais frequente!",
            "invasao_monstros": "RPG dá 2x XP e dinheiro!",
            "bonus_trabalho": "Trabalhos pagam 1.5x mais!"
        }.get(evento, "Bônus especial"), inline=False)
        
        # Menciona @everyone? Não, melhor não. Avisa no embed
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="parar-evento", description="[ADM] Pare um evento")
    @app_commands.default_permissions(manage_guild=True)
    async def parar_evento(self, interaction: discord.Interaction, evento: str):
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("DELETE FROM eventos_ativos WHERE guild_id=? AND evento_id=?", (interaction.guild.id, evento))
            await db.commit()
        await interaction.response.send_message(f"⏹️ Evento `{evento}` parado!")

    async def get_multiplicador(self, guild_id, tipo_evento):
        """Helper para outros cogs checarem multiplicador"""
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT multiplicador FROM eventos_ativos WHERE guild_id=? AND (evento_id=? OR tipo=?)", (guild_id, tipo_evento, tipo_evento)) as cur:
                row = await cur.fetchone()
                return row[0] if row else 1.0
            # Também checa hora_feliz que afeta tudo
            async with db.execute("SELECT multiplicador FROM eventos_ativos WHERE guild_id=? AND evento_id='hora_feliz'", (guild_id,)) as cur:
                row = await cur.fetchone()
                if row:
                    return row[0]
        return 1.0

    @commands.Cog.listener()
    async def on_message(self, message):
        # Aumenta spawn durante chuva pokemon
        if message.author.bot or not message.guild:
            return
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT * FROM eventos_ativos WHERE guild_id=? AND evento_id='chuva_pokemon'", (message.guild.id,)) as cur:
                if await cur.fetchone():
                    # Durante chuva, dobra chance de spawn no cog pokemon
                    # O cog pokemon já vai lidar? Vamos só aumentar contador artificialmente
                    pass

async def setup(bot):
    await bot.add_cog(Eventos(bot))
