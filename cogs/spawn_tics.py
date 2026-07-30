import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import datetime
import aiosqlite
import database
import asyncio

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

class SpawnTics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Cache de contadores por canal/modulo
        self.counters = {}  # (guild_id, channel_id, modulo) -> count
        self.last_spawn_time = {}  # (guild_id, channel_id, modulo) -> datetime

    @app_commands.command(name="configurar-ticks", description=f"[ADM] Configure tempo de spawn (tics) - {TAG}")
    @app_commands.describe(
        modulo="Qual sistema? pokemon, rpg, dungeon, loot, farm",
        canal="Canal (vazio = global guild)",
        mensagens="Msgs necessárias pra spawn (ex: 15)",
        tempo="Tempo mínimo em segundos entre spawns (ex: 120)",
        chance="Chance % de spawn quando atinge tic (1-100)"
    )
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        app_commands.Choice(name="⛏️ Farm Veios", value="farm"),
        app_commands.Choice(name="🎉 Evento Aleatório", value="evento"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def configurar_ticks(self, interaction: discord.Interaction, modulo: str, mensagens: int = 20, tempo: int = 180, chance: int = 25, canal: discord.TextChannel = None):
        if mensagens < 1 or mensagens > 500:
            await interaction.response.send_message("Mensagens deve ser 1-500", ephemeral=True)
            return
        if tempo < 10 or tempo > 3600:
            await interaction.response.send_message("Tempo deve ser 10-3600s", ephemeral=True)
            return
        if chance < 1 or chance > 100:
            await interaction.response.send_message("Chance 1-100", ephemeral=True)
            return
        
        channel_id = canal.id if canal else 0
        await database.set_spawn_tic(interaction.guild.id, channel_id, modulo, mensagens, tempo, chance)
        
        embed = discord.Embed(title=f"⏱️ Tics Configurados - {modulo.upper()}", description=f"**Módulo:** {modulo}\n**Canal:** {canal.mention if canal else '🌐 Global (toda guild)'}\n**Msgs pra spawn:** {mensagens}\n**Tempo mínimo:** {tempo}s ({tempo//60}min)\n**Chance:** {chance}%\n\n{message_ := ''}", color=config["cores"]["principal"])
        # Explicação
        embed.add_field(name="Como funciona?", value=f"A cada {mensagens} msgs no canal + {tempo}s de cooldown, tem {chance}% de spawnar {modulo}.\nUse `/pings` pra ver status completo.", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="configurar-ping", description=f"[ADM] Configure cargo pingado no spawn - {TAG}")
    @app_commands.describe(
        modulo="Qual spawn pinga?",
        cargo="Cargo a ser mencionado (vazio = remove ping)",
        canal="Canal (vazio = global)"
    )
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        app_commands.Choice(name="⛏️ Farm", value="farm"),
        app_commands.Choice(name="🎉 Todos spawns", value="todos"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def configurar_ping(self, interaction: discord.Interaction, modulo: str, cargo: discord.Role = None, canal: discord.TextChannel = None):
        channel_id = canal.id if canal else 0
        if modulo == "todos":
            for mod in ["pokemon","rpg","dungeon","loot","farm"]:
                await database.set_ping_role(interaction.guild.id, channel_id, mod, cargo.id if cargo else None)
            msg = f"Ping configurado para TODOS os módulos"
        else:
            await database.set_ping_role(interaction.guild.id, channel_id, modulo, cargo.id if cargo else None)
            msg = f"Ping {modulo} configurado"
        
        if cargo:
            embed = discord.Embed(title="🔔 Ping Configurado!", description=f"{msg}\n**Cargo:** {cargo.mention}\n**Canal:** {canal.mention if canal else 'Global'}\n**Módulo:** {modulo}\n\nAgora quando {modulo} spawnar, vai pingar {cargo.mention}!", color=config["cores"]["sucesso"])
        else:
            embed = discord.Embed(title="🔕 Ping Removido!", description=f"{msg} removido no canal {canal.mention if canal else 'global'}", color=config["cores"]["erro"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pings", description="Veja tics e pings configurados")
    async def pings_lista(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT channel_id, modulo, mensagens, tempo_seg, chance FROM spawn_tics WHERE guild_id=?", (guild_id,)) as cur:
                tics = await cur.fetchall()
            async with db.execute("SELECT channel_id, modulo, role_id FROM pings_config WHERE guild_id=? AND habilitado=1", (guild_id,)) as cur:
                pings = await cur.fetchall()
        
        embed = discord.Embed(title=f"⏱️🔔 Tics & Pings - {interaction.guild.name}", description=f"Configuração atual de spawns\nDev: {TAG} | {MARCA}", color=config["cores"]["principal"])
        
        if tics:
            txt=""
            for ch_id, mod, msgs, tempo, chance in tics:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                txt += f"{mod}: {ch_txt} - {msgs} msgs, {tempo}s, {chance}%\n"
            embed.add_field(name="⏱️ Tics Configurados", value=txt[:1024] or "Nenhum", inline=False)
        else:
            embed.add_field(name="⏱️ Tics", value="Padrão: Pokemon 20 msgs/180s/20%, RPG 25/300/15%, Dungeon 40/600/10%, Loot 30/400/20%\nUse `/configurar-ticks` pra mudar", inline=False)
        
        if pings:
            txt=""
            for ch_id, mod, role_id in pings:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                role = interaction.guild.get_role(role_id)
                role_txt = role.mention if role else f"ID {role_id}"
                txt += f"{mod}: {ch_txt} -> {role_txt}\n"
            embed.add_field(name="🔔 Pings Ativos", value=txt[:1024], inline=False)
        else:
            embed.add_field(name="🔔 Pings", value="Nenhum ping configurado.\nUse `/configurar-ping modulo:pokemon cargo:@Cargo`", inline=False)
        
        embed.add_field(name="💡 Comandos ADM", value="`/configurar-ticks modulo:pokemon mensagens:10 tempo:60 chance:50 canal:#pokemon`\n`/configurar-ping modulo:pokemon cargo:@Caçadores canal:#pokemon`\n`/spawn-forcado modulo:dungeon canal:#geral`", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="testar-ping", description="[ADM] Teste se ping de cargo está funcionando")
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot", value="loot"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def testar_ping(self, interaction: discord.Interaction, modulo: str):
        role_id = await database.get_ping_role(interaction.guild.id, interaction.channel.id, modulo)
        if not role_id:
            role_id = await database.get_ping_role(interaction.guild.id, 0, modulo)
        
        if not role_id:
            await interaction.response.send_message(f"❌ Nenhum ping configurado para {modulo}! Use `/configurar-ping modulo:{modulo} cargo:@Cargo`", ephemeral=True)
            return
        
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Cargo ID {role_id} não existe mais!", ephemeral=True)
            return
        
        # Testa ping
        allowed = discord.AllowedMentions(roles=True)
        await interaction.response.send_message(f"🔔 Teste ping {modulo}: {role.mention} - Se você recebeu notificação, pings estão funcionando! | {MARCA}", allowed_mentions=allowed)
        # Também manda embed de teste
        embed = discord.Embed(title=f"🔔 Teste Ping - {modulo}", description=f"Cargo pingado: {role.mention}\nCanal: {interaction.channel.mention}\nSe apareceu notificação, tá OK!\nSe NÃO apareceu, verifique:\n1. Cargo não está silenciado?\n2. Bot tem permissão de mencionar cargos?\n3. Você tem o cargo? (Discord não notifica quem já tem cargo mutado)", color=config["cores"]["sucesso"])
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed, allowed_mentions=allowed)

    @app_commands.command(name="spawn-forcado", description="[ADM] Força spawn de algo")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG Mob", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot", value="loot"),
    ])
    async def spawn_forcado(self, interaction: discord.Interaction, modulo: str, canal: discord.TextChannel = None):
        canal_alvo = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        
        # Pega cog correspondente e força spawn
        if modulo == "pokemon":
            cog = self.bot.get_cog("Pokemon")
            if cog:
                await cog.spawn_pokemon(interaction.guild, canal_alvo)
                # Adiciona ping se configurado
                role_id = await database.get_ping_role(interaction.guild.id, canal_alvo.id, "pokemon") or await database.get_ping_role(interaction.guild.id, 0, "pokemon")
                ping_txt = f"<@&{role_id}> " if role_id else ""
                await interaction.followup.send(f"✅ Pokemon spawnado em {canal_alvo.mention} {ping_txt}", ephemeral=True)
            else:
                await interaction.followup.send("Cog Pokemon não encontrado", ephemeral=True)
        elif modulo == "rpg":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_mob(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Mob RPG spawnado em {canal_alvo.mention}", ephemeral=True)
            else:
                await interaction.followup.send("Cog Mundo não carregado", ephemeral=True)
        elif modulo == "dungeon":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_dungeon(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Dungeon spawnada em {canal_alvo.mention}", ephemeral=True)
        elif modulo == "loot":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_loot(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Baú spawnado em {canal_alvo.mention}", ephemeral=True)

    # Listener para contar mensagens e verificar tics
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        guild_id = message.guild.id
        channel_id = message.channel.id
        key_base = f"{guild_id}_{channel_id}"
        
        # Para cada modulo, verifica tic
        # Pokemon é tratado pelo seu próprio cog (pokemon.py) que já usa tics custom, então não duplicamos
        for modulo in ["rpg", "dungeon", "loot", "farm"]:
            tic = await database.get_spawn_tic(guild_id, channel_id, modulo)
            if not tic:
                tic = await database.get_spawn_tic(guild_id, 0, modulo)
            if not tic:
                # Usa padrão
                defaults = {"pokemon": {"mensagens":20,"tempo_seg":180,"chance":20},
                            "rpg": {"mensagens":25,"tempo_seg":300,"chance":15},
                            "dungeon": {"mensagens":40,"tempo_seg":600,"chance":10},
                            "loot": {"mensagens":30,"tempo_seg":400,"chance":20},
                            "farm": {"mensagens":20,"tempo_seg":200,"chance":25}}
                tic = defaults.get(modulo, {"mensagens":20,"tempo_seg":180,"chance":20})
            
            cache_key = (guild_id, channel_id, modulo)
            count = self.counters.get(cache_key, 0) + 1
            self.counters[cache_key] = count
            
            last = self.last_spawn_time.get(cache_key)
            if last:
                diff = (discord.utils.utcnow() - last).total_seconds()
                if diff < tic["tempo_seg"]:
                    continue  # Ainda em cooldown
            
            if count >= tic["mensagens"]:
                import random
                if random.randint(1,100) <= tic["chance"]:
                    # Spawn!
                    self.counters[cache_key] = 0
                    self.last_spawn_time[cache_key] = discord.utils.utcnow()
                    
                    # Dispara spawn conforme modulo
                    if modulo == "pokemon":
                        # Deixa o cog pokemon lidar, mas já resetamos contador
                        pass
                    elif modulo in ["rpg","dungeon","loot"]:
                        mundo = self.bot.get_cog("Mundo")
                        if mundo:
                            if modulo == "rpg":
                                await mundo.spawn_mob(message.guild, message.channel)
                            elif modulo == "dungeon":
                                await mundo.spawn_dungeon(message.guild, message.channel)
                            elif modulo == "loot":
                                await mundo.spawn_loot(message.guild, message.channel)

async def setup(bot):
    await bot.add_cog(SpawnTics(bot))
