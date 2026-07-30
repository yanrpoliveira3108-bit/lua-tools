import discord
from discord.ext import commands
from discord import app_commands
import json
import random
import aiohttp
import aiosqlite
import database

with open("config.json", "r", encoding="utf-8") as f:
    config = json.load(f)

POKEBOLAS = config["pokemon"]["pokebolas"]
MARCA = config["dono"]["marca_dagua"]

def check_modulo():
    async def predicate(interaction: discord.Interaction):
        if not await database.is_modulo_enabled(interaction.guild.id, "pokemon", interaction.channel.id):
            embed = discord.Embed(title="❌ Desativado", description="**Pokémon** desativado aqui. Use /modulos", color=config["cores"]["erro"])
            embed.set_footer(text=MARCA)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return False
        return True
    return app_commands.check(predicate)

POKEMONS_LISTA = [
    {"id": 1, "nome": "bulbasaur", "raridade": "comum"}, {"id": 4, "nome": "charmander", "raridade": "comum"},
    {"id": 7, "nome": "squirtle", "raridade": "comum"}, {"id": 25, "nome": "pikachu", "raridade": "raro"},
    {"id": 39, "nome": "jigglypuff", "raridade": "comum"}, {"id": 52, "nome": "meowth", "raridade": "comum"},
    {"id": 54, "nome": "psyduck", "raridade": "comum"}, {"id": 94, "nome": "gengar", "raridade": "raro"},
    {"id": 133, "nome": "eevee", "raridade": "raro"}, {"id": 143, "nome": "snorlax", "raridade": "raro"},
    {"id": 150, "nome": "mewtwo", "raridade": "lendario"}, {"id": 149, "nome": "dragonite", "raridade": "raro"},
    {"id": 6, "nome": "charizard", "raridade": "raro"}, {"id": 130, "nome": "gyarados", "raridade": "raro"},
    {"id": 144, "nome": "articuno", "raridade": "lendario"}, {"id": 145, "nome": "zapdos", "raridade": "lendario"},
    {"id": 146, "nome": "moltres", "raridade": "lendario"}, {"id": 151, "nome": "mew", "raridade": "mitico"},
    {"id": 249, "nome": "lugia", "raridade": "lendario"}, {"id": 250, "nome": "ho-oh", "raridade": "lendario"},
    {"id": 384, "nome": "rayquaza", "raridade": "mitico"}, {"id": 382, "nome": "kyogre", "raridade": "lendario"},
    {"id": 483, "nome": "dialga", "raridade": "mitico"}, {"id": 484, "nome": "palkia", "raridade": "mitico"},
]

RARIDADE_PESO = {"comum": 0.60, "raro": 0.25, "lendario": 0.12, "mitico": 0.03}
RARIDADE_COR = {"comum": 0x95a5a6, "raro": 0x3498db, "lendario": 0xf1c40f, "mitico": 0x9b59b6}
RARIDADE_CHANCE_MOD = {"comum": 1.0, "raro": 0.8, "lendario": 0.5, "mitico": 0.3}

