import discord
from discord.ext import commands
import json
import random
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
                defaults = {"rpg": {"mensagens":25,"tempo_seg":300,"chance":15}, "dungeon": {"mensagens":40,"tempo_seg":600,"chance":10}, "loot": {"mensagens":30,"tempo_seg":400,"chance":20}, "farm": {"mensagens":20,"tempo_seg":200,"chance":25}}
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

    @discord.app_commands.command(name="configurar-ticks", description=f"[ADM] Configure tempo de spawn - {TAG}")
    @discord.app_commands.describe(modulo="Qual sistema?", canal="Canal (vazio=global)", mensagens="Msgs 1-500", tempo="Tempo seg 10-3600", chance="Chance 1-100")
    @discord.app_commands.choices(modulo=[
        discord.app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        discord.app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        discord.app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        discord.app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        discord.app_commands.Choice(name="⛏️ Farm", value="farm"),
    ])
    @discord.app_commands.default_permissions(manage_guild=True)
    async def configurar_ticks(self, interaction: discord.Interaction, modulo: str, mensagens: int = 20, tempo: int = 180, chance: int = 25, canal: discord.TextChannel = None):
        if not (1 <= mensagens <= 500 and 10 <= tempo <= 3600 and 1 <= chance <= 100):
            await interaction.response.send_message("Valores inválidos! msgs 1-500, tempo 10-3600, chance 1-100", ephemeral=True)
            return
        channel_id = canal.id if canal else 0
        await database.set_spawn_tic(interaction.guild.id, channel_id, modulo, mensagens, tempo, chance)
        embed = discord.Embed(title=f"⏱️ Tics {modulo.upper()} Configurados!", description=f"**Módulo:** {modulo}\n**Canal:** {canal.mention if canal else '🌐 Global'}\n**Msgs:** {mensagens}\n**Tempo:** {tempo}s\n**Chance:** {chance}%\n\nUse `/pings` pra ver", color=config["cores"]["principal"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="configurar-ping", description=f"[ADM] Configure cargo pingado - {TAG} - SEM bloqueio")
    @discord.app_commands.describe(modulo="Qual spawn pinga?", cargo="Cargo a mencionar (vazio=remove)", canal="Canal (vazio=global)")
    @discord.app_commands.choices(modulo=[
        discord.app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        discord.app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        discord.app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        discord.app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        discord.app_commands.Choice(name="⛏️ Farm", value="farm"),
        discord.app_commands.Choice(name="🎉 Todos spawns", value="todos"),
    ])
    @discord.app_commands.default_permissions(manage_guild=True)
    async def configurar_ping(self, interaction: discord.Interaction, modulo: str, cargo: discord.Role = None, canal: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)
        channel_id = canal.id if canal else 0
        guild = interaction.guild
        
        aviso = ""
        if cargo and cargo.position >= guild.me.top_role.position:
            aviso = f"\n⚠️ **Aviso:** Meu cargo é menor que {cargo.mention}! Não consigo tornar mencionável sozinho. Ative manual: Config > Cargos > {cargo.name} > Permitir menção.\n"
        
        # Salva ping (NÃO bloqueia mais por hierarquia)
        if modulo == "todos":
            for mod in ["pokemon","rpg","dungeon","loot","farm"]:
                await database.set_ping_role(guild.id, channel_id, mod, cargo.id if cargo else None)
            msg = "Ping para TODOS os módulos"
        else:
            await database.set_ping_role(guild.id, channel_id, modulo, cargo.id if cargo else None)
            msg = f"Ping {modulo}"

        if cargo:
            # Tenta tornar mencionável mas não falha se não conseguir
            try:
                if not cargo.mentionable:
                    await cargo.edit(mentionable=True, reason=f"Lua Tools ping por {interaction.user}")
            except:
                pass
            
            embed = discord.Embed(title="🔔 Ping Configurado!", description=f"{msg}\n**Cargo:** {cargo.mention}\n**Canal:** {canal.mention if canal else '🌐 Global'}\n**Módulo:** {modulo}\n{aviso}\n✅ Agora quando {modulo} spawnar, vai pingar {cargo.mention}!\n\nTeste: `/testar-ping modulo:{modulo}`", color=config["cores"]["sucesso"])
            if aviso:
                embed.add_field(name="⚠️ Como arrumar", value=f"1. Arraste cargo Lua Tools acima de {cargo.mention}\n2. Ou ative: Cargos > {cargo.name} > Permitir menção", inline=False)
        else:
            embed = discord.Embed(title="🔕 Ping Removido!", description=f"{msg} removido em {canal.mention if canal else 'global'}", color=config["cores"]["erro"])

        # Cria tic padrão se não existe
        if cargo and modulo != "todos":
            tic = await database.get_spawn_tic(guild.id, channel_id, modulo)
            if not tic:
                await database.set_spawn_tic(guild.id, channel_id, modulo, 20, 180, 25)
                embed.add_field(name="⏱️ Tic", value="Tic padrão criado (20/180s/25%). /configurar-ticks pra mudar", inline=False)
        
        embed.set_footer(text=f"{MARCA} | /pings")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="pings", description="Veja tics e pings configurados")
    async def pings_lista(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT channel_id, modulo, mensagens, tempo_seg, chance FROM spawn_tics WHERE guild_id=?", (guild_id,)) as cur:
                tics = await cur.fetchall()
            async with db.execute("SELECT channel_id, modulo, role_id FROM pings_config WHERE guild_id=? AND habilitado=1", (guild_id,)) as cur:
                pings = await cur.fetchall()
        
        embed = discord.Embed(title=f"⏱️🔔 Tics & Pings - {interaction.guild.name}", description=f"{MARCA}", color=config["cores"]["principal"])
        if tics:
            txt=""
            for ch_id, mod, msgs, tempo, chance in tics:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                txt += f"`{mod}` {ch_txt}: {msgs}msgs/{tempo}s/{chance}%\n"
            embed.add_field(name="⏱️ Tics", value=txt[:1024] or "Nenhum", inline=False)
        else:
            embed.add_field(name="⏱️ Tics", value="Padrão: pokemon 20/180s/20%, rpg 25/300s/15%, dungeon 40/600s/10%, loot 30/400s/20%", inline=False)
        
        if pings:
            txt=""
            for ch_id, mod, role_id in pings:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                role = interaction.guild.get_role(role_id)
                role_txt = role.mention if role else f"ID {role_id}"
                txt += f"`{mod}` {ch_txt} -> {role_txt}\n"
            embed.add_field(name="🔔 Pings Ativos", value=txt[:1024], inline=False)
        else:
            embed.add_field(name="🔔 Pings", value="❌ Nenhum! Use `/configurar-ping modulo:pokemon cargo:@Cargo canal:#f`", inline=False)
        
        embed.add_field(name="💡", value="`/configurar-ticks` `/configurar-ping` `/testar-ping` `/spawn-forcado`", inline=False)
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed, ephemeral=True)

    @discord.app_commands.command(name="testar-ping", description="[ADM] Teste se ping funciona")
    @discord.app_commands.choices(modulo=[
        discord.app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        discord.app_commands.Choice(name="⚔️ RPG", value="rpg"),
        discord.app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        discord.app_commands.Choice(name="💰 Loot", value="loot"),
    ])
    @discord.app_commands.default_permissions(manage_guild=True)
    async def testar_ping(self, interaction: discord.Interaction, modulo: str):
        role_id = await database.get_ping_role(interaction.guild.id, interaction.channel.id, modulo) or await database.get_ping_role(interaction.guild.id, 0, modulo)
        if not role_id:
            await interaction.response.send_message(f"❌ Nenhum ping pra `{modulo}`! Configure: `/configurar-ping modulo:{modulo} cargo:@Cargo`", ephemeral=True)
            return
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message(f"❌ Cargo ID {role_id} deletado!", ephemeral=True)
            return
        allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
        await interaction.response.send_message(f"🔔 Teste `{modulo}`: {role.mention} - Recebeu notificação? ✅", allowed_mentions=allowed)
        embed = discord.Embed(title=f"🔔 Teste Ping - {modulo}", description=f"Cargo: {role.mention}\nCanal: {interaction.channel.mention}\n\n✅ Notificação? Pings OK!\n❌ Sem? Verifique se cargo permite menção.", color=config["cores"]["sucesso"])
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed, allowed_mentions=allowed)

    @discord.app_commands.command(name="spawn-forcado", description="[ADM] Força spawn com ping")
    @discord.app_commands.default_permissions(manage_guild=True)
    @discord.app_commands.choices(modulo=[
        discord.app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        discord.app_commands.Choice(name="⚔️ RPG Mob", value="rpg"),
        discord.app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        discord.app_commands.Choice(name="💰 Loot", value="loot"),
    ])
    async def spawn_forcado(self, interaction: discord.Interaction, modulo: str, canal: discord.TextChannel = None):
        canal_alvo = canal or interaction.channel
        await interaction.response.defer(ephemeral=True)
        role_id = await database.get_ping_role(interaction.guild.id, canal_alvo.id, modulo) or await database.get_ping_role(interaction.guild.id, 0, modulo)
        ping_txt = f"<@&{role_id}> " if role_id else "(sem ping)"
        if modulo == "pokemon":
            cog = self.bot.get_cog("Pokemon")
            if cog:
                await cog.spawn_pokemon(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Pokemon em {canal_alvo.mention} Ping: {ping_txt}", ephemeral=True)
        elif modulo == "rpg":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_mob(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Mob RPG em {canal_alvo.mention} {ping_txt}", ephemeral=True)
        elif modulo == "dungeon":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_dungeon(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Dungeon em {canal_alvo.mention} {ping_txt}", ephemeral=True)
        elif modulo == "loot":
            mundo = self.bot.get_cog("Mundo")
            if mundo:
                await mundo.spawn_loot(interaction.guild, canal_alvo)
                await interaction.followup.send(f"✅ Baú em {canal_alvo.mention} {ping_txt}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(SpawnTics(bot))
