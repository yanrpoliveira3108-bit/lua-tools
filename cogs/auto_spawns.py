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

class AutoSpawns(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spawn_loop.start()
        print(f"[AUTO-SPAWN] Loop automático iniciado - yna.019")

    def cog_unload(self):
        self.spawn_loop.cancel()

    @tasks.loop(seconds=60)
    async def spawn_loop(self):
        """Spawna automaticamente a cada 60s verificando tics - yna.019"""
        await self.bot.wait_until_ready()
        try:
            async with aiosqlite.connect(database.DB_PATH) as db:
                # Pega todas configs de tics
                async with db.execute("SELECT guild_id, channel_id, modulo, mensagens, tempo_seg, chance FROM spawn_tics") as cur:
                    configs = await cur.fetchall()
                    
                # Se não tem config custom, usa padrão global por guild
                guilds_configs = {}
                for guild_id, ch_id, modulo, msgs, tempo, chance in configs:
                    if guild_id not in guilds_configs:
                        guilds_configs[guild_id] = []
                    guilds_configs[guild_id].append((ch_id, modulo, msgs, tempo, chance))
                
                # Para guilds sem config, cria padrão
                if not configs:
                    # Pega todos guilds do bot
                    for guild in self.bot.guilds:
                        # Tenta achar canal ativo pra cada modulo
                        for modulo in ["pokemon", "rpg", "dungeon", "loot"]:
                            defaults = {
                                "pokemon": (20, 180, 20),
                                "rpg": (25, 300, 15),
                                "dungeon": (40, 600, 10),
                                "loot": (30, 400, 20),
                                "farm": (20, 200, 25)
                            }
                            msgs, tempo, chance = defaults.get(modulo, (20, 180, 20))
                            
                            # 5% chance por minuto de spawn automático mesmo sem msg
                            if random.randint(1,100) <= 5:
                                channel = None
                                for ch in guild.text_channels:
                                    if ch.permissions_for(guild.me).send_messages:
                                        if await database.is_modulo_enabled(guild.id, modulo if modulo in ["economia","rpg","pokemon","familia","casa","farm","eventos","diversao"] else "rpg" if modulo=="rpg" else "pokemon" if modulo=="pokemon" else "diversao", ch.id):
                                            channel = ch
                                            break
                                if channel:
                                    await self.do_spawn(guild, channel, modulo, chance)
                    return
                
                # Para configs custom
                for guild_id, ch_id, modulo, msgs, tempo, chance in configs:
                    guild = self.bot.get_guild(guild_id)
                    if not guild:
                        continue
                    
                    # Verifica se já passou tempo desde último spawn
                    # Vamos usar uma tabela simples em memória ou verificar se canal tem spawn ativo
                    # Se canal_id=0 (global), escolhe canal aleatório da guild
                    if ch_id == 0:
                        # Global - escolhe canal aleatório com permissão
                        possible_channels = [c for c in guild.text_channels if c.permissions_for(guild.me).send_messages]
                        if not possible_channels:
                            continue
                        channel = random.choice(possible_channels)
                    else:
                        channel = guild.get_channel(ch_id)
                        if not channel:
                            continue
                    
                    # Verifica se já tem spawn ativo desse tipo
                    if modulo == "pokemon":
                        async with db.execute("SELECT * FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (guild_id, channel.id)) as cur:
                            if await cur.fetchone():
                                continue  # Já tem pokemon
                    elif modulo in ["rpg","dungeon","loot"]:
                        # Verifica mundo_spawns
                        async with db.execute("SELECT * FROM mundo_spawns WHERE guild_id=? AND channel_id=? AND tipo=?", (guild_id, channel.id, modulo)) as cur:
                            if await cur.fetchone():
                                continue
                    
                    # Chance por tempo: a cada minuto, chance% de spawn automático
                    # Se tempo configurado é 180s (3min), a chance por minuto é chance/3
                    # Simplifica: chance% por verificação (a cada 60s)
                    chance_real = chance * 0.3  # Reduz um pouco pra não spam
                    if random.randint(1,100) <= chance_real:
                        await self.do_spawn(guild, channel, modulo, chance)

        except Exception as e:
            print(f"[AUTO-SPAWN] Erro loop: {e}")
            import traceback
            traceback.print_exc()

    async def do_spawn(self, guild, channel, modulo, chance):
        try:
            print(f"[AUTO-SPAWN] Spawn {modulo} em {guild.name}/#{channel.name} chance {chance}% - yna.019")
            if modulo == "pokemon":
                cog = self.bot.get_cog("Pokemon")
                if cog:
                    await cog.spawn_pokemon(guild, channel)
            elif modulo == "rpg":
                mundo = self.bot.get_cog("Mundo")
                if mundo:
                    await mundo.spawn_mob(guild, channel)
            elif modulo == "dungeon":
                mundo = self.bot.get_cog("Mundo")
                if mundo:
                    await mundo.spawn_dungeon(guild, channel)
            elif modulo == "loot":
                mundo = self.bot.get_cog("Mundo")
                if mundo:
                    await mundo.spawn_loot(guild, channel)
            elif modulo == "farm":
                mundo = self.bot.get_cog("Mundo")
                if mundo:
                    # Farm pode ser veio de recurso
                    await channel.send(f"⛏️ **Veio de recursos raro apareceu!** Use `/farm minerar` em {channel.mention}! Ganha 3x recursos por 5min!", delete_after=30)
        except Exception as e:
            print(f"[AUTO-SPAWN] Erro do_spawn {modulo}: {e}")

    @spawn_loop.before_loop
    async def before_spawn(self):
        await self.bot.wait_until_ready()
        print("[AUTO-SPAWN] Aguardando bot pronto...")

    @app_commands.command(name="auto-spawns", description="Configure spawns automáticos por tempo (sem precisar msg)")
    @app_commands.default_permissions(manage_guild=True)
    @app_commands.describe(
        modulo="Qual sistema auto-spawna?",
        ativar="Ativar ou desativar auto spawn por tempo?",
        canal="Canal específico (vazio=global)"
    )
    @app_commands.choices(modulo=[
        app_commands.Choice(name="🔮 Pokémon", value="pokemon"),
        app_commands.Choice(name="⚔️ RPG Mobs", value="rpg"),
        app_commands.Choice(name="🏰 Dungeon", value="dungeon"),
        app_commands.Choice(name="💰 Loot/Baú", value="loot"),
        app_commands.Choice(name="⛏️ Farm Veios", value="farm"),
        app_commands.Choice(name="🎉 Todos", value="todos"),
    ], ativar=[
        app_commands.Choice(name="✅ Ativar Auto", value="ativar"),
        app_commands.Choice(name="❌ Desativar Auto", value="desativar"),
    ])
    async def auto_spawns(self, interaction: discord.Interaction, modulo: str, ativar: str, canal: discord.TextChannel = None):
        channel_id = canal.id if canal else 0
        guild_id = interaction.guild.id
        
        if ativar == "ativar":
            # Se não tem tic configurado, cria um padrão rápido pra auto
            tic = await database.get_spawn_tic(guild_id, channel_id, modulo) if modulo != "todos" else None
            if not tic:
                defaults = {"pokemon": (15, 120, 30), "rpg": (20, 180, 20), "dungeon": (30, 300, 15), "loot": (25, 240, 25), "farm": (15, 150, 30)}
                if modulo == "todos":
                    for mod, (msgs, tempo, chance) in defaults.items():
                        await database.set_spawn_tic(guild_id, channel_id, mod, msgs, tempo, chance)
                else:
                    msgs, tempo, chance = defaults.get(modulo, (20, 180, 20))
                    await database.set_spawn_tic(guild_id, channel_id, modulo, msgs, tempo, chance)
            
            embed = discord.Embed(title=f"✅ Auto-Spawn Ativado - {modulo.upper()}", description=f"**Canal:** {canal.mention if canal else '🌐 Global (todos canais com permissão)'}\n\nAgora **{modulo}** vai spawnar automaticamente:\n• A cada X mensagens (configurado no tic)\n• **E também a cada poucos minutos mesmo sem mensagem!** (loop automático)\n\nUse `/configurar-ticks` pra ajustar velocidade e `/configurar-ping` pra escolher cargo pingado.\n\nTeste: `/spawn-forcado modulo:{modulo}`", color=config["cores"]["sucesso"])
        else:
            # Desativar = seta chance 0 e mensagens muito alta
            if modulo == "todos":
                for mod in ["pokemon","rpg","dungeon","loot","farm"]:
                    await database.set_spawn_tic(guild_id, channel_id, mod, 9999, 9999, 0)
            else:
                await database.set_spawn_tic(guild_id, channel_id, modulo, 9999, 9999, 0)
            embed = discord.Embed(title=f"❌ Auto-Spawn Desativado - {modulo.upper()}", description=f"**Canal:** {canal.mention if canal else 'Global'}\n\n{modulo} não spawna mais automaticamente.\nUse `/auto-spawns modulo:{modulo} ativar:ativar` pra reativar.", color=config["cores"]["erro"])
        
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="spawns-status", description="Veja status dos spawns automáticos")
    async def spawns_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild_id = interaction.guild.id
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT channel_id, modulo, mensagens, tempo_seg, chance FROM spawn_tics WHERE guild_id=?", (guild_id,)) as cur:
                tics = await cur.fetchall()
            async with db.execute("SELECT channel_id, modulo, role_id FROM pings_config WHERE guild_id=?", (guild_id,)) as cur:
                pings = await cur.fetchall()
            # Verifica spawns ativos agora
            async with db.execute("SELECT channel_id, pokemon_nome, raridade FROM pokemon_spawns WHERE guild_id=?", (guild_id,)) as cur:
                ativos_poke = await cur.fetchall()
        
        embed = discord.Embed(title=f"🌍 Spawns Automáticos - {interaction.guild.name}", description=f"**Loop checa a cada 60s** - Spawna mesmo sem msgs!\n{MARCA}", color=config["cores"]["principal"])
        
        if tics:
            txt=""
            for ch_id, mod, msgs, tempo, chance in tics[:10]:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐 Global"
                auto = "✅ Auto" if tempo < 9999 else "❌ Desativado"
                txt += f"`{mod}` {ch_txt} {msgs}msgs/{tempo}s/{chance}% {auto}\n"
            embed.add_field(name="⏱️ Tics", value=txt[:1024], inline=False)
        else:
            embed.add_field(name="⏱️ Tics", value="Padrão ativo (sem config custom). Use `/auto-spawns` pra ativar/desativar", inline=False)
        
        if ativos_poke:
            txt=""
            for ch_id, nome, rar in ativos_poke:
                txt += f"<#{ch_id}>: **{nome}** ({rar})\n"
            embed.add_field(name="🔮 Pokémons Ativos Agora", value=txt[:1024], inline=False)
        else:
            embed.add_field(name="🔮 Ativos", value="Nenhum pokémon ativo agora. Use `/spawn-forcado modulo:pokemon`", inline=False)
        
        if pings:
            txt=""
            for ch_id, mod, role_id in pings[:10]:
                ch_txt = f"<#{ch_id}>" if ch_id!=0 else "🌐"
                txt += f"{mod} {ch_txt} -> <@&{role_id}>\n"
            embed.add_field(name="🔔 Pings", value=txt[:1024], inline=False)
        
        embed.add_field(name="💡 Como usar", value="`/auto-spawns modulo:pokemon ativar:ativar canal:#f` - ativa auto\n`/auto-spawns modulo:pokemon ativar:desativar` - desativa\n`/configurar-ticks` - muda velocidade\n`/configurar-ping` - cargo pingado\n`/spawn-forcado` - testa agora", inline=False)
        embed.set_footer(text=f"{MARCA} | Auto-spawn a cada 60s")
        await interaction.followup.send(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AutoSpawns(bot))