class Pokemon(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.message_counts = {}

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        if not await database.is_modulo_enabled(message.guild.id, "pokemon", message.channel.id):
            return
        key = f"{message.guild.id}_{message.channel.id}"
        self.message_counts[key] = self.message_counts.get(key, 0) + 1
        
        # Verifica se já tem spawn
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemon_nome FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (message.guild.id, message.channel.id)) as cur:
                if await cur.fetchone():
                    return

        # Pega tic configurado por ADM (ou padrão)
        tic = await database.get_spawn_tic(message.guild.id, message.channel.id, "pokemon")
        if not tic:
            tic = await database.get_spawn_tic(message.guild.id, 0, "pokemon")
        if not tic:
            tic = {"mensagens": config["pokemon"]["messages_para_spawn"], "tempo_seg": 180, "chance": config["pokemon"]["spawn_chance"]}

        threshold = tic["mensagens"]
        chance = tic["chance"]

        if self.message_counts[key] >= threshold:
            # Verifica cooldown de tempo também se tiver
            # Se passou, chance configurável
            if random.randint(1,100) <= chance or self.message_counts[key] >= threshold*1.5:
                await self.spawn_pokemon(message.guild, message.channel)
                self.message_counts[key] = 0

    async def spawn_pokemon(self, guild, channel):
        # Escolhe raridade
        r = random.random()
        raridade = "comum"
        acum = 0
        for rar, peso in RARIDADE_PESO.items():
            acum += peso
            if r <= acum:
                raridade = rar
                break
        candidatos = [p for p in POKEMONS_LISTA if p["raridade"]==raridade]
        if not candidatos:
            candidatos = POKEMONS_LISTA
        poke = random.choice(candidatos)
        
        async with aiosqlite.connect(database.DB_PATH) as db:
            await db.execute("INSERT OR REPLACE INTO pokemon_spawns (guild_id, channel_id, pokemon_nome, pokemon_id, raridade) VALUES (?, ?, ?, ?, ?)", (guild.id, channel.id, poke["nome"], poke["id"], raridade))
            await db.commit()
        
        # Ping role se configurado
        role_id = await database.get_ping_role(guild.id, channel.id, "pokemon")
        if not role_id:
            role_id = await database.get_ping_role(guild.id, 0, "pokemon")
        ping_text = f"<@&{role_id}> " if role_id else ""
        
        cor = RARIDADE_COR.get(raridade, config["cores"]["pokemon"])
        emoji_rar = {"comum":"⚪","raro":"🔵","lendario":"🟡","mitico":"🟣"}[raridade]
        embed = discord.Embed(title=f"{emoji_rar} Pokémon selvagem apareceu!", description=f"{ping_text}**Raridade:** {raridade.upper()}\nDica: `{poke['nome'][0]}`...`{poke['nome'][-1]}` ({len(poke['nome'])} letras)\nUse `/capturar nome:{poke['nome']} bola:ultra_bola`", color=cor)
        embed.set_image(url=f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{poke['id']}.png")
        embed.set_footer(text=f"#{channel.name} | /pokeloja | {MARCA}")
        try:
            # FIX PING: precisa allowed_mentions pra pingar cargo
            allowed = discord.AllowedMentions(roles=True, users=True, everyone=False)
            await channel.send(content=ping_text if ping_text else None, embed=embed, allowed_mentions=allowed)
            print(f"[POKEMON] Spawn {poke['nome']} em #{channel.name} - Ping: {ping_text}")
        except Exception as e:
            print(f"[POKEMON] Erro spawn: {e}")
            # Fallback sem ping
            try:
                await channel.send(embed=embed)
            except:
                pass

    @app_commands.command(name="pokeloja", description="Loja de Pokébolas")
    @check_modulo()
    async def pokeloja(self, interaction: discord.Interaction):
        embed = discord.Embed(title="🏪 Loja Pokémon - Pokébolas", description=f"Use `/comprar item:<nome>`\nVocê precisa de pokébolas para capturar!\n{MARCA}", color=config["cores"]["pokemon"])
        for ball_id, info in POKEBOLAS.items():
            embed.add_field(name=f"{info['emoji']} {info['nome']} - {info['preco']} {config['economia']['moeda_emoji']}", value=f"Chance: {int(info['chance']*100)}% | ID: `{ball_id}`", inline=False)
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "pokemon")
        if inv:
            txt = "\n".join([f"{POKEBOLAS.get(k,{}).get('emoji','')} {k}: {v}" for k,v in inv.items()])
            embed.add_field(name="🎒 Suas Pokébolas", value=txt, inline=False)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="bolsa", description="Suas pokébolas")
    @check_modulo()
    async def bolsa(self, interaction: discord.Interaction):
        inv = await database.get_inventario(interaction.user.id, interaction.guild.id, "pokemon")
        if not inv:
            await interaction.response.send_message(f"🎒 Bolsa vazia! Compre em `/pokeloja`\nGanhe 2 grátis no `/daily`\n{MARCA}", ephemeral=True)
            return
        embed = discord.Embed(title="🎒 Bolsa Pokémon", color=config["cores"]["pokemon"])
        for ball_id, qtd in inv.items():
            info = POKEBOLAS.get(ball_id, {"nome": ball_id, "emoji": "🔴"})
            embed.add_field(name=f"{info['emoji']} {info['nome']}", value=f"Qtd: {qtd}", inline=True)
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="capturar", description="Capture o pokémon")
    @app_commands.describe(nome="Nome do pokémon", bola="Qual pokébola usar")
    @app_commands.choices(bola=[
        app_commands.Choice(name="🔴 Pokébola (60%) - 100", value="pokebola"),
        app_commands.Choice(name="🔵 Grande Bola (80%) - 300", value="grande_bola"),
        app_commands.Choice(name="🟡 Ultra Bola (92%) - 800", value="ultra_bola"),
        app_commands.Choice(name="🟣 Master Bola (100%) - 5000", value="master_bola"),
    ])
    @check_modulo()
    async def capturar(self, interaction: discord.Interaction, nome: str, bola: str = "pokebola"):
        if bola not in POKEBOLAS:
            await interaction.response.send_message(f"Pokébola inválida! Use `/pokeloja`\n{MARCA}", ephemeral=True)
            return
        if not await database.has_item(interaction.user.id, interaction.guild.id, bola, 1):
            await interaction.response.send_message(f"❌ Você não tem {POKEBOLAS[bola]['nome']}! Compre com `/comprar item:{bola}`\n{MARCA}", ephemeral=True)
            return

        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemon_nome, pokemon_id, raridade FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message(f"❌ Nenhum pokémon aqui! Continue conversando.\n{MARCA}", ephemeral=True)
                    return
                nome_correto, poke_id, raridade = row
                if nome.lower() != nome_correto.lower():
                    await interaction.response.send_message(f"❌ Nome errado! Dica: começa com `{nome_correto[0].upper()}`\n{MARCA}", ephemeral=True)
                    return

                await database.remove_item(interaction.user.id, interaction.guild.id, bola, 1)
                base_chance = POKEBOLAS[bola]["chance"]
                mod_raridade = RARIDADE_CHANCE_MOD.get(raridade, 1.0)
                chance_final = base_chance * mod_raridade
                sucesso = random.random() < chance_final

                if sucesso:
                    await db.execute("DELETE FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id))
                    async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur2:
                        r2 = await cur2.fetchone()
                        import json as js
                        lista = js.loads(r2[0]) if r2 else []
                        lista.append({"id": poke_id, "nome": nome_correto, "raridade": raridade, "nivel": random.randint(5,50)})
                        await db.execute("INSERT OR REPLACE INTO pokemon_users (user_id, guild_id, pokemons) VALUES (?, ?, ?)", (interaction.user.id, interaction.guild.id, js.dumps(lista)))
                    await db.commit()
                    embed = discord.Embed(title="🎉 Capturado!", description=f"{interaction.user.mention} capturou **{nome_correto.capitalize()}** [{raridade.upper()}]\nUsou {POKEBOLAS[bola]['emoji']} {POKEBOLAS[bola]['nome']}\nChance {int(chance_final*100)}%\n{MARCA}", color=config["cores"]["sucesso"])
                    embed.set_thumbnail(url=f"https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{poke_id}.png")
                    embed.set_footer(text=MARCA)
                    await interaction.response.send_message(embed=embed)
                else:
                    fugiu = random.random() < 0.3
                    if fugiu:
                        await db.execute("DELETE FROM pokemon_spawns WHERE guild_id=? AND channel_id=?", (interaction.guild.id, interaction.channel.id))
                        await db.commit()
                        await interaction.response.send_message(f"💨 **{nome_correto.capitalize()}** escapou! {POKEBOLAS[bola]['emoji']} falhou ({int(chance_final*100)}%) e fugiu!\n{MARCA}")
                    else:
                        await db.commit()
                        await interaction.response.send_message(f"❌ Quase! {POKEBOLAS[bola]['emoji']} falhou ({int(chance_final*100)}%). Tente de novo! Continua ali.\n{MARCA}")

    @app_commands.command(name="pokedex", description="Info de pokémon")
    @check_modulo()
    async def pokedex(self, interaction: discord.Interaction, nome: str):
        await interaction.response.defer()
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"https://pokeapi.co/api/v2/pokemon/{nome.lower()}") as resp:
                    if resp.status != 200:
                        await interaction.followup.send(f"Pokémon `{nome}` não encontrado!")
                        return
                    data = await resp.json()
        except Exception as e:
            await interaction.followup.send(f"Erro: {e}")
            return
        embed = discord.Embed(title=f"#{data['id']} {data['name'].capitalize()}", color=config["cores"]["pokemon"])
        embed.set_thumbnail(url=data['sprites']['other']['official-artwork']['front_default'])
        tipos = ", ".join([t['type']['name'] for t in data['types']])
        embed.add_field(name="Tipo", value=tipos, inline=True)
        embed.add_field(name="Altura", value=f"{data['height']/10}m", inline=True)
        embed.add_field(name="Peso", value=f"{data['weight']/10}kg", inline=True)
        embed.set_footer(text=MARCA)
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="meus-pokemons", description="Sua coleção")
    @check_modulo()
    async def meus_pokemons(self, interaction: discord.Interaction):
        async with aiosqlite.connect(database.DB_PATH) as db:
            async with db.execute("SELECT pokemons FROM pokemon_users WHERE user_id=? AND guild_id=?", (interaction.user.id, interaction.guild.id)) as cur:
                row = await cur.fetchone()
                if not row:
                    await interaction.response.send_message(f"Nenhum pokémon! Continue ativo no chat.\n{MARCA}", ephemeral=True)
                    return
                import json as js
                lista = js.loads(row[0])
        if not lista:
            await interaction.response.send_message(f"Nenhum ainda :(\n{MARCA}", ephemeral=True)
            return
        from collections import Counter
        rar_count = Counter([p.get("raridade","comum") for p in lista])
        desc = f"Total: {len(lista)} | " + " | ".join([f"{rar}: {qtd}" for rar,qtd in rar_count.items()]) + "\n\n"
        for p in lista[-15:]:
            emoji_rar = {"comum":"⚪","raro":"🔵","lendario":"🟡","mitico":"🟣"}.get(p.get("raridade","comum"),"⚪")
            desc += f"{emoji_rar} `#{p['id']}` **{p['nome'].capitalize()}** Nv {p['nivel']}\n"
        embed = discord.Embed(title=f"🎒 {interaction.user.display_name} ({len(lista)})", description=desc, color=config["cores"]["pokemon"])
        embed.set_footer(text=MARCA)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="pokemon-spawn", description="[ADM] Forçar spawn")
    @app_commands.default_permissions(manage_guild=True)
    async def force_spawn(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.spawn_pokemon(interaction.guild, interaction.channel)
        await interaction.followup.send(f"✅ Spawn forçado! {MARCA}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pokemon(bot))
