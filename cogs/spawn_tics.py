import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import datetime
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

MARCA = config["dono"]["marca_dagua"]
TAG = config["dono"]["tag"]

class SpawnTics(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.counters = {}
        self.last_spawn_time = {}

    @app_commands.command(name="configurar-ticks", description=f"[ADM] Configure tempo de spawn (tics) - {TAG}")
    @app_commands.describe(
        modulo="Qual sistema? pokemon, rpg, dungeon, loot, farm",
        canal="Canal (vazio = global guild)",
        mensagens="Msgs necessárias (1-500)",
        tempo="Tempo mínimo segundos entre spawns (10-3600)",
        chance="Chance % (1-100)"
    )
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        app_commands.Choice(name="⛏️ Farm Veios", value="farm"),
    ])
    @app_commands.default_permissions(manage_guild=True)
    async def configurar_ticks(self, interaction: discord.Interaction, modulo: str, mensagens: int = 20, tempo: int = 180, chance: int = 25, canal: discord.TextChannel = None):
        if not (1 <= mensagens <= 500 and 10 <= tempo <= 3600 and 1 <= chance <= 100):
            await interaction.response.send_message("Valores inválidos! msgs 1-500, tempo 10-3600, chance 1-100", ephemeral=True)
            return
        channel_id = canal.id if canal else 0
        await database.set_spawn_tic(interaction.guild.id, channel_id, modulo, mensagens, tempo, chance)
        embed = discord.Embed(title=f"⏱️ Tics {modulo.upper()} Configurados!", description=f"**Módulo:** {modulo}\n**Canal:** {canal.mention if canal else '🌐 Global'}\n**Msgs:** {mensagens}\n**Tempo:** {tempo}s ({tempo//60}min)\n**Chance:** {chance}%\n\nUse `/pings` pra ver status.", color=config["cores"]["principal"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="configurar-ping", description=f"[ADM] Configure cargo pingado no spawn - {TAG}")
    @app_commands.describe(
        modulo="Qual spawn pinga?",
        cargo="Cargo a mencionar (vazio = remove)",
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
        guild = interaction.guild
        
        # Verifica permissão bot mencionar cargo
        if cargo:
            if cargo.position >= guild.me.top_role.position:
                await interaction.response.send_message(f"❌ Meu cargo é menor que {cargo.mention}! Suba meu cargo acima dele.", ephemeral=True)
                return
        
        if modulo == "todos":
            for mod in ["pokemon","rpg","dungeon","loot","farm"]:
                await database.set_ping_role(guild.id, channel_id, mod, cargo.id if cargo else None)
            msg = f"Ping para TODOS os módulos ({', '.join(['pokemon','rpg','dungeon','loot','farm'])})"
        else:
            await database.set_ping_role(guild.id, channel_id, modulo, cargo.id if cargo else None)
            msg = f"Ping {modulo}"
        
        if cargo:
            # Tenta deixar cargo mencionável temporariamente se não for
            if not cargo.mentionable:
                try:
                    await cargo.edit(mentionable=True, reason=f"Lua Tools ping config por {interaction.user}")
                except:
                    pass
            embed = discord.Embed(title="🔔 Ping Configurado!", description=f"{msg}\n**Cargo:** {cargo.mention}\n**Canal:** {canal.mention if canal else '🌐 Global'}\n**Módulo:** {modulo}\n\n✅ Agora quando {modulo} spawnar em {canal.mention if canal else 'qualquer canal da guild'}, vai pingar {cargo.mention}!\n\nTeste: `/testar-ping modulo:{modulo}`", color=config["cores"]["sucesso"])
        else:
            embed = discord.Embed(title="🔕 Ping Removido!", description=f"{msg} removido no {canal.mention if canal else 'global'}", color=config["cores"]["erro"])
        
        # Verifica se já existe tic configurado, se não, cria padrão
        tic = await database.get_spawn_tic(guild.id, channel_id, modulo) if modulo != "todos" else None
        if not tic and modulo != "todos":
            await database.set_spawn_tic(guild.id, channel_id, modulo, 20, 180, 25)
            embed.add_field(name="⏱️ Tic", value="Tic padrão criado (20 msgs, 180s, 25%). Use `/configurar-ticks` pra mudar", inline=False)
        
        embed.set_footer(text=f"{MARCA} | Use /pings pra ver tudo")
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
        
        embed = discord.Embed(title=f"⏱️🔔 Tics & Pings - {interaction.guild.name}", description=f"Dev: {TAG} | {MARCA}", color=config["cores"]["principal"])
        
        if tics:
            txt=""
            for ch_id, mod, msgs, tempo, chance in tics:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                txt += f"`{mod}` {ch_txt}: {msgs}msgs/{tempo}s/{chance}%\n"
            embed.add_field(name="⏱️ Tics Configurados", value=txt[:1024] or "Nenhum", inline=False)
        else:
            embed.add_field(name="⏱️ Tics", value="Padrão:\n• pokemon: 20 msgs / 180s / 20%\n• rpg: 25 / 300s / 15%\n• dungeon: 40 / 600s / 10%\n• loot: 30 / 400s / 20%\nUse `/configurar-ticks` pra mudar", inline=False)
        
        if pings:
            txt=""
            for ch_id, mod, role_id in pings:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                role = interaction.guild.get_role(role_id)
                role_txt = role.mention if role else f"ID {role_id} (deleted)"
                txt += f"`{mod}` {ch_txt} -> {role_txt}\n"
            embed.add_field(name="🔔 Pings Ativos", value=txt[:1024], inline=False)
        else:
            embed.add_field(name="🔔 Pings", value="❌ Nenhum ping configurado!\nUse: `/configurar-ping modulo:pokemon cargo:@SeuCargo canal:#f`\nDepois teste: `/testar-ping modulo:pokemon`", inline=False)
        
        embed.add_field(name="💡 Comandos", value="`/configurar-ticks modulo:pokemon mensagens:10 tempo:60 chance:50 canal:#f`\n`/configurar-ping modulo:pokemon cargo:@Cargo canal:#f`\n`/testar-ping modulo:pokemon` - testa se pinga\n`/spawn-forcado modulo:dungeon canal:#geral`", inline=False)
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
            await interaction.response.send_message(f"❌ Nenhum ping configurado para `{modulo}` neste canal nem global!\nConfigure: `/configurar-ping modulo:{modulo} cargo:@SeuCargo canal:#{interaction.channel.name}`", ephemeral=True)
            return
        
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Cargo ID {role_id} não existe mais! Foi deletado. Configure de novo.", ephemeral=True)
            return
        
        allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
        # Teste 1: ping simples
        await interaction.response.send_message(f"🔔 Teste ping `{modulo}`: {role.mention} - Se você recebeu notificação (com som), pings estão funcionando! ✅", allowed_mentions=allowed)
        
        # Teste 2: embed com ping no content
        embed = discord.Embed(title=f"🔔 Teste Ping - {modulo}", description=f"Cargo pingado: {role.mention}\nCanal: {interaction.channel.mention}\n\n✅ Se apareceu notificação, tá OK!\n❌ Se NÃO apareceu:\n1. Você silenciou o cargo? (Discord > Config cargo)\n2. Bot tem permissão mencionar? (cargo abaixo do bot)\n3. Você tem o cargo mutado nas notificações?\n\nTente tornar cargo mencionável: Editar cargo > Permitir que qualquer um mencione", color=config["cores"]["sucesso"])
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed, allowed_mentions=allowed)

    @app_commands.command(name="spawn-forcado", description="[ADM] Força spawn com ping")
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
        
        role_id = await database.get_ping_role(interaction.guild.id, canal_alvo.id, modulo) or await database.get_ping_role(interaction.guild.id, 0, modulo)
        ping_txt = f"<@&{role_id}> " if role_id else "(sem ping configurado - use /configurar-ping)"
        
        if modulo == "pokemon":
            cog = self.bot.get_cog("Pokemon")
            if cog:
                await cog.spawn_pokemon(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Pokemon forçado em {canal_alvo.mention}\nPing: {ping_txt}\nSe não pingou, configure: `/configurar-ping modulo:pokemon cargo:@Cargo canal:{canal_alvo.mention}`", ephemeral=True)
        elif modulo == "rpg":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_mob(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Mob RPG forçado em {canal_alvo.mention} com ping {ping_txt}", ephemeral=True)
        elif modulo == "dungeon":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_dungeon(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Dungeon forçada em {canal_alvo.mention} {ping_txt}", ephemeral=True)
        elif modulo == "loot":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_loot(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Baú forçado em {canal_alvo.mention} {ping_txt}", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        guild_id = message.guild.id
        channel_id = message.channel.id
        
        for modulo in ["rpg", "dungeon", "loot", "farm"]:
            tic = await database.get_spawn_tic(guild_id, channel_id, modulo)
            if not tic:
                tic = await database.get_spawn_tic(guild_id, 0, modulo)
            if not tic:
                defaults = {"rpg": {"mensagens":25,"tempo_seg":300,"chance":15},
                            "dungeon": {"mensagens":40,"tempo_seg":600,"chance":10},
                            "loot": {"mensagens":30,"tempo_seg":400,"chance":20},
                            "farm": {"mensagens":20,"tempo_seg":200,"chance":25}}
                tic = defaults.get(modulo)
                if not tic:
                    continue
            
            key = (guild_id, channel_id, modulo)
            count = self.counters.get(key, 0) + 1
            self.counters[key] = count
            
            last = self.last_spawn_time.get(key)
            if last:
                diff = (discord.utils.utcnow() - last).total_seconds()
                if diff < tic["tempo_seg"]:
                    continue
            
            if count >= tic["mensagens"]:
                if random.randint(1,100) <= tic["chance"]:
                    self.counters[key] = 0
                    self.last_spawn_time[key] = discord.utils.utcnow()
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
